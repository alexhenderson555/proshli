"""Redis-backed sliding-bucket rate-limit dependency.

Pattern from ``reference-vault/ai-apps/vercel-ai-chatbot/lib/ratelimit.ts``:
atomic ``INCR`` + ``EXPIRE NX`` in a Redis ``MULTI`` block — one RTT per check,
no race between INCR and EXPIRE.

Designed as a FastAPI ``Depends`` you can attach per-route::

    from app.middleware.rate_limit import RateLimit

    @router.post(
        "/login",
        dependencies=[Depends(RateLimit("auth-login", limit=10, window_seconds=60))],
    )

Bucket key is ``rl:{namespace}:{ip}`` so different endpoints get independent
budgets and an aggressive client doesn't starve unrelated traffic.

If Redis is unreachable the dependency **fails open** (logs a warning, lets the
request through). The alternative — failing closed — would let one outage take
down the entire API.
"""

from __future__ import annotations

import structlog
from fastapi import HTTPException, Request, status

from app.redis_client import get_redis

log = structlog.get_logger(__name__)


class RateLimit:
    """Per-IP fixed-window rate limit.

    Args:
        namespace: identifier mixed into the Redis key (use one per endpoint
            family, e.g. ``"auth-login"`` / ``"ai-chat"``).
        limit: maximum requests per window.
        window_seconds: window length.
    """

    def __init__(self, namespace: str, *, limit: int, window_seconds: int) -> None:
        self.namespace = namespace
        self.limit = limit
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        client = await get_redis()
        if client is None:
            # Fail open: Redis outage shouldn't take the API down.
            return

        ip = _client_ip(request)
        key = f"rl:{self.namespace}:{ip}"
        try:
            async with client.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, self.window_seconds, nx=True)
                results = await pipe.execute()
            current = int(results[0])
        except Exception as exc:  # noqa: BLE001
            log.warning("ratelimit.redis_error", error=str(exc), namespace=self.namespace)
            return

        if current > self.limit:
            log.info(
                "ratelimit.exceeded",
                namespace=self.namespace,
                ip=ip,
                current=current,
                limit=self.limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests; retry in {self.window_seconds}s",
                headers={"Retry-After": str(self.window_seconds)},
            )


def _client_ip(request: Request) -> str:
    """Best-effort client IP, honouring ``X-Forwarded-For`` if a proxy set it."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",", 1)[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"
