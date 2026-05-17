"""HTTP route modules.

Each domain lives in its own router file so that ``app.main`` becomes a thin
composition layer.  Order of inclusion in ``main.py`` controls OpenAPI tag
ordering.
"""

from app.routes import auth, health, profiles, resumes, users, vacancies

__all__ = ["auth", "health", "profiles", "resumes", "users", "vacancies"]
