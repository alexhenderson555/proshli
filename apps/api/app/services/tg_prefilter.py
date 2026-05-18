"""Batch prefilter — find unpublished vacancies and enqueue them.

The publication pipeline is split in two so each side stays simple:

* :mod:`app.services.tg_publication` is the per-vacancy unit of work
  (filter → classify → render → INSERT). Pure-ish, easy to test.
* This module is the batch driver: scan ``vacancies`` for rows that
  don't yet have a ``publication_queue`` entry for the requested
  target, then call :func:`enqueue_vacancy` on each.

The driver is intentionally idempotent — the unique constraint on
``(vacancy_id, target)`` is the source of truth for dedup, so even if
the same vacancy slips through the candidate query twice (race with a
concurrent worker), the second insert is a no-op via :func:`is_duplicate`
inside :func:`enqueue_vacancy`.

Recency window: we only consider vacancies posted in the last 14 days.
Older rows are backlog — if they didn't make it into the queue when
fresh, re-publishing them weeks later spams the channel with stale
listings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import structlog
from app.config import settings
from app.models import PublicationQueueItem, Vacancy
from app.services.tg_publication import enqueue_vacancy
from app.time_utils import now_utc
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


# Vacancies older than this don't get auto-queued — operator can still
# manually publish via admin tools (Wave-late).
_RECENCY_DAYS = 14


@dataclass(frozen=True, slots=True)
class PrefilterRunResult:
    """Tally of one prefilter sweep — what the Celery wrapper logs.

    ``considered`` is the candidate set size; ``enqueued`` is how many
    actually got a ``publication_queue`` row; the difference is rows
    rejected by the filter gates (description too short, recruiter
    agency, no signal, duplicate). ``failed`` covers exceptions raised
    while classifying or rendering a single row — we never let one
    poison row sink the batch.
    """

    considered: int
    enqueued: int
    rejected: int
    failed: int

    def as_dict(self) -> dict[str, int]:
        return {
            "considered": self.considered,
            "enqueued": self.enqueued,
            "rejected": self.rejected,
            "failed": self.failed,
        }


async def find_unqueued_vacancies(
    db: AsyncSession,
    *,
    target: str = "group",
    limit: int = 200,
    recency_days: int = _RECENCY_DAYS,
) -> list[Vacancy]:
    """Return recently-ingested vacancies with no queue row for ``target``.

    The ``NOT EXISTS`` correlated sub-query is the right shape because
    ``publication_queue`` is bound to grow fast — a left-join with NULL
    check would force the planner to keep building bigger and bigger
    join intermediates. The compound index ``(vacancy_id, target)``
    on the queue table makes the existence probe cheap.
    """
    cutoff = now_utc() - timedelta(days=recency_days)
    stmt = (
        select(Vacancy)
        .where(Vacancy.published_at >= cutoff)
        .where(Vacancy.is_active.is_(True))
        .where(Vacancy.is_deleted.is_(False))
        .where(
            ~exists().where(
                (PublicationQueueItem.vacancy_id == Vacancy.id)
                & (PublicationQueueItem.target == target)
            )
        )
        .order_by(Vacancy.published_at.desc())
        .limit(limit)
    )
    return list((await db.scalars(stmt)).all())


async def prefilter_batch(
    db: AsyncSession,
    *,
    target: str = "group",
    limit: int = 200,
) -> PrefilterRunResult:
    """Run the prefilter over a batch of unqueued vacancies.

    Each row gets its own try/except so a single misbehaving classifier
    call (network blip, malformed LLM output) doesn't take the rest of
    the batch down with it. The session is committed by the surrounding
    ``run_with_session`` wrapper.
    """
    base_url = settings.app_base_url
    candidates = await find_unqueued_vacancies(db, target=target, limit=limit)

    enqueued = 0
    rejected = 0
    failed = 0
    for vacancy in candidates:
        try:
            queue_id = await enqueue_vacancy(
                db,
                vacancy,
                target=target,
                base_url=base_url,
                locale="ru",
            )
        except Exception as exc:  # noqa: BLE001 - intentional: never let one row sink the batch
            log.warning(
                "tg_prefilter.enqueue_failed",
                vacancy_id=vacancy.id,
                error=str(exc),
            )
            failed += 1
            continue
        if queue_id is None:
            rejected += 1
        else:
            enqueued += 1

    return PrefilterRunResult(
        considered=len(candidates),
        enqueued=enqueued,
        rejected=rejected,
        failed=failed,
    )
