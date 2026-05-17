"""One-shot scheduler entrypoint used by the admin route + Celery beat."""

from __future__ import annotations

from dataclasses import dataclass

from app.connectors.registry import build_connectors
from app.services.dispatcher import dispatch_all
from app.services.ingestion import run_ingestion
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class SchedulerRunResult:
    ingestion_runs: int
    ingestion_inserted: int
    ingestion_deduped: int
    digests_sent: int
    digests_skipped: int
    digests_failed: int


async def run_once(db: AsyncSession, digest_frequency: str) -> SchedulerRunResult:
    connectors = build_connectors()
    ingestion_runs = 0
    inserted_total = 0
    deduped_total = 0

    for connector in connectors:
        run = await run_ingestion(db, connector.source_name, connector.fetch())
        ingestion_runs += 1
        inserted_total += run.inserted_count
        deduped_total += run.deduped_count

    events = await dispatch_all(db, digest_frequency)
    sent = len([event for event in events if event.status == "sent"])
    skipped = len([event for event in events if event.status == "skipped"])
    failed = len([event for event in events if event.status == "failed"])

    return SchedulerRunResult(
        ingestion_runs=ingestion_runs,
        ingestion_inserted=inserted_total,
        ingestion_deduped=deduped_total,
        digests_sent=sent,
        digests_skipped=skipped,
        digests_failed=failed,
    )
