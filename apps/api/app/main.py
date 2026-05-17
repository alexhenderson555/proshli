"""FastAPI application factory.

Sprint 1 wave-5: full router surface is live on the async stack. All routes
from the legacy monolithic main.py have been extracted into
``app/routes/`` and converted to ``AsyncSession``.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import (
    admin,
    ai,
    auth,
    digest,
    health,
    ingest,
    profiles,
    resumes,
    users,
    vacancies,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Otklik.ai API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    return app


app = create_app()
