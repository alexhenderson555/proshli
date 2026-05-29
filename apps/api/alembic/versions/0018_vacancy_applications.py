"""Seeker kanban: vacancy_applications table.

One row per (seeker, vacancy) tracked through the saved/applied/interview/
offer/rejected lanes. See ``app.models.VacancyApplication`` for the design
rationale.

Revision ID: 0018_vacancy_applications
Revises: 0017_resume_embedding
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_vacancy_applications"
down_revision: str | Sequence[str] | None = "0017_resume_embedding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "vacancy_applications" in inspector.get_table_names():
        return

    op.create_table(
        "vacancy_applications",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
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
        sa.Column("status", sa.String(16), nullable=False, server_default="saved", index=True),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.UniqueConstraint(
            "user_id",
            "vacancy_id",
            name="uq_vacancy_applications_user_vacancy",
        ),
    )


def downgrade() -> None:
    op.drop_table("vacancy_applications")
