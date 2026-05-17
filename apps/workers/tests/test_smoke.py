"""Celery app smoke tests.

We don't boot a worker or a broker — that's an integration concern. These
tests only verify that the app object is well-formed: the schedule names
exist, the tasks are registered, and the include list resolves cleanly.
"""

from __future__ import annotations

from workers.celery_app import celery_app


def test_celery_app_name() -> None:
    assert celery_app.main == "otklik"


def test_expected_tasks_registered() -> None:
    expected = {
        "workers.tasks.ingest.ingest_source",
        "workers.tasks.ingest.run_all_connectors",
        "workers.tasks.digest.send_digests",
        "workers.tasks.billing.renew_expiring_subscriptions",
    }
    registered = set(celery_app.tasks.keys())
    missing = expected - registered
    assert not missing, f"missing tasks: {missing}"


def test_beat_schedule_entries() -> None:
    schedule = celery_app.conf.beat_schedule
    assert "ingest-every-10-min" in schedule
    assert "daily-digest-09-utc" in schedule
    assert "weekly-digest-mon-09-utc" in schedule
    assert "renew-subscriptions-hourly" in schedule
    assert schedule["daily-digest-09-utc"]["kwargs"] == {"frequency": "daily"}


def test_broker_and_backend_configured() -> None:
    assert celery_app.conf.broker_url
    assert celery_app.conf.result_backend
    # Timezone + UTC must be set so beat fires deterministically.
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True
