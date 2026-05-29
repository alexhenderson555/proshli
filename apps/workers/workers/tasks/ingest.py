"""Ingest tasks — pull jobs from connectors into the DB.

The HH sweep is split into two cadences:

* ``run_hh_light`` — every 10 min, narrow scope (Moscow + Russia-wide),
  capped pages, for top-of-funnel freshness.
* ``run_hh_wide``  — every 6 h, 50-city × 86-query sweep with deep
  pagination, for breadth coverage.

Other connectors (habr_career, company_sites, telegram, rss) run on the
same 10-min cadence as ``run_hh_light`` via ``run_all_connectors``.
"""

from __future__ import annotations

from typing import Any

import structlog
from app.connectors.hh import (
    DEFAULT_HH_AREAS,
    DEFAULT_HH_QUERIES,
    WIDE_HH_AREAS,
    WIDE_HH_QUERIES,
    HhConnector,
)
from app.connectors.registry import build_connectors
from app.services.ingestion import run_ingestion
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from workers._async_bridge import run_with_session

log = structlog.get_logger(__name__)


async def _ingest_one(db: AsyncSession, source_name: str) -> dict[str, Any]:
    connectors = {c.source_name: c for c in build_connectors()}
    connector = connectors.get(source_name)
    if connector is None:
        raise ValueError(f"Unknown connector source: {source_name!r}")
    run = await run_ingestion(db, connector.source_name, connector.fetch())
    return {
        "source": source_name,
        "inserted": run.inserted_count,
        "deduped": run.deduped_count,
    }


@shared_task(
    name="workers.tasks.ingest.ingest_source",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def ingest_source(self: Any, source_name: str) -> dict[str, Any]:
    """Pull jobs from a single connector. Retries on any exception."""
    log.info("ingest.start", source=source_name)
    try:
        result = run_with_session(lambda db: _ingest_one(db, source_name))
    except Exception as exc:
        log.warning("ingest.failed", source=source_name, error=str(exc))
        raise
    log.info("ingest.done", **result)
    return result


async def _ingest_all(db: AsyncSession) -> dict[str, Any]:
    connectors = build_connectors()
    runs: list[dict[str, Any]] = []
    for connector in connectors:
        run = await run_ingestion(db, connector.source_name, connector.fetch())
        runs.append(
            {
                "source": connector.source_name,
                "inserted": run.inserted_count,
                "deduped": run.deduped_count,
            }
        )
    return {
        "runs": runs,
        "total_inserted": sum(r["inserted"] for r in runs),
        "total_deduped": sum(r["deduped"] for r in runs),
    }


@shared_task(
    name="workers.tasks.ingest.run_all_connectors",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def run_all_connectors(self: Any) -> dict[str, Any]:
    """Periodic task fired by Celery beat — ingests every registered source."""
    log.info("ingest.batch.start")
    result = run_with_session(_ingest_all)
    log.info("ingest.batch.done", **result)
    return result


# ---------------------------------------------------------------------------
# HH-specific sweeps
# ---------------------------------------------------------------------------
async def _ingest_hh(db: AsyncSession, connector: HhConnector) -> dict[str, Any]:
    """Single ingestion against a preconfigured HH connector instance.

    Reused by both the light and wide HH tasks — only the connector
    instance varies between them.
    """
    run = await run_ingestion(db, connector.source_name, connector.fetch())
    return {
        "source": connector.source_name,
        "inserted": run.inserted_count,
        "deduped": run.deduped_count,
    }


@shared_task(
    name="workers.tasks.ingest.run_hh_light",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def run_hh_light(self: Any) -> dict[str, Any]:
    """Narrow HH sweep — every 10 min, Moscow + Russia-wide.

    Trades breadth for freshness. ~48 queries × 2 areas × 3 pages × 100
    per_page caps at the global limit (env-driven, typically 2000) so a
    misconfig can't stall the worker beyond the soft timeout.
    """
    log.info("ingest.hh_light.start")
    connector = HhConnector(
        queries=DEFAULT_HH_QUERIES,
        areas=DEFAULT_HH_AREAS,
        max_pages=3,
        global_limit=500,
    )
    result = run_with_session(lambda db: _ingest_hh(db, connector))
    log.info("ingest.hh_light.done", **result)
    return result


@shared_task(
    name="workers.tasks.ingest.run_hh_wide",
    bind=True,
    max_retries=1,
    default_retry_delay=120,
)
def run_hh_wide(self: Any) -> dict[str, Any]:
    """Wide HH sweep — every 6 h, 50 cities × 86 queries with deep pagination.

    Heavy task: wall-clock ~10–15 min at the 0.5s/page throttle, ~5K–10K
    new vacancies per run after dedup. Cadence is dictated by the cleanup
    task (90-day retention) and HH's content turnover — twice a day is
    overkill, every 6 h hits the freshness vs. cost sweet spot.
    """
    log.info("ingest.hh_wide.start")
    connector = HhConnector(
        queries=WIDE_HH_QUERIES,
        areas=WIDE_HH_AREAS,
        max_pages=10,
        global_limit=5000,
    )
    result = run_with_session(lambda db: _ingest_hh(db, connector))
    log.info("ingest.hh_wide.done", **result)
    return result
