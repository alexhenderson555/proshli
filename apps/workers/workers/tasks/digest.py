"""Digest dispatch tasks."""

from __future__ import annotations

from typing import Any

import structlog
from app.services.dispatcher import dispatch_all
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from workers._async_bridge import run_with_session

log = structlog.get_logger(__name__)


async def _dispatch(db: AsyncSession, frequency: str) -> dict[str, Any]:
    events = await dispatch_all(db, frequency)
    sent = sum(1 for e in events if e.status == "sent")
    skipped = sum(1 for e in events if e.status == "skipped")
    failed = sum(1 for e in events if e.status == "failed")
    return {
        "frequency": frequency,
        "considered": len(events),
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
    }


@shared_task(
    name="workers.tasks.digest.send_digests",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
)
def send_digests(self: Any, frequency: str = "daily") -> dict[str, Any]:
    """Periodic task fired by Celery beat — dispatches the chosen-frequency digest."""
    if frequency not in {"daily", "weekly"}:
        raise ValueError(f"Unknown digest frequency: {frequency!r}")
    log.info("digest.start", frequency=frequency)
    result = run_with_session(lambda db: _dispatch(db, frequency))
    log.info("digest.done", **result)
    return result
