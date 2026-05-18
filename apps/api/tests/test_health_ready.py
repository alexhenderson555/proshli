"""Readiness probe tests (wave 7).

``/health`` must always be 200 (liveness — process is up).
``/health/ready`` returns the per-dep state. In the in-process test client we
hit a live Postgres (the bootstrap fixture created the schema) but Redis is
not available, so we assert the shape rather than 200 status.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_always_ok(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "proshli-api"


@pytest.mark.asyncio
async def test_readiness_returns_per_dependency_status(client: AsyncClient) -> None:
    resp = await client.get("/health/ready")
    # 200 if both DB+Redis are up, 503 otherwise. Either way the body shape
    # must be a per-dep status map.
    assert resp.status_code in {200, 503}
    body = resp.json()
    assert set(body.keys()) == {"db", "redis"}
    assert body["db"] in {"ok", "down"}
    assert body["redis"] in {"ok", "down"}
