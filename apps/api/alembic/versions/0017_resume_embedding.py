"""Add nullable embedding column to resumes.

Lazy backfill: existing resumes get embeddings on first /match request.
No HNSW index -- we never search resumes by similarity, only fetch by user_id.

Revision ID: 0017_resume_embedding
Revises: 0016_channel_approval
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_resume_embedding"
down_revision: str | Sequence[str] | None = "0016_channel_approval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMBEDDING_DIM = 1024


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("resumes")}
    if "embedding" not in columns:
        op.execute(
            f"ALTER TABLE resumes "
            f"ADD COLUMN embedding vector({_EMBEDDING_DIM})"
        )


def downgrade() -> None:
    op.execute("ALTER TABLE resumes DROP COLUMN IF EXISTS embedding")
