"""vacancies.parsed_skills + ai_summary

Revision ID: 0015_vacancy_skills_summary
Revises: 0014_publication_queue
Create Date: 2026-05-18

Two columns that complete the TG-publication post template:

* ``parsed_skills`` — comma-separated extracted skill tokens
  (``"Python,FastAPI,PostgreSQL"``). Cached on the vacancy so the
  prefilter doesn't re-extract on every classification pass. The
  rule-based extractor populates this from a curated keyword dictionary;
  the LLM enrichment step (later wave) augments it for vacancies whose
  description doesn't trigger any dictionary hits.
* ``ai_summary`` — 1-2 sentence Claude-rendered summary used as the
  middle line of the TG post. Cached so we pay the LLM cost exactly
  once per vacancy regardless of how many times it's re-published.

Both are nullable to keep the migration backwards-compatible — old rows
that haven't been re-processed simply render with the fallback path
(title-derived skills, first-sentence summary). Idempotent.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_vacancy_skills_summary"
down_revision: str | Sequence[str] | None = "0014_publication_queue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "vacancies" not in set(inspector.get_table_names()):
        return

    vacancies_cols = {c["name"] for c in inspector.get_columns("vacancies")}
    if "parsed_skills" not in vacancies_cols:
        op.add_column(
            "vacancies",
            sa.Column(
                "parsed_skills",
                sa.Text(),
                nullable=False,
                server_default=sa.text("''"),
            ),
        )
    if "ai_summary" not in vacancies_cols:
        op.add_column(
            "vacancies",
            sa.Column("ai_summary", sa.Text(), nullable=True),
        )
    if "summary_generated_at" not in vacancies_cols:
        op.add_column(
            "vacancies",
            sa.Column("summary_generated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "vacancies" not in set(inspector.get_table_names()):
        return

    vacancies_cols = {c["name"] for c in inspector.get_columns("vacancies")}
    if "summary_generated_at" in vacancies_cols:
        op.drop_column("vacancies", "summary_generated_at")
    if "ai_summary" in vacancies_cols:
        op.drop_column("vacancies", "ai_summary")
    if "parsed_skills" in vacancies_cols:
        op.drop_column("vacancies", "parsed_skills")
