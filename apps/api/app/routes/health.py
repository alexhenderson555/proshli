"""Liveness + readiness probes.

* ``GET /health`` is a cheap liveness check — no I/O. kubelet / Compose can
  use it without coupling app uptime to Postgres availability.
* ``GET /health/ready`` is a deep readiness check — pings Postgres and Redis
  in parallel and returns 503 if either is unreachable. Use it as the
  Kubernetes readinessProbe / Compose ``healthcheck``.

The readiness check holds the connections for at most ~1s before timing out
(via the configured socket timeouts on the asyncpg engine and the redis
client). It must not block.
"""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db import engine
from app.redis_client import get_redis

router = APIRouter(tags=["health"])
log = structlog.get_logger(__name__)


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness — always 200 unless the process is wedged."""
    return {"status": "ok", "service": "proshli-api"}


@router.get("/health/ready")
async def ready() -> JSONResponse:
    """Readiness — verifies the app can actually serve traffic."""
    db_ok, redis_ok = await asyncio.gather(
        _check_db(), _check_redis(), return_exceptions=False
    )
    payload = {
        "db": "ok" if db_ok else "down",
        "redis": "ok" if redis_ok else "down",
    }
    status_code = 200 if (db_ok and redis_ok) else 503
    return JSONResponse(status_code=status_code, content=payload)


async def _check_db() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("health.db_down", error=str(exc))
        return False


async def _check_redis() -> bool:
    from typing import Any, cast

    client = await get_redis()
    if client is None:
        return False
    try:
        # See ``redis_client.get_redis`` — ping() is typed as a union by the
        # stubs but is always awaitable under ``redis.asyncio``.
        await cast("Any", client.ping())
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("health.redis_down", error=str(exc))
        return False
