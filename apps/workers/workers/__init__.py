"""Proshli Celery workers package.

Two long-running processes run alongside the FastAPI app:

* a Celery worker that consumes ingest + digest tasks
* a Celery beat scheduler that enqueues those tasks on a schedule

Tasks reuse the API's services (``app.services.ingestion`` /
``app.services.dispatcher``) — workers are thin shims that own the
sync/async bridge plus retry semantics.

We import ``app.*`` symbolically. The api project is marked
``package = false`` so it isn't pip-installable; we extend ``sys.path``
once at startup so ``from app.config import settings`` works whether the
worker is launched from this directory (local dev) or from the repo root
(docker compose).
"""

from __future__ import annotations

import sys
from pathlib import Path

_API_ROOT = (Path(__file__).resolve().parents[2] / "api").resolve()
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))
