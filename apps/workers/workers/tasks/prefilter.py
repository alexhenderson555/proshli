"""Prefilter batch task — drains newly-ingested vacancies into the queue.

Sits between :mod:`workers.tasks.ingest` (which writes to ``vacancies``)
and :mod:`workers.tasks.publisher` (which reads from ``publication_queue``).
Runs on a 10-min cadence offset from the ingest beat so we naturally
process each ingest batch within ~5-15 minutes of insertion.

The heavy lifting (filter rules, classifier LLM call, rendering) lives
in :func:`app.services.tg_prefilter.prefilter_batch`. This module is
just the sync→async bridge plus structlog wrapping.

Disabled-mode behaviour matches the publisher: when
``telegram_publication_group_id`` is empty we log
``prefilter.disabled`` and return zeroed counters, so the beat schedule
keeps ticking without errors in dev/CI.
"""

from __future__ import annotations

from typing import Any

import structlog
from app.config import settings
from app.services.tg_prefilter import prefilter_batch
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from workers._async_bridge import run_with_session

log = structlog.get_logger(__name__)


async def _run(db: AsyncSession) -> dict[str, Any]:
    """Async entry point — drains the candidate set into the queue."""
    result = await prefilter_batch(
        db,
        target="group",
        # 200 candidates / 10 min cadence handles ~28 800 vacancies/day
        # — well above any realistic ingest rate. Bumping this only
        # makes sense if the LLM classifier is the bottleneck, which
        # is unlikely at 5-token responses.
        limit=200,
    )
    return result.as_dict()


@shared_task(
    name="workers.tasks.prefilter.prefilter_pending_vacancies",
    bind=True,
    # Like the publisher, this task is its own retry mechanism — the
    # next 10-min beat tick will reprocess anything that didn't land
    # in the queue. Stacking Celery's autoretry on top of that gives
    # us duplicated classify-LLM calls for the same rows.
    max_retries=0,
)
def prefilter_pending_vacancies(self: Any) -> dict[str, Any]:
    """Beat-driven entry point — push unpublished vacancies through the gates."""
    if not settings.telegram_publication_group_id:
        log.info("prefilter.disabled")
        return {
            "considered": 0,
            "enqueued": 0,
            "rejected": 0,
            "failed": 0,
            "disabled": True,
        }
    log.info("prefilter.start")
    result = run_with_session(_run)
    log.info("prefilter.done", **result)
    return result
