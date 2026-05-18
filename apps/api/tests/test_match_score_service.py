"""Unit tests for app.services.match_score (Task 3 / match-score wave).

The three async tests require a live DB session (the shared test DB is
bootstrapped by the session-scoped ``_bootstrap_schema`` fixture in
conftest.py). No network calls are made — the embedding service is either
not invoked (embedding already present) or monkeypatched to a fake.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Resume, User
from app.time_utils import now_utc


def _uid(prefix: str) -> str:
    """Return a unique email-safe string for a test user."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test"


# ---------------------------------------------------------------------------
# Pure-function tests — no DB, no async
# ---------------------------------------------------------------------------


def test_match_tier_thresholds():
    from app.services.match_score import match_tier

    assert match_tier(0.95) == "strong"
    assert match_tier(0.80) == "strong"
    assert match_tier(0.799) == "decent"
    assert match_tier(0.60) == "decent"
    assert match_tier(0.59) == "stretch"
    assert match_tier(0.40) == "stretch"
    assert match_tier(0.39) == "longshot"
    assert match_tier(0.0) == "longshot"


def test_cosine_similarity_known_vectors():
    from app.services.match_score import cosine_similarity

    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(1.0)
    c = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, c) == pytest.approx(0.0)
    d = [-1.0, 0.0, 0.0]
    assert cosine_similarity(a, d) == pytest.approx(-1.0)


# ---------------------------------------------------------------------------
# Async tests — require db_session fixture
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_resume_embedding_returns_most_recent(db_session: AsyncSession):
    from app.services.match_score import user_resume_embedding

    user = User(
        email=_uid("recent"), password_hash="x", role="seeker", created_at=now_utc()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    older = Resume(
        user_id=user.id,
        name="old",
        raw_text="x",
        parsed_skills="",
        embedding=[0.1] * 1024,
        created_at=now_utc(),
    )
    db_session.add(older)
    await db_session.commit()

    await asyncio.sleep(0.01)
    newer = Resume(
        user_id=user.id,
        name="new",
        raw_text="y",
        parsed_skills="",
        embedding=[0.2] * 1024,
        created_at=now_utc(),
    )
    db_session.add(newer)
    await db_session.commit()

    emb = await user_resume_embedding(db_session, user.id)
    assert emb is not None
    assert emb[0] == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_user_resume_embedding_none_when_no_resume(db_session: AsyncSession):
    from app.services.match_score import user_resume_embedding

    user = User(
        email=_uid("empty"), password_hash="x", role="seeker", created_at=now_utc()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    emb = await user_resume_embedding(db_session, user.id)
    assert emb is None


@pytest.mark.asyncio
async def test_user_resume_embedding_backfills_when_null(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    from app.services.match_score import user_resume_embedding

    class FakeService:
        name = "fake"
        dim = 1024

        async def embed_texts(self, texts, *, input_type="document"):
            return [[0.5] * 1024 for _ in texts]

    monkeypatch.setattr(
        "app.services.match_score.get_embedding_service",
        lambda: FakeService(),
    )

    user = User(
        email=_uid("bf"), password_hash="x", role="seeker", created_at=now_utc()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    r = Resume(
        user_id=user.id,
        name="r",
        raw_text="content for embed",
        parsed_skills="",
        embedding=None,
        created_at=now_utc(),
    )
    db_session.add(r)
    await db_session.commit()
    await db_session.refresh(r)

    emb = await user_resume_embedding(db_session, user.id)
    assert emb is not None
    assert emb[0] == pytest.approx(0.5)

    await db_session.refresh(r)
    assert r.embedding is not None
