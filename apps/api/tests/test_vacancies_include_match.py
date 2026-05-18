"""Integration tests for the ``include_match`` query param on GET /vacancies.

Four scenarios:
1. Anonymous caller with ``include_match=true`` → match fields are None.
2. Authed seeker with a resume + a matching vacancy → match_score ≈ 1.0, tier "strong".
3. Authed seeker with no resume → match fields are None.
4. ``include_match=false`` (the default) → match fields absent / None.
"""

from __future__ import annotations

import io
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.helpers import auth_headers, register_test_user

from app.db import async_session_factory
from app.models import Resume, User, Vacancy
from app.time_utils import now_utc


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_vacancy_with_embedding(
    db: AsyncSession,
    *,
    title: str = "Python Backend Engineer",
    embedding: list[float] | None = None,
) -> Vacancy:
    """Insert a vacancy directly; optionally attach an embedding for scoring."""
    v = Vacancy(
        source="manual",
        external_id=f"match-test-{uuid.uuid4().hex[:8]}",
        title=title,
        company="Proshli Test",
        location="Remote",
        employment_type="full-time",
        experience_level="middle",
        salary_from=None,
        salary_to=None,
        currency="RUB",
        description="FastAPI, Python, PostgreSQL",
        applications_count=0,
        published_at=now_utc(),
        is_active=True,
        is_deleted=False,
        is_promoted=False,
    )
    db.add(v)
    await db.commit()
    await db.refresh(v)

    if embedding is not None:
        # Assign the embedding column directly with raw SQL to bypass
        # potential ORM type friction around pgvector.
        from sqlalchemy import text
        await db.execute(
            text("UPDATE vacancies SET embedding = CAST(:emb AS vector) WHERE id = :vid"),
            {"emb": str(embedding), "vid": v.id},
        )
        await db.commit()
        await db.refresh(v)

    return v


async def _create_user_with_resume(
    db: AsyncSession,
    *,
    embedding: list[float],
) -> tuple[User, Resume]:
    """Create a seeker user with a resume that has the given embedding."""
    user = User(
        email=_uid("match"),
        password_hash="x",
        role="seeker",
        created_at=now_utc(),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    resume = Resume(
        user_id=user.id,
        name="Test CV",
        raw_text="Python developer FastAPI",
        parsed_skills="python,fastapi",
        embedding=embedding,
        created_at=now_utc(),
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    return user, resume


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anonymous_include_match_returns_none_scores(client: AsyncClient) -> None:
    """Anonymous caller + include_match=true → match_score and match_tier are None."""
    async with async_session_factory() as db:
        vacancy = await _create_vacancy_with_embedding(
            db, embedding=[0.9] * 1024
        )
        vid = vacancy.id

    try:
        resp = await client.get(
            "/vacancies",
            params={"include_match": "true", "include_live_hh": "false"},
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        target = next((item for item in items if item["id"] == vid), None)
        assert target is not None, "Created vacancy must appear in the listing"
        assert target["match_score"] is None
        assert target["match_tier"] is None
    finally:
        async with async_session_factory() as db:
            v = await db.get(Vacancy, vid)
            if v:
                v.is_deleted = True
                await db.commit()


@pytest.mark.asyncio
async def test_authed_seeker_with_resume_gets_match_score(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Authed seeker with a resume embedding matching the vacancy → score ≈ 1.0, tier 'strong'."""
    # Use a deterministic unit vector so cosine similarity = 1.0
    emb = [1.0] + [0.0] * 1023

    async with async_session_factory() as db:
        vacancy = await _create_vacancy_with_embedding(db, embedding=emb)
        vid = vacancy.id
        user, resume = await _create_user_with_resume(db, embedding=emb)

    # Build a JWT token for this user via the register path is not possible
    # since user was created directly. Use create_access_token instead.
    from app.auth import create_access_token
    token = create_access_token(str(user.id))
    headers = auth_headers(token)

    try:
        resp = await client.get(
            "/vacancies",
            params={"include_match": "true", "include_live_hh": "false"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        target = next((item for item in items if item["id"] == vid), None)
        assert target is not None, "Created vacancy must appear in the listing"
        assert target["match_score"] is not None
        assert abs(target["match_score"] - 1.0) < 0.05, (
            f"Expected score ≈ 1.0 for identical embeddings, got {target['match_score']}"
        )
        assert target["match_tier"] == "strong"
    finally:
        async with async_session_factory() as db:
            v = await db.get(Vacancy, vid)
            if v:
                v.is_deleted = True
                await db.commit()
            r = await db.get(Resume, resume.id)
            if r:
                await db.delete(r)
                await db.commit()
            u = await db.get(User, user.id)
            if u:
                await db.delete(u)
                await db.commit()


@pytest.mark.asyncio
async def test_authed_seeker_without_resume_gets_none_scores(client: AsyncClient) -> None:
    """Authed seeker with no resume → match_score and match_tier stay None."""
    _, token, cleanup = await register_test_user(client, role="seeker")
    headers = auth_headers(token)

    async with async_session_factory() as db:
        vacancy = await _create_vacancy_with_embedding(
            db, embedding=[0.5] * 1024
        )
        vid = vacancy.id

    try:
        resp = await client.get(
            "/vacancies",
            params={"include_match": "true", "include_live_hh": "false"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        target = next((item for item in items if item["id"] == vid), None)
        assert target is not None, "Created vacancy must appear in the listing"
        assert target["match_score"] is None
        assert target["match_tier"] is None
    finally:
        async with async_session_factory() as db:
            v = await db.get(Vacancy, vid)
            if v:
                v.is_deleted = True
                await db.commit()
        await cleanup()


@pytest.mark.asyncio
async def test_include_match_false_default_no_score_fields(client: AsyncClient) -> None:
    """Without include_match (default false) the listing still works and match fields are None."""
    async with async_session_factory() as db:
        vacancy = await _create_vacancy_with_embedding(
            db, embedding=[0.3] * 1024
        )
        vid = vacancy.id

    try:
        # Default (no include_match param)
        resp = await client.get(
            "/vacancies",
            params={"include_live_hh": "false"},
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        target = next((item for item in items if item["id"] == vid), None)
        assert target is not None, "Created vacancy must appear in the listing"
        # match_score / match_tier should be None (or absent, treated as None)
        assert target.get("match_score") is None
        assert target.get("match_tier") is None
    finally:
        async with async_session_factory() as db:
            v = await db.get(Vacancy, vid)
            if v:
                v.is_deleted = True
                await db.commit()
