"""Integration tests for GET /vacancies/{vacancy_id}/match-score.

Four scenarios:
1. Authed seeker with a resume + vacancy embedding that match → score ≈ 1.0, tier "strong".
2. Authed seeker with no resume → 404.
3. Anonymous request → 401.
4. Authed seeker, vacancy has no embedding → 404.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.auth import create_access_token
from app.db import async_session_factory
from app.models import Resume, User, Vacancy
from app.time_utils import now_utc
from tests.helpers import auth_headers, register_test_user


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test"


# ---------------------------------------------------------------------------
# Helpers (reuse patterns from test_vacancies_include_match.py)
# ---------------------------------------------------------------------------


async def _create_vacancy_with_embedding(
    *,
    embedding: list[float] | None = None,
) -> Vacancy:
    """Insert a vacancy; optionally attach an embedding."""
    async with async_session_factory() as db:
        v = Vacancy(
            source="manual",
            external_id=f"ms-test-{uuid.uuid4().hex[:8]}",
            title="Python Backend Engineer",
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
            from sqlalchemy import text

            await db.execute(
                text(
                    "UPDATE vacancies SET embedding = CAST(:emb AS vector) WHERE id = :vid"
                ),
                {"emb": str(embedding), "vid": v.id},
            )
            await db.commit()
            await db.refresh(v)

        return v


async def _create_user_with_resume(
    *,
    embedding: list[float],
) -> tuple[User, Resume]:
    """Create a seeker user with a resume that has the given embedding."""
    async with async_session_factory() as db:
        user = User(
            email=_uid("ms"),
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


async def _delete_vacancy(vacancy_id: int) -> None:
    async with async_session_factory() as db:
        v = await db.get(Vacancy, vacancy_id)
        if v:
            v.is_deleted = True
            await db.commit()


async def _delete_user_and_resume(user_id: int, resume_id: int) -> None:
    async with async_session_factory() as db:
        r = await db.get(Resume, resume_id)
        if r:
            await db.delete(r)
            await db.commit()
        u = await db.get(User, user_id)
        if u:
            await db.delete(u)
            await db.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_match_score_with_matching_resume_and_vacancy(client: AsyncClient) -> None:
    """Authed seeker with matching resume + vacancy embedding → score ≈ 1.0, tier 'strong'."""
    emb = [1.0] + [0.0] * 1023

    vacancy = await _create_vacancy_with_embedding(embedding=emb)
    user, resume = await _create_user_with_resume(embedding=emb)

    token = create_access_token(str(user.id))
    headers = auth_headers(token)

    try:
        resp = await client.get(
            f"/vacancies/{vacancy.id}/match-score",
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "score" in body
        assert "tier" in body
        assert abs(body["score"] - 1.0) < 0.05, (
            f"Expected score ≈ 1.0 for identical embeddings, got {body['score']}"
        )
        assert body["tier"] == "strong"
    finally:
        await _delete_vacancy(vacancy.id)
        await _delete_user_and_resume(user.id, resume.id)


@pytest.mark.asyncio
async def test_match_score_no_resume_returns_404(client: AsyncClient) -> None:
    """Authed seeker with no resume → 404."""
    _, token, cleanup = await register_test_user(client, role="seeker")
    headers = auth_headers(token)

    vacancy = await _create_vacancy_with_embedding(embedding=[0.5] * 1024)

    try:
        resp = await client.get(
            f"/vacancies/{vacancy.id}/match-score",
            headers=headers,
        )
        assert resp.status_code == 404, resp.text
        assert "resume" in resp.json()["detail"].lower()
    finally:
        await _delete_vacancy(vacancy.id)
        await cleanup()


@pytest.mark.asyncio
async def test_match_score_anonymous_returns_401(client: AsyncClient) -> None:
    """Anonymous request → 401 (get_current_user raises HTTP 401)."""
    vacancy = await _create_vacancy_with_embedding(embedding=[0.5] * 1024)

    try:
        resp = await client.get(f"/vacancies/{vacancy.id}/match-score")
        assert resp.status_code == 401, resp.text
    finally:
        await _delete_vacancy(vacancy.id)


@pytest.mark.asyncio
async def test_match_score_vacancy_no_embedding_returns_404(client: AsyncClient) -> None:
    """Authed seeker, vacancy has no embedding → 404."""
    emb = [1.0] + [0.0] * 1023

    # Vacancy created WITHOUT an embedding
    vacancy = await _create_vacancy_with_embedding(embedding=None)
    user, resume = await _create_user_with_resume(embedding=emb)

    token = create_access_token(str(user.id))
    headers = auth_headers(token)

    try:
        resp = await client.get(
            f"/vacancies/{vacancy.id}/match-score",
            headers=headers,
        )
        assert resp.status_code == 404, resp.text
        assert "embed" in resp.json()["detail"].lower()
    finally:
        await _delete_vacancy(vacancy.id)
        await _delete_user_and_resume(user.id, resume.id)
