"""Match-score 2.0: match_reasonings cache table.

Stores Claude reranker output keyed on (resume, vacancy). See
``app.models.MatchReasoning`` for the design rationale — TTL,
invalidation triggers, and why cosine is kept alongside the rerank
score.

Revision ID: 0019_match_reasoning
Revises: 0018_vacancy_applications
Create Date: 2026-05-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_match_reasoning"
down_revision: str | Sequence[str] | None = "0018_vacancy_applications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "match_reasonings" in inspector.get_table_names():
        return

    op.create_table(
        "match_reasonings",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column(
            "resume_id",
            sa.Integer,
            sa.ForeignKey("resumes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "vacancy_id",
            sa.Integer,
            sa.ForeignKey("vacancies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("rerank_score", sa.Float, nullable=False, index=True),
        sa.Column("cosine_score", sa.Float, nullable=False),
        sa.Column("reasoning_ru", sa.Text, nullable=False),
        sa.Column("reasoning_en", sa.Text, nullable=True),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.UniqueConstraint(
            "resume_id",
            "vacancy_id",
            name="uq_match_reasonings_resume_vacancy",
        ),
    )


def downgrade() -> None:
    op.drop_table("match_reasonings")
