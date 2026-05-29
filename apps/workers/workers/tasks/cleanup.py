"""Daily housekeeping — prune vacancies that have aged out of relevance.

The HH wide sweep adds thousands of rows every 6 h. Without a cleanup
pass the table would grow to ~10 M rows in a few months — slow queries,
heavier embeddings index, bigger backups. We don't need that history for
product surface: a vacancy that's been on HH for 90 days is either
filled, dead, or the kind of evergreen role we'll re-fetch on the next
sweep anyway.

Retention policy
================

* ``published_at IS NOT NULL`` — we only prune rows where the source
  supplied a real publication date. Manually-curated rows and rows from
  sources that don't surface a timestamp are kept indefinitely.
* ``published_at < now() - 90 days`` — three-month window matches HH's
  own freshness ranking horizon (older postings drop out of their
  default sort regardless of relevance).
* No cascade to ``vacancy_applications`` is configured because the FK
  there is ``ON DELETE CASCADE`` already — a seeker's kanban entry for a
  pruned vacancy is intentional collateral.
* ``match_reasonings`` likewise cascades on the vacancy FK.
* ``raw_vacancies`` is kept (it's the audit log of what we ingested);
  separate retention for that table can be added later if storage
  pressure demands it.

Idempotency
===========

The task is a single ``DELETE`` statement under one transaction; if the
worker is killed mid-run the next tick simply finishes the rest. We
return the row count so Grafana can chart prune volume — if it spikes
unexpectedly that's the first signal something changed upstream.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import structlog
from app.models import Vacancy
from celery import shared_task
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from workers._async_bridge import run_with_session

log = structlog.get_logger(__name__)

# Retention horizon. Pulled to a module constant so tests can monkey-patch
# it down to seconds for a deterministic prune assertion.
RETENTION_DAYS: int = 90


async def _prune_stale(db: AsyncSession) -> int:
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    stmt = delete(Vacancy).where(
        Vacancy.published_at.is_not(None),
        Vacancy.published_at < cutoff,
    )
    result = await db.execute(stmt)
    await db.commit()
    # ``rowcount`` is -1 on dialects that don't report it; coerce to 0
    # so the metric is always a non-negative integer.
    return max(int(result.rowcount or 0), 0)


@shared_task(
    name="workers.tasks.cleanup.cleanup_stale_vacancies",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
)
def cleanup_stale_vacancies(self: Any) -> dict[str, Any]:
    """Delete vacancies older than ``RETENTION_DAYS`` (default 90)."""
    log.info("cleanup.start", retention_days=RETENTION_DAYS)
    deleted = run_with_session(_prune_stale)
    log.info("cleanup.done", deleted=deleted)
    return {"deleted": deleted, "retention_days": RETENTION_DAYS}
