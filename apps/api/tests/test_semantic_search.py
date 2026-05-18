"""Integration tests for the semantic-search route (wave 4).

Three angles:

* Tier gate — free users get 402 with the upgrade copy.
* Ranking — a deterministic fake embedding service produces vectors that
  put the matching vacancy first in cosine-distance order.
* Backfill helper — fills NULL ``embedding`` rows in a single batch.

We monkeypatch :func:`app.services.embeddings.get_embedding_service` *and*
the module-local binding in ``app.routes.vacancies`` — same dance as the
LLM tests, otherwise the route closes over the original symbol at import
time and never sees the override.
"""

from __future__ import annotations

import pytest
from app.db import async_session_factory
from app.models import Plan, Subscription, Vacancy
from app.routes import vacancies as vac_route
from app.services import embeddings as emb_module
from app.services.embeddings import EMBEDDING_DIM, RuleBasedEmbeddingService
from app.services.semantic_search import backfill_vacancy_embeddings
from app.time_utils import now_utc
from httpx import AsyncClient
from sqlalchemy import delete, select
from tests.helpers import auth_headers, register_test_user


class _DeterministicEmbedder:
    """Maps known phrases to specific 1024-d one-hot-ish vectors.

    Used to force a known cosine ordering without depending on either the
    rule-based hash or a network call. Each phrase gets a unit vector
    along a distinct axis; unrelated phrases hash through the rule-based
    fallback (cosine ≈ 0) so the planted match sorts to the top.
    """

    name = "test_deterministic"
    dim = EMBEDDING_DIM

    def __init__(self, *, axes: dict[str, int]) -> None:
        self._axes = axes
        self._fallback = RuleBasedEmbeddingService()

    async def embed_texts(
        self, texts: list[str], *, input_type: str = "document"
    ) -> list[list[float]]:
        del input_type
        out: list[list[float]] = []
        for text in texts:
            axis = None
            for phrase, idx in self._axes.items():
                if phrase in text:
                    axis = idx
                    break
            if axis is not None:
                vec = [0.0] * EMBEDDING_DIM
                vec[axis] = 1.0
                out.append(vec)
            else:
                [v] = await self._fallback.embed_texts([text])
                out.append(v)
        return out


