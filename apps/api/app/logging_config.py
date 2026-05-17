"""structlog setup — JSON in non-dev, pretty console in dev.

Call :func:`configure_logging` once at app startup. Subsequent calls are
idempotent.

Loggers obtained via ``structlog.get_logger(...)`` honour the configured
processor chain, and the request-id middleware binds ``request_id`` into the
contextvars so every record correlates with its HTTP request.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.config import settings

_configured = False


def configure_logging() -> None:
    """Wire stdlib ``logging`` and ``structlog`` together.

    Idempotent: safe to call from tests / multiple ``create_app()`` calls.
    """
    global _configured
    if _configured:
        return

    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.add_logger_name,
    ]

    if settings.app_env == "development":
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(colors=True)
        # ConsoleRenderer prints pretty tracebacks itself when given exc_info;
        # the explicit ``format_exc_info`` processor would short-circuit that
        # and structlog warns about the combination.
        exc_processor: structlog.types.Processor | None = None
    else:
        renderer = structlog.processors.JSONRenderer()
        # JSON output needs the traceback rendered to a string field.
        exc_processor = structlog.processors.format_exc_info

    processors: list[structlog.types.Processor] = [
        *shared_processors,
        structlog.processors.StackInfoRenderer(),
    ]
    if exc_processor is not None:
        processors.append(exc_processor)
    processors.append(renderer)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _configured = True
