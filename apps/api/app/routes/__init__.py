"""HTTP route modules.

Each domain lives in its own router file so that ``app.main`` becomes a thin
composition layer.  Order of inclusion in ``main.py`` controls OpenAPI tag
ordering.
"""

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

__all__ = [
    "admin",
    "ai",
    "auth",
    "digest",
    "health",
    "ingest",
    "profiles",
    "resumes",
    "users",
    "vacancies",
]
