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
    "proshli",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "workers.tasks.ingest",
        "workers.tasks.digest",
        "workers.tasks.billing",
        "workers.tasks.prefilter",
        "workers.tasks.publisher",
    ],
)

# Eagerly import task modules so they register on the canonical app object.
# ``include=`` lazy-imports them only when the worker boots; for tests +
# importers of ``celery_app`` we want the side-effect now.
import workers.tasks.billing as _billing  # noqa: E402
import workers.tasks.digest as _digest  # noqa: E402
import workers.tasks.ingest as _ingest  # noqa: E402
import workers.tasks.prefilter as _prefilter  # noqa: E402
import workers.tasks.publisher as _publisher  # noqa: E402

# Mark modules referenced so static analysis sees the side-effect imports
# as intentional. The task decorators register against ``celery_app`` at
# import time — that's the whole point.
_REGISTERED_TASK_MODULES = (_billing, _digest, _ingest, _prefilter, _publisher)

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
        # Wave 2: hourly autopayment renewal. Skewed off the :00 mark so we
        # don't pile onto ЮKassa's own minute-zero spike.
        "renew-subscriptions-hourly": {
            "task": "workers.tasks.billing.renew_expiring_subscriptions",
            "schedule": crontab(minute=7),
        },
        # TG prefilter: scan ingest output every 10 min, classify, and
        # push survivors into ``publication_queue``. Offset from the
        # ingest cron (every 10 min on the dot) by 5 minutes so we
        # consistently process the latest batch.
        "prefilter-every-10-min": {
            "task": "workers.tasks.prefilter.prefilter_pending_vacancies",
            "schedule": crontab(minute="5,15,25,35,45,55"),
        },
        # TG publication firehose: drain ``publication_queue`` every 15 min.
        # Skewed off ``*/15`` exact-quarter-hour to avoid colliding with the
        # ingest task at minute 0 — keeps the worker prefetch=1 contention
        # from queueing the publisher behind a long-running ingest.
        "publish-pending-every-15-min": {
            "task": "workers.tasks.publisher.publish_pending_batch",
            "schedule": crontab(minute="3,18,33,48"),
        },
    },
)
