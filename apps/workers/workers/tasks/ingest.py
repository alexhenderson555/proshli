"""Ingest tasks — pull jobs from connectors into the DB."""

from __future__ import annotations

from typing import Any

import structlog
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
