"""Integration tests for the seeker kanban router.

Covers role gating, the 5-lane CRUD cycle, idempotent POST, and the
counts endpoint that feeds the dashboard overview.
"""

from __future__ import annotations

import uuid

import pytest
from app.models import Vacancy
from app.time_utils import now_utc
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.helpers import auth_headers, register_test_user


async def _seed_vacancy(db_session: AsyncSession) -> int:
    vac = Vacancy(
        source=f"kanban-{uuid.uuid4().hex[:6]}",
        external_id=f"kanban-{uuid.uuid4().hex[:8]}",
        title="Kanban Engineer",
        company="Proshli",
        location="Remote",
        description="kanban",
        published_at=now_utc(),
        is_active=True,
        is_deleted=False,
    )
    db_session.add(vac)
    await db_session.commit()
    await db_session.refresh(vac)
    return vac.id


@pytest.mark.asyncio
async def test_employer_cannot_use_applications(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="employer")
    try:
        resp = await client.get("/applications", headers=auth_headers(token))
        assert resp.status_code == 403
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_seeker_kanban_lifecycle(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    headers = auth_headers(token)
    vacancy_id = await _seed_vacancy(db_session)
    try:
        # Create at default "saved" lane.
        create = await client.post(
            "/applications",
            json={"vacancy_id": vacancy_id},
            headers=headers,
        )
        assert create.status_code == 201, create.text
        app_row = create.json()
        assert app_row["status"] == "saved"
        assert app_row["vacancy"]["id"] == vacancy_id

        # Idempotent re-POST returns the existing row (no 409).
        again = await client.post(
            "/applications",
            json={"vacancy_id": vacancy_id, "status": "applied"},
            headers=headers,
        )
        assert again.status_code == 201
        assert again.json()["id"] == app_row["id"]

        # Move through lanes.
        for lane in ("applied", "interview", "offer", "rejected"):
            patch = await client.patch(
                f"/applications/{app_row['id']}",
                json={"status": lane},
                headers=headers,
            )
            assert patch.status_code == 200, patch.text
            assert patch.json()["status"] == lane

        # Notes update independently.
        notes = await client.patch(
            f"/applications/{app_row['id']}",
            json={"notes": "interview scheduled monday"},
            headers=headers,
        )
        assert notes.status_code == 200
        assert notes.json()["notes"] == "interview scheduled monday"

        # Filtered list — only "rejected" rows.
        listing = await client.get(
            "/applications", params={"status": "rejected"}, headers=headers
        )
        assert listing.status_code == 200
        assert any(item["id"] == app_row["id"] for item in listing.json())

        # Counts surface one-per-lane.
        counts = await client.get("/applications/counts", headers=headers)
        assert counts.status_code == 200
        cbody = counts.json()
        assert cbody["rejected"] >= 1
        assert set(cbody.keys()) == {
            "saved",
            "applied",
            "interview",
            "offer",
            "rejected",
        }

        # Delete.
        delete = await client.delete(
            f"/applications/{app_row['id']}", headers=headers
        )
        assert delete.status_code == 200
        assert delete.json()["status"] == "deleted"

        # 404 on subsequent GET via the same id.
        gone = await client.patch(
            f"/applications/{app_row['id']}",
            json={"status": "saved"},
            headers=headers,
        )
        assert gone.status_code == 404
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_create_application_with_unknown_vacancy_404s(
    client: AsyncClient,
) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.post(
            "/applications",
            json={"vacancy_id": 999_999_999},
            headers=auth_headers(token),
        )
        assert resp.status_code == 404
    finally:
        await cleanup()
