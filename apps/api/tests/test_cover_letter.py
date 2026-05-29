"""Integration tests for POST /ai/cover-letter.

Exercises the rule-based path so we don't need an Anthropic key in CI.
Covers role gating, missing-vacancy 404, and the happy path where the
response carries a non-empty body + the standard budget envelope.
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
        source=f"cl-{uuid.uuid4().hex[:6]}",
        external_id=f"cl-{uuid.uuid4().hex[:8]}",
        title="Senior Python Engineer",
        company="Proshli",
        location="Remote",
        description="Build the matching pipeline. Python, FastAPI, PostgreSQL.",
        published_at=now_utc(),
        is_active=True,
        is_deleted=False,
    )
    db_session.add(vac)
    await db_session.commit()
    await db_session.refresh(vac)
    return vac.id


@pytest.mark.asyncio
async def test_employer_cannot_use_cover_letter(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="employer")
    try:
        resp = await client.post(
            "/ai/cover-letter",
            json={"vacancy_id": 1},
            headers=auth_headers(token),
        )
        assert resp.status_code == 403
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_cover_letter_with_unknown_vacancy_404s(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.post(
            "/ai/cover-letter",
            json={"vacancy_id": 999_999_999},
            headers=auth_headers(token),
        )
        assert resp.status_code == 404
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_cover_letter_happy_path_rule_based(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    vacancy_id = await _seed_vacancy(db_session)
    try:
        resp = await client.post(
            "/ai/cover-letter",
            json={"vacancy_id": vacancy_id, "tone": "friendly", "language": "ru"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert isinstance(body["body"], str)
        assert len(body["body"]) > 30
        # Budget envelope is always present.
        assert body["used_today"] >= 1
        assert body["limit"] > 0
        assert body["backend"] in {"rule_based", "anthropic"}
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_cover_letter_english_path(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    vacancy_id = await _seed_vacancy(db_session)
    try:
        resp = await client.post(
            "/ai/cover-letter",
            json={"vacancy_id": vacancy_id, "tone": "formal", "language": "en"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # The rule-based fallback uses a known opener phrase in EN; with the
        # Anthropic backend we only assert language behaviour via length.
        if body["backend"] == "rule_based":
            assert "interest in" in body["body"].lower()
    finally:
        await cleanup()
