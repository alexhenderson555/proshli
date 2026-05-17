"""enable pgvector extension

Revision ID: 0010_pgvector_extension
Revises: 0009_telegram_account_linking
Create Date: 2026-05-17

We don't have ``Vector`` columns yet, but the extension is needed for the
semantic-match pipeline in Sprint 2. Creating it idempotently here means we
don't have to do it from application code at startup, and CI/test environments
get the extension installed automatically when ``alembic upgrade head`` runs.

The container image (``pgvector/pgvector:pg16``) already ships the extension's
shared library; this just registers it in the target database.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010_pgvector_extension"
down_revision: str | Sequence[str] | None = "0009_telegram_account_linking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Intentionally a no-op: dropping the extension would break any rows that
    # later acquire ``vector`` columns. Operators can drop it manually if they
    # really want to.
    pass
