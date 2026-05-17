"""Celery application factory.

Single source of truth for the broker/backend URLs (driven by the same
``Settings`` the API uses) and for the periodic beat schedule. Importing
``celery_app`` from this module is enough — the task modules register
themselves via ``include`` below.

Celery 5 is not natively async, so each task wraps the async service call
with ``asyncio.run`` inside a fresh ``AsyncSession``. The pattern keeps the
service layer 100% async while letting us reuse Celery's mature retry +
scheduling story.
"""

from __future__ import annotations

from app.config import settings
from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "otklik",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "workers.tasks.ingest",
        "workers.tasks.digest",
    ],
)

# Eagerly import task modules so they register on the canonical app object.
# ``include=`` lazy-imports them only when the worker boots; for tests +
# importers of ``celery_app`` we want the side-effect now.
import workers.tasks.digest  # noqa: E402
import workers.tasks.ingest  # noqa: E402, F401

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    # Soft timeout < hard timeout: gives the task a chance to clean up.
    task_soft_time_limit=540,  # 9 min
    task_time_limit=600,       # 10 min
    timezone="UTC",
    enable_utc=True,
    # Result expiration: 24h is plenty for retry / debugging windows.
    result_expires=60 * 60 * 24,
    # Beat schedule lives here so it ships with the app (no separate file
    # to forget). Times are UTC.
    beat_schedule={
        "ingest-every-10-min": {
            "task": "workers.tasks.ingest.run_all_connectors",
            "schedule": crontab(minute="*/10"),
        },
        "daily-digest-09-utc": {
            "task": "workers.tasks.digest.send_digests",
            "schedule": crontab(hour=9, minute=0),
            "kwargs": {"frequency": "daily"},
        },
        "weekly-digest-mon-09-utc": {
            "task": "workers.tasks.digest.send_digests",
            "schedule": crontab(hour=9, minute=15, day_of_week="mon"),
            "kwargs": {"frequency": "weekly"},
        },
    },
)
