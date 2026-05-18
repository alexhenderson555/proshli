"""publication_queue + vacancies.topic_id, classified_at

Revision ID: 0014_publication_queue
Revises: 0013_processed_webhook_events
Create Date: 2026-05-18

Phase-1 plumbing for the Telegram-publication subsystem
(`docs/superpowers/specs/2026-05-18-tg-publication-design.md`).

* ``publication_queue`` — FIFO of vacancy → TG-surface posts. Rows
  flow ``pending`` → ``published`` or ``failed`` / ``dismissed``. The
  partial index on ``(status, scheduled_for)`` keeps the publisher's
  per-batch ``SELECT … WHERE status='pending' AND scheduled_for ≤ now``
  scan cheap even once the table has months of history.
* ``vacancies.topic_id`` (1..28) + ``classified_at`` — cached
  classifier output so re-render / re-publish don't re-classify a
  vacancy we already routed.

Idempotent — re-running on an environment that already has the table
or columns is a no-op.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_publication_queue"
down_revision: str | Sequence[str] | None = "0013_processed_webhook_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # ------------------------------------------------------------------
    # vacancies: cached classifier output
    # ------------------------------------------------------------------
    if "vacancies" in existing_tables:
        vacancies_cols = {c["name"] for c in inspector.get_columns("vacancies")}
        if "topic_id" not in vacancies_cols:
            op.add_column(
                "vacancies",
                sa.Column("topic_id", sa.Integer(), nullable=True),
            )
        if "classified_at" not in vacancies_cols:
            op.add_column(
                "vacancies",
                sa.Column("classified_at", sa.DateTime(), nullable=True),
            )

    # ------------------------------------------------------------------
    # publication_queue
    # ------------------------------------------------------------------
    if "publication_queue" not in existing_tables:
        op.create_table(
            "publication_queue",
            sa.Column("id", sa.BigInteger(), primary_key=True),
            sa.Column(
                "vacancy_id",
                sa.Integer(),
                sa.ForeignKey("vacancies.id", ondelete="CASCADE"),
                nullable=False,
            ),
            # 'group' | 'channel' — keeps the publisher's branching cheap
            # without a dedicated enum.
            sa.Column("target", sa.String(length=16), nullable=False),
            # 1..28 for group rows; NULL for channel rows (no topic).
            sa.Column("topic_id", sa.Integer(), nullable=True),
            sa.Column("rendered_text", sa.Text(), nullable=False),
            # pending | published | failed | dismissed
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column(
                "scheduled_for",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("published_message_id", sa.BigInteger(), nullable=True),
            sa.Column(
                "attempts",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("published_at", sa.DateTime(), nullable=True),
        )
        # One row per (vacancy, target) — re-enqueue is a deliberate
        # admin action, not a race-condition outcome.
        op.create_index(
            "uq_publication_queue_vacancy_target",
            "publication_queue",
            ["vacancy_id", "target"],
            unique=True,
        )
        # Hot path for the 15-min publisher batch.
        op.create_index(
            "ix_publication_queue_pending",
            "publication_queue",
            ["status", "scheduled_for"],
            postgresql_where=sa.text("status = 'pending'"),
        )
        # Secondary index for ad-hoc queries (admin UI: "what failed today?").
        op.create_index(
            "ix_publication_queue_status",
            "publication_queue",
            ["status"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "publication_queue" in existing_tables:
        op.drop_index(
            "ix_publication_queue_status", table_name="publication_queue"
        )
        op.drop_index(
            "ix_publication_queue_pending", table_name="publication_queue"
        )
        op.drop_index(
            "uq_publication_queue_vacancy_target",
            table_name="publication_queue",
        )
        op.drop_table("publication_queue")

    if "vacancies" in existing_tables:
        vacancies_cols = {c["name"] for c in inspector.get_columns("vacancies")}
        if "classified_at" in vacancies_cols:
            op.drop_column("vacancies", "classified_at")
        if "topic_id" in vacancies_cols:
            op.drop_column("vacancies", "topic_id")
