"""Sentry initialisation — guarded by DSN + environment.

We only init Sentry when a DSN is configured AND we're not in the test suite.
This prevents test runs (and accidental local dev runs without a DSN) from
spinning up the Sentry transport thread, which slows down CI.

Pattern from ``reference-vault/.../fastapi-full-stack-template/backend/app/main.py``.
"""

from __future__ import annotations

import structlog

from app.config import settings

log = structlog.get_logger(__name__)


def init_sentry() -> bool:
    """Initialise Sentry if a DSN is configured. Returns ``True`` if active."""
    if not settings.sentry_dsn:
        log.debug("sentry.disabled", reason="no_dsn")
        return False
    if settings.app_env == "test":
        log.debug("sentry.disabled", reason="test_env")
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        # Celery integration is conditional — the API process doesn't ship
        # the celery library on the import path, so importing it
        # unconditionally would break the FastAPI startup. Workers DO have
        # celery, so the import succeeds there and CeleryIntegration kicks
        # in to capture task failures, retries, and beat misses.
        integrations: list = [FastApiIntegration(), AsyncioIntegration()]
        try:
            from sentry_sdk.integrations.celery import CeleryIntegration

            integrations.append(CeleryIntegration())
        except ImportError:
            pass

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            integrations=integrations,
            send_default_pii=False,
        )
        log.info("sentry.initialized", env=settings.app_env)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("sentry.init_failed", error=str(exc))
        return False
