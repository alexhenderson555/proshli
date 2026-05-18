"""Post-deploy smoke test for a running Proshli stack.

Hits the externally observable surface to confirm:

* API liveness (``/health``)
* API readiness — Postgres + Redis reachable (``/health/ready``)
* Prometheus metrics endpoint serves exposition format (``/metrics``)
* Telegram bot token works (``getMe``) — proxy for "the bot is up
  and the env file isn't stale". The bot itself is polling, so there
  is no inbound port to probe; ``getMe`` is the cheapest signal that
  the token is valid and Telegram accepts it.

Read-only, no auth required against the API (the health routes are
public). Designed to be run from CI after a deploy or from cron as a
liveness alarm.

Usage
-----

    python scripts/smoke_prod.py                                    # localhost
    python scripts/smoke_prod.py --base-url https://api.proshli.ru
    python scripts/smoke_prod.py --bot-token "$TELEGRAM_BOT_TOKEN"  # full sweep

Exit code is ``0`` if every requested check passes, ``1`` otherwise.
Each check prints one line — easy to grep, easy to wire into Slack.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import Callable

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass
class CheckResult:
    """One smoke check's outcome.

    ``ok`` is the only field that affects the exit code; ``latency_ms``
    and ``detail`` are surfaced for the human reading the log.
    """

    name: str
    ok: bool
    latency_ms: int
    detail: str = ""


def _format(result: CheckResult) -> str:
    mark = "PASS" if result.ok else "FAIL"
    line = f"[{mark}] {result.name:<28} {result.latency_ms:>5} ms"
    if result.detail:
        line += f"  {result.detail}"
    return line


def _timed(name: str, fn: Callable[[], CheckResult]) -> CheckResult:
    """Run ``fn`` and stamp its wall-clock latency.

    Wraps unexpected exceptions so a connection refused / DNS error
    surfaces as a normal failed check instead of a stack trace — the
    operator wants ``[FAIL] api_liveness`` in the log, not a Python
    traceback. ``name`` is passed in explicitly so the failure line
    still attributes to the right check when the function itself
    couldn't return a :class:`CheckResult`.
    """
    start = time.perf_counter()
    try:
        result = fn()
    except (httpx.HTTPError, OSError) as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return CheckResult(
            name=name,
            ok=False,
            latency_ms=elapsed_ms,
            detail=f"transport error: {exc}",
        )
    result.latency_ms = int((time.perf_counter() - start) * 1000)
    return result


def check_api_liveness(client: httpx.Client, base_url: str) -> CheckResult:
    resp = client.get(f"{base_url}/health")
    if resp.status_code != 200:
        return CheckResult("api_liveness", False, 0, f"status={resp.status_code}")
    payload = resp.json()
    if payload.get("status") != "ok":
        return CheckResult("api_liveness", False, 0, f"body={payload}")
    return CheckResult("api_liveness", True, 0)


def check_api_readiness(client: httpx.Client, base_url: str) -> CheckResult:
    """Hits ``/health/ready`` — fails fast if Postgres or Redis is down."""
    resp = client.get(f"{base_url}/health/ready")
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if resp.status_code != 200:
        # 503 from the endpoint means at least one dep is down; surface
        # which one in the failure line so the operator goes straight to
        # the culprit.
        deps = ", ".join(f"{k}={v}" for k, v in body.items()) if body else f"status={resp.status_code}"
        return CheckResult("api_readiness_db_redis", False, 0, deps)
    if body.get("db") != "ok" or body.get("redis") != "ok":
        return CheckResult("api_readiness_db_redis", False, 0, f"body={body}")
    return CheckResult("api_readiness_db_redis", True, 0)


def check_metrics_endpoint(client: httpx.Client, base_url: str) -> CheckResult:
    """``/metrics`` must serve Prometheus exposition format.

    We deliberately don't parse the metric values — that would couple
    the smoke test to the specific counters in ``ai_metrics.py``. All
    we want is "the endpoint exists, returns 200, and the body looks
    like exposition format (starts with a ``# HELP`` or ``# TYPE``)".
    """
    resp = client.get(f"{base_url}/metrics")
    if resp.status_code != 200:
        return CheckResult("metrics_endpoint", False, 0, f"status={resp.status_code}")
    body = resp.text or ""
    if "# HELP" not in body and "# TYPE" not in body:
        return CheckResult(
            "metrics_endpoint",
            False,
            0,
            "body does not look like prometheus exposition format",
        )
    return CheckResult("metrics_endpoint", True, 0)


def check_bot_token(client: httpx.Client, bot_token: str) -> CheckResult:
    """Confirm the bot token is valid by hitting Telegram's ``getMe``.

    A working ``getMe`` is necessary-but-not-sufficient for "the bot is
    actually polling and serving users" — but if it fails, the bot is
    definitely broken (revoked token, wrong env, network blocked). It's
    the cheapest external check available since the bot uses polling.
    """
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    resp = client.get(url)
    if resp.status_code != 200:
        return CheckResult("bot_token_valid", False, 0, f"status={resp.status_code}")
    body = resp.json()
    if not body.get("ok"):
        return CheckResult("bot_token_valid", False, 0, f"body={body}")
    username = body.get("result", {}).get("username", "?")
    return CheckResult("bot_token_valid", True, 0, f"as @{username}")


def run(base_url: str, bot_token: str | None, timeout: float) -> int:
    """Execute every check in order and return a shell-friendly exit code.

    Order is from cheapest to most informative: liveness first because
    a dead API makes every other check meaningless; the bot check
    last because it's a separate origin and slowest.
    """
    print(f"smoke_prod: base_url={base_url} timeout={timeout}s")
    results: list[CheckResult] = []
    with httpx.Client(timeout=timeout) as client:
        checks: list[tuple[str, Callable[[], CheckResult]]] = [
            ("api_liveness", lambda: check_api_liveness(client, base_url)),
            ("api_readiness_db_redis", lambda: check_api_readiness(client, base_url)),
            ("metrics_endpoint", lambda: check_metrics_endpoint(client, base_url)),
        ]
        if bot_token:
            checks.append(("bot_token_valid", lambda: check_bot_token(client, bot_token)))
        for name, check in checks:
            results.append(_timed(name, check))

    for result in results:
        print(_format(result))

    failed = [r for r in results if not r.ok]
    if failed:
        print(f"smoke_prod: {len(failed)}/{len(results)} checks FAILED")
        return 1
    print(f"smoke_prod: all {len(results)} checks passed")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument(
        "--base-url",
        default=os.getenv("PROSHLI_SMOKE_BASE_URL", DEFAULT_BASE_URL),
        help="Public API base URL (default: $PROSHLI_SMOKE_BASE_URL or localhost).",
    )
    parser.add_argument(
        "--bot-token",
        default=os.getenv("TELEGRAM_BOT_TOKEN"),
        help="Telegram bot token (default: $TELEGRAM_BOT_TOKEN). If unset, the bot check is skipped.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-request timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(run(args.base_url.rstrip("/"), args.bot_token, args.timeout))
