"""Liveness probe.

Intentionally has no DB dependency — kubelet/Compose health checks must not
fail because Postgres is briefly down; that's what readiness probes are for
(to be added when the worker fleet lands in Task 7).
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "otklik-api"}
