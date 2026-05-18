"""Prefilter batch task — integration test against the shared API DB.

Seeds a small set of vacancies, runs ``prefilter_batch`` against the
real session, and asserts the queue grows by the expected amount.

The classifier and summary side calls go through their default
implementations: with no ``ANTHROPIC_API_KEY`` the classifier degrades
to the rule-based path and the summary stays a deterministic
first-sentence snippet, so we don't need to mock either.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import timedelta

import pytest
import pytest_asyncio
import workers  # noqa: F401  -- side-effect: extends sys.path with ../api/
from app.db import Base, async_session_factory, engine
from app.models import PublicationQueueItem, Vacancy
from app.services.tg_prefilter import (
    PrefilterRunResult,
    find_unqueued_vacancies,
    prefilter_batch,
)
from app.time_utils import now_utc
from sqlalchemy import delete, select


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _bootstrap_schema() -> AsyncIterator[None]:
    """One-shot schema create — workers don't ship alembic of their own."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


async def _seed_vacancy(
    *,
    title: str = "Senior Python Engineer",
    company: str = "Yandex",
    description: str = "",
    salary_from: int | None = 250_000,
    salary_to: int | None = 400_000,
    published_offset_days: int = 0,
) -> int:
    """Insert a fresh vacancy; returns its id."""
    if not description:
        description = (
            "Большая команда продуктового бэкенда. Python 3.12, FastAPI, "
            "PostgreSQL, k8s. От senior — 4+ года опыта."
        )
    async with async_session_factory() as session:
        v = Vacancy(
            source="test",
            external_id=f"ext-{uuid.uuid4().hex[:10]}",
            title=title,
            company=company,
            location="Москва",
            description=description,
            salary_from=salary_from,
            salary_to=salary_to,
            published_at=now_utc() - timedelta(days=published_offset_days),
        )
        session.add(v)
        await session.commit()
        await session.refresh(v)
        return v.id


async def _cleanup(vacancy_ids: list[int]) -> None:
    if not vacancy_ids:
        return
    async with async_session_factory() as session:
        await session.execute(
            delete(PublicationQueueItem).where(
                PublicationQueueItem.vacancy_id.in_(vacancy_ids)
            )
        )
        await session.execute(delete(Vacancy).where(Vacancy.id.in_(vacancy_ids)))
        await session.commit()


@pytest.mark.asyncio
async def test_find_unqueued_skips_already_queued_rows() -> None:
    """If a queue row exists for the (vacancy, target) pair, it's filtered."""
    queued_id = await _seed_vacancy()
    fresh_id = await _seed_vacancy()
    try:
        # Pretend the first one already has a queue entry for 'group'.
        async with async_session_factory() as session:
            session.add(
                PublicationQueueItem(
                    vacancy_id=queued_id,
                    target="group",
                    rendered_text="already-queued",
                    status="pending",
                )
            )
            await session.commit()

        async with async_session_factory() as session:
            candidates = await find_unqueued_vacancies(
                session, target="group", limit=50
            )
        candidate_ids = {v.id for v in candidates}
        assert queued_id not in candidate_ids
        assert fresh_id in candidate_ids
    finally:
        await _cleanup([queued_id, fresh_id])


@pytest.mark.asyncio
async def test_find_unqueued_respects_recency_window() -> None:
    """Vacancies older than the recency cutoff don't get re-published."""
    fresh_id = await _seed_vacancy(published_offset_days=1)
    stale_id = await _seed_vacancy(published_offset_days=30)
    try:
        async with async_session_factory() as session:
            candidates = await find_unqueued_vacancies(
                session, target="group", limit=50, recency_days=14
            )
        candidate_ids = {v.id for v in candidates}
        assert fresh_id in candidate_ids
        assert stale_id not in candidate_ids
    finally:
        await _cleanup([fresh_id, stale_id])


@pytest.mark.asyncio
async def test_prefilter_batch_enqueues_eligible_and_rejects_bad(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One good vacancy enqueues; one short-description rejects on the gate."""
    from app.config import settings

    monkeypatch.setattr(settings, "app_base_url", "https://proshli.ru")

    good_id = await _seed_vacancy(
        title="Senior Python Engineer",
        company="Yandex",
    )
    short_id = await _seed_vacancy(
        title="Junior Dev",
        company="SmallCo",
        description="Hire me",  # < 100 chars → filter rejects
    )
    try:
        async with async_session_factory() as session:
            result = await prefilter_batch(session, target="group", limit=50)
            await session.commit()

        assert isinstance(result, PrefilterRunResult)
        # We may collect other unrelated test rows in the candidate set,
        # so assert the counters cover *at least* our two seeds without
        # demanding exact equality.
        assert result.considered >= 2
        assert result.enqueued >= 1
        assert result.rejected >= 1

        # The good one is now in the queue, the short one isn't.
        async with async_session_factory() as session:
            queue_rows = list(
                (
                    await session.scalars(
                        select(PublicationQueueItem).where(
                            PublicationQueueItem.vacancy_id.in_(
                                [good_id, short_id]
                            )
                        )
                    )
                ).all()
            )
        queued_vacancy_ids = {r.vacancy_id for r in queue_rows}
        assert good_id in queued_vacancy_ids
        assert short_id not in queued_vacancy_ids
    finally:
        await _cleanup([good_id, short_id])


@pytest.mark.asyncio
async def test_prefilter_batch_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running the batch twice in a row doesn't double-enqueue any row."""
    from app.config import settings

    monkeypatch.setattr(settings, "app_base_url", "https://proshli.ru")

    vacancy_id = await _seed_vacancy()
    try:
        async with async_session_factory() as session:
            await prefilter_batch(session, target="group", limit=50)
            await session.commit()
        async with async_session_factory() as session:
            second = await prefilter_batch(session, target="group", limit=50)
            await session.commit()

        # On the second pass, the queued vacancy is not re-considered
        # (it's filtered out at SELECT time).
        async with async_session_factory() as session:
            row_count = len(
                list(
                    (
                        await session.scalars(
                            select(PublicationQueueItem).where(
                                PublicationQueueItem.vacancy_id == vacancy_id
                            )
                        )
                    ).all()
                )
            )
        assert row_count == 1
        # The second batch shouldn't have enqueued our seed.
        # (Counters cover the whole candidate set; we just assert our
        # row didn't get a duplicate.)
        assert second.enqueued >= 0
    finally:
        await _cleanup([vacancy_id])
