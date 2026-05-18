"""channel_candidates + company_prestige (Phase 2 channel approval)

Revision ID: 0016_channel_approval
Revises: 0015_vacancy_skills_summary
Create Date: 2026-05-18

Phase 2 of the TG-publication design — daily admin-approval flow for
the @proshli curated channel. Adds two tables:

* ``company_prestige`` — hand-curated 0.0..1.0 prestige score per
  normalised company name. The scoring service falls back to ``0.0``
  for any company not in the table, so growing the catalog is purely
  additive — no migration needed to seed it.

* ``channel_candidates`` — one row per (vacancy, batch_date). Stores
  the composite score, its component breakdown (JSON), the admin
  decision, and the Telegram message id of the DM that surfaced it.
  The unique constraint on (vacancy_id, batch_date) means re-running
  the daily task is idempotent.

Both tables are created idempotently. Indexes match the access
patterns: candidate lookup by status, sort by score, lookup by
company.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_channel_approval"
down_revision: str | Sequence[str] | None = "0015_vacancy_skills_summary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "company_prestige" not in existing_tables:
        op.create_table(
            "company_prestige",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "company_normalised",
                sa.String(length=255),
                nullable=False,
                unique=True,
            ),
            sa.Column(
                "score",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0.0"),
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_company_prestige_company_normalised",
            "company_prestige",
            ["company_normalised"],
        )

    if "channel_candidates" not in existing_tables:
        op.create_table(
            "channel_candidates",
            sa.Column("id", sa.BigInteger(), primary_key=True),
            sa.Column(
                "vacancy_id",
                sa.Integer(),
                sa.ForeignKey("vacancies.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("batch_date", sa.String(length=10), nullable=False),
            sa.Column(
                "score",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0.0"),
            ),
            sa.Column(
                "score_breakdown",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column("decided_at", sa.DateTime(), nullable=True),
            sa.Column("admin_message_id", sa.BigInteger(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "vacancy_id",
                "batch_date",
                name="uq_channel_candidates_vacancy_batch",
            ),
        )
        op.create_index(
            "ix_channel_candidates_vacancy_id",
            "channel_candidates",
            ["vacancy_id"],
        )
        op.create_index(
            "ix_channel_candidates_batch_date",
            "channel_candidates",
            ["batch_date"],
        )
        op.create_index(
            "ix_channel_candidates_status",
            "channel_candidates",
            ["status"],
        )
        op.create_index(
            "ix_channel_candidates_score",
            "channel_candidates",
            ["score"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "channel_candidates" in existing_tables:
        op.drop_index("ix_channel_candidates_score", table_name="channel_candidates")
        op.drop_index("ix_channel_candidates_status", table_name="channel_candidates")
        op.drop_index("ix_channel_candidates_batch_date", table_name="channel_candidates")
        op.drop_index("ix_channel_candidates_vacancy_id", table_name="channel_candidates")
        op.drop_table("channel_candidates")
    if "company_prestige" in existing_tables:
        op.drop_index(
            "ix_company_prestige_company_normalised",
            table_name="company_prestige",
        )
        op.drop_table("company_prestige")
