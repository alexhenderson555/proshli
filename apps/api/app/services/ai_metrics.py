"""Prometheus counters for Anthropic API usage.

Records token consumption and call outcomes for every LLM call site, so the
``/metrics`` endpoint can answer "what did the AI stack cost today" without
a separate billing scrape against Anthropic's dashboard.

Endpoint labels stay stable enum-style strings (``chat``, ``cover_letter``,
``improve_resume``, ``vacancy_summary``, ``skill_extract``, ``topic_classify``)
— consumers (Grafana, alert rules) hard-code them, so renaming silently
breaks dashboards. Add new endpoints, don't rename old ones.

Three kinds of token are tracked so the cost calculator can apply the right
unit price:

* ``input`` — fresh input tokens (most expensive aside from output).
* ``output`` — model-emitted tokens.
* ``cache_read`` — input tokens served from Anthropic's prompt cache
  (~10× cheaper than ``input``); confirms ``cache_control`` is working.
* ``cache_creation`` — first-pass cache population; same price as ``input``
  with a small one-time markup, but tracked separately for visibility.

Counters live at module scope so the Prometheus registry only registers
them once per process — re-importing this module does not duplicate
them.
"""

from __future__ import annotations

from typing import Any

import structlog
from prometheus_client import Counter

log = structlog.get_logger(__name__)


# Token-level counter. Labels are intentionally low-cardinality (6 × 4 = 24
# series) — adding per-user or per-model labels would explode the registry.
AI_TOKENS = Counter(
    "proshli_ai_tokens_total",
    "Anthropic tokens consumed, by endpoint and kind.",
    labelnames=("endpoint", "kind"),
)

# Call-level counter so we can spot outages (spike in ``error``) or fallback
# events (spike in ``fallback`` means the rule-based path is being used).
AI_CALLS = Counter(
    "proshli_ai_calls_total",
    "Anthropic API calls, by endpoint and outcome.",
    labelnames=("endpoint", "outcome"),
)


def record_usage(endpoint: str, usage_obj: Any) -> None:
    """Extract token counts from an Anthropic ``Usage`` object and bump counters.

    Accepts ``None`` / objects missing some fields without raising — the
    Anthropic SDK doesn't always populate cache counters when caching is
    disabled, and we don't want a missing attribute to fail the request.
    """
    if usage_obj is None:
        return
    input_tokens = int(getattr(usage_obj, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage_obj, "output_tokens", 0) or 0)
    cache_read = int(getattr(usage_obj, "cache_read_input_tokens", 0) or 0)
    cache_creation = int(getattr(usage_obj, "cache_creation_input_tokens", 0) or 0)

    if input_tokens:
        AI_TOKENS.labels(endpoint=endpoint, kind="input").inc(input_tokens)
    if output_tokens:
        AI_TOKENS.labels(endpoint=endpoint, kind="output").inc(output_tokens)
    if cache_read:
        AI_TOKENS.labels(endpoint=endpoint, kind="cache_read").inc(cache_read)
    if cache_creation:
        AI_TOKENS.labels(endpoint=endpoint, kind="cache_creation").inc(cache_creation)


def record_outcome(endpoint: str, outcome: str) -> None:
    """Bump the call-outcome counter.

    ``outcome`` is one of ``"success"`` (Anthropic returned a usable
    response), ``"error"`` (network / quota / parse failure — we fell back
    to a scripted answer), or ``"fallback"`` (rule-based path was selected
    deliberately, e.g. no API key configured). Keep the vocabulary tiny so
    alerts can pattern-match on it.
    """
    AI_CALLS.labels(endpoint=endpoint, outcome=outcome).inc()
