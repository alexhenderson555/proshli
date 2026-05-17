"""FastAPI application factory.

Sprint 1 wave-2 status: only the **health + auth + users** domains are live.
The remaining 28 routes from the legacy monolithic main are preserved in
``app/main_legacy.py.bak`` and will be ported into ``app/routes/`` in
subsequent waves (vacancies, resumes, profiles, ai, digest, ingest, admin).

Until those waves land, the runtime app intentionally exposes a narrower
surface — that's the price of switching cleanly from sync to async without
running two database sessions in parallel.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import auth as auth_routes
from app.routes import health as health_routes
from app.routes import users as users_routes
from app.routes import vacancies as vacancies_routes


def create_app() -> FastAPI:
    app = FastAPI(title="Otklik.ai API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(users_routes.router)
    app.include_router(vacancies_routes.router)

    return app


app = create_app()
