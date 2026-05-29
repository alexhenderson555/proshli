"""Smoke test for the anonymous ``GET /vacancies/stats`` endpoint.

The landing-page hero strip depends on this endpoint to replace the
old hard-coded "40+ / 10× / 24/7" placeholders with live counters.
The contract: anonymous-readable, returns ``{total, last_24h, sources}``
with non-negative integers.
"""

from __future__ import annotations

import uuid

import pytest
from app.models import Vacancy
from app.time_utils import now_utc
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_vacancy_stats_anonymous_smoke(client: AsyncClient) -> None:
    resp = await client.get("/vacancies/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"total", "last_24h", "sources"}
    assert isinstance(body["total"], int) and body["total"] >= 0
    assert isinstance(body["last_24h"], int) and body["last_24h"] >= 0
    assert isinstance(body["sources"], int) and body["sources"] >= 0
    assert body["last_24h"] <= body["total"]


@pytest.mark.asyncio
async def test_vacancy_stats_counts_active_vacancies(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Inserting a non-deleted active vacancy bumps ``total`` and ``last_24h``.

    Uses ``db_session`` directly (not the HTTP route) so we don't burn
    the shared auth-register rate limit when the suite runs alongside
    other tests.
    """
    before = (await client.get("/vacancies/stats")).json()
    vac = Vacancy(
        source=f"stats-test-{uuid.uuid4().hex[:8]}",
        external_id=f"stats-{uuid.uuid4().hex[:10]}",
        title="Stats Engineer",
        company="Proshli",
        location="Remote",
        description="stats",
        published_at=now_utc(),
        is_active=True,
        is_deleted=False,
    )
    db_session.add(vac)
    await db_session.commit()
    try:
        after = (await client.get("/vacancies/stats")).json()
        assert after["total"] == before["total"] + 1
        assert after["last_24h"] == before["last_24h"] + 1
        # The source slug is unique per test invocation, so the distinct
        # count must have grown by exactly one.
        assert after["sources"] == before["sources"] + 1
    finally:
        await db_session.delete(vac)
        await db_session.commit()
