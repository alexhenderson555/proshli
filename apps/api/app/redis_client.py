"""Lazy async Redis client.

We don't want a Redis dependency at import time — the test suite runs without
Redis (in-process httpx/ASGI), and the rate-limit middleware degrades cleanly
when the server is unreachable. ``get_redis`` returns ``None`` if connection
fails, so callers can early-out.

Production deployments set ``REDIS_URL`` in env and the first request will
warm the pool.
"""

from __future__ import annotations

import contextlib
from typing import cast

import redis.asyncio as redis_async
import structlog

from app.config import settings

log = structlog.get_logger(__name__)

_client: redis_async.Redis | None = None
_init_attempted = False


async def get_redis() -> redis_async.Redis | None:
    """Return a shared async-Redis client, or ``None`` if Redis is unreachable.

    Cached across requests after the first successful connect; a failure is
    cached too so we don't hammer the server on every request when Redis is
    down (the cached ``None`` is cleared via :func:`reset_redis`).
    """
    global _client, _init_attempted
    if _client is not None:
        return _client
    if _init_attempted:
        return None
    _init_attempted = True
    try:
        client = redis_async.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )
        # redis-py types ping() as Awaitable[bool] | bool depending on sync vs
        # async client; under ``redis.asyncio`` it's always awaitable at runtime,
        # but the type stubs union both. Cast to make mypy happy.
        from typing import Any  # local import keeps top-level imports clean
        await cast("Any", client.ping())
        _client = client
        log.info("redis.connected", url=_redact(settings.redis_url))
        return _client
    except Exception as exc:  # noqa: BLE001 — caller intentionally degrades
        log.warning("redis.unreachable", error=str(exc))
        return None


async def reset_redis() -> None:
    """Tear down the cached client (used by tests + on graceful shutdown)."""
    global _client, _init_attempted
    if _client is not None:
        with contextlib.suppress(Exception):
            await _client.aclose()
    _client = None
    _init_attempted = False


def _redact(url: str) -> str:
    """Strip credentials from a Redis URL before logging it."""
    if "@" not in url:
        return url
    scheme, _, tail = url.partition("://")
    return f"{scheme}://***@{tail.split('@', 1)[1]}"