async def _ensure_plan(slug: str, *, semantic_search: bool) -> int:
    """Idempotent plan seeding for tier-gate tests."""
    async with async_session_factory() as session:
        existing = (
            await session.execute(select(Plan).where(Plan.slug == slug))
        ).scalar_one_or_none()
        if existing is not None:
            existing.semantic_search = semantic_search
            await session.commit()
            return existing.id
        plan = Plan(
            slug=slug,
            name_ru=slug.title(),
            price_rub=0 if slug == "free" else 490,
            ai_daily_limit=50,
            semantic_search=semantic_search,
            digest_frequency="daily",
            created_at=now_utc(),
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
        return plan.id


async def _attach_subscription(email: str, plan_slug: str) -> None:
    async with async_session_factory() as session:
        from app.models import User as UserM

        user_id = (
            await session.execute(select(UserM.id).where(UserM.email == email))
        ).scalar_one()
        plan_id = (
            await session.execute(select(Plan.id).where(Plan.slug == plan_slug))
        ).scalar_one()
        existing = (
            await session.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.plan_id = plan_id
            existing.status = "active"
        else:
            session.add(
                Subscription(
                    user_id=user_id,
                    plan_id=plan_id,
                    status="active",
                    created_at=now_utc(),
                    updated_at=now_utc(),
                )
            )
        await session.commit()


# ----------------------------------------------------------------- tier gate


@pytest.mark.asyncio
async def test_free_tier_gets_402_for_semantic_search(client: AsyncClient) -> None:
    """A user on the free plan (or no plan) must be turned away with 402."""
    await _ensure_plan("free", semantic_search=False)

    email, token, cleanup = await register_test_user(client, role="seeker")
    try:
        await _attach_subscription(email, "free")
        resp = await client.get(
            "/vacancies/search/semantic",
            params={"q": "senior python remote"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 402, resp.text
        # The error copy nudges towards an upgrade — that's the whole
        # point of returning 402 instead of silently degrading.
        assert "Pro" in resp.json()["detail"]
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_pro_tier_can_call_semantic_search(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Pro-plan user should get a 200 even if the result set is empty."""
    await _ensure_plan("pro", semantic_search=True)
    # Force the rule-based fallback so this test is hermetic.
    emb_module.get_embedding_service.cache_clear()
    monkeypatch.setattr(emb_module.settings, "voyage_api_key", "")
    fake = RuleBasedEmbeddingService()
    monkeypatch.setattr(emb_module, "get_embedding_service", lambda: fake)
    monkeypatch.setattr(vac_route, "get_embedding_service", lambda: fake)

    email, token, cleanup = await register_test_user(client, role="seeker")
    try:
        await _attach_subscription(email, "pro")
        resp = await client.get(
            "/vacancies/search/semantic",
            params={"q": "any query", "limit": 5},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), list)
    finally:
        await cleanup()


# -------------------------------------------------------------- ranking + ordering


@pytest.mark.asyncio
async def test_semantic_search_orders_by_query_match(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The vacancy whose embedding sits on the same axis as the query must
    come back first, ahead of an unrelated row."""
    await _ensure_plan("pro", semantic_search=True)

    embedder = _DeterministicEmbedder(
        axes={
            "Senior Python": 7,
            "Junior Frontend": 42,
        }
    )
    monkeypatch.setattr(emb_module, "get_embedding_service", lambda: embedder)
    monkeypatch.setattr(vac_route, "get_embedding_service", lambda: embedder)

    # Two employer-owned vacancies, each indexed by the deterministic embedder
    # the moment they're created.
    employer_email, emp_token, emp_cleanup = await register_test_user(
        client, role="employer"
    )
    seeker_email, seeker_token, seeker_cleanup = await register_test_user(
        client, role="seeker"
    )
    try:
        await _attach_subscription(seeker_email, "pro")
        await client.post(
            "/vacancies",
            json={
                "source": "manual",
                "external_id": "sem-python-1",
                "title": "Senior Python Engineer",
                "company": "Proshli",
                "location": "Remote",
                "description": "Senior Python — FastAPI, asyncio.",
            },
            headers=auth_headers(emp_token),
        )
        await client.post(
            "/vacancies",
            json={
                "source": "manual",
                "external_id": "sem-front-1",
                "title": "Junior Frontend Developer",
                "company": "Proshli",
                "location": "Moscow",
                "description": "Junior Frontend — React, TypeScript.",
            },
            headers=auth_headers(emp_token),
        )

        resp = await client.get(
            "/vacancies/search/semantic",
            params={"q": "Senior Python", "limit": 10},
            headers=auth_headers(seeker_token),
        )
        assert resp.status_code == 200, resp.text
        rows = resp.json()
        assert len(rows) >= 1
        titles = [r["title"] for r in rows]
        # The python row must appear and must beat the frontend one when
        # the latter is even returned (it might be, because rule-based
        # vectors are non-zero too — but cosine to the python axis is 0
        # for them).
        assert "Senior Python Engineer" in titles
        py_idx = titles.index("Senior Python Engineer")
        if "Junior Frontend Developer" in titles:
            fe_idx = titles.index("Junior Frontend Developer")
            assert py_idx < fe_idx
    finally:
        # ``emp_cleanup`` already DELETEs vacancies owned by the employer
        # through the ``employer_vacancies`` join, so we don't need an
        # additional bulk delete here — that would race with the FK
        # constraint if another test happens to share the external_id.
        await seeker_cleanup()
        await emp_cleanup()


# ------------------------------------------------------------ backfill helper


@pytest.mark.asyncio
async def test_backfill_fills_only_null_embeddings() -> None:
    """``backfill_vacancy_embeddings`` updates exactly the NULL rows and
    skips ones that already have a vector."""
    embedder = RuleBasedEmbeddingService()

    async with async_session_factory() as session:
        seed = Vacancy(
            source="manual",
            external_id="bf-null-1",
            title="Backend Engineer",
            company="Proshli",
            location="Remote",
            description="Backend Engineer position — Go, kafka.",
            published_at=now_utc(),
        )
        already_filled = Vacancy(
            source="manual",
            external_id="bf-filled-1",
            title="ML Engineer",
            company="Proshli",
            location="Moscow",
            description="ML Engineer — pytorch.",
            embedding=[0.5] * EMBEDDING_DIM,
            published_at=now_utc(),
        )
        session.add_all([seed, already_filled])
        await session.commit()
        await session.refresh(seed)
        await session.refresh(already_filled)
        original_filled_first = already_filled.embedding[0]

        updated = await backfill_vacancy_embeddings(
            session, embedder, batch_size=50
        )
        assert updated >= 1

        # Re-read with a fresh query to bypass the identity-map cache.
        refreshed_seed = await session.scalar(
            select(Vacancy).where(Vacancy.id == seed.id)
        )
        refreshed_filled = await session.scalar(
            select(Vacancy).where(Vacancy.id == already_filled.id)
        )
        assert refreshed_seed is not None and refreshed_seed.embedding is not None
        assert refreshed_filled is not None
        # The pre-filled row's embedding must remain untouched.
        assert refreshed_filled.embedding[0] == original_filled_first

        # Clean up.
        await session.execute(
            delete(Vacancy).where(
                Vacancy.external_id.in_(["bf-null-1", "bf-filled-1"])
            )
        )
        await session.commit()


def test_rule_based_embedder_is_deterministic_and_normalised() -> None:
    """Smoke check: same input twice → identical vector; magnitude == 1."""
    import asyncio

    svc = RuleBasedEmbeddingService()

    async def _run() -> tuple[list[float], list[float]]:
        [a] = await svc.embed_texts(["Senior Python в Москве"])
        [b] = await svc.embed_texts(["Senior Python в Москве"])
        return a, b

    a, b = asyncio.run(_run())
    assert a == b
    mag_sq = sum(x * x for x in a)
    # Allow a tiny float epsilon.
    assert abs(mag_sq - 1.0) < 1e-6
