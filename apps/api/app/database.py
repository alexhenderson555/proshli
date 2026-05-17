"""Legacy sync-DB compatibility shim.

Re-exports the async ``Base`` from :mod:`app.db` so that ORM model imports keep
working during the sync→async migration.  Sync ``engine`` / ``SessionLocal`` /
``get_db`` from the pre-uv era are intentionally removed; the few remaining
sync callers (scripts/, the legacy monolithic ``main.py``) are being rewritten
in this same task.

Once the migration completes, this module will be deleted in favour of direct
imports from ``app.db`` and ``app.deps``.
"""

from app.db import Base

__all__ = ["Base"]
