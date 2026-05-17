"""FastAPI application factory — Otklik.ai backend.

Sprint 1 wave 7 wires the production-readiness stack on top of the
fully-async route surface:

* structlog (JSON in non-dev, console in dev) configured at startup
* Sentry init when a DSN is configured outside of test env
* RequestId middleware → ``X-Request-ID`` header + structlog contextvars
* Global exception handler → stable JSON envelope with request id
* Health is split into liveness (``/health``) and readiness (``/health/ready``)
* Rate-limit + Redis client used by ``/auth`` and ``/ai`` routers

The ``custom_generate_unique_id`` callable produces clean operation IDs of
the form ``tag-handler_name`` — critical for downstream codegen (Wave 9
generates the TS SDK from the OpenAPI doc and the operation ids become
exported function names).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.config import settings
from app.exception_handlers import register_exception_handlers
from app.logging_config import configure_logging
from app.middleware.request_id import RequestIdMiddleware
from app.routes import (
    admin,
    ai,
    auth,
    billing,
    digest,
    health,
    ingest,
    profiles,
    resumes,
    users,
    vacancies,
    webhooks,
)
from app.sentry import init_sentry


def custom_generate_unique_id(route: APIRoute) -> str:
    """Produce stable, codegen-friendly operation IDs.

    Pattern from ``reference-vault/fastapi-full-stack-template`` —
    ``{first_tag}-{handler_name}`` gives the generated TS client function
    names like ``vacancies-list_vacancies`` instead of FastAPI's auto-id
    ``list_vacancies_vacancies_get``. We sanitise the tag so router-level
    titles like ``"AI Chat"`` still produce a valid identifier.
    """
    raw_tag = route.tags[0] if route.tags else "default"
    # Tags can be plain strings or Enum members (FastAPI accepts both); coerce
    # to str so ``.lower()``/``.replace()`` are always valid.
    tag = str(raw_tag).lower().replace(" ", "-")
    return f"{tag}-{route.name}"


def create_app() -> FastAPI:
    configure_logging()
    init_sentry()

    app = FastAPI(
        title="Otklik.ai API",
        version="0.1.0",
        description="Russian-language job aggregator — backend API.",
        generate_unique_id_function=custom_generate_unique_id,
    )

    # Middleware order: outermost first. RequestId must precede CORS so even
    # preflight responses get the id; CORS is the user-facing edge layer.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)

    # Order controls OpenAPI tag ordering and route resolution priority.
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(profiles.router)
    app.include_router(resumes.router)
    app.include_router(vacancies.router)
    app.include_router(ingest.router)
    app.include_router(digest.router)
    app.include_router(ai.router)
    app.include_router(admin.router)
    app.include_router(billing.router)
    app.include_router(webhooks.router)

    return app


app = create_app()
