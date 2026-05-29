"""Product-analytics event_log substrate.

General-purpose append-only table for cross-cutting product events:
page_view, signup, login, vacancy_view, vacancy_apply, digest_open,
ai_chat. See ``app.models.EventLog`` for the schema rationale and the
``app.middleware.event_tracking`` ASGI middleware that populates it.

DAU, funnel, and retention queries run against this table directly via
Grafana's Postgres datasource — no pre-aggregation until row count
demands it.

Revision ID: 0020_event_log
Revises: 0019_match_reasoning
Create Date: 2026-05-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_event_log"
down_revision: str | Sequence[str] | None = "0019_match_reasoning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "event_log" in inspector.get_table_names():
        return

    op.create_table(
        "event_log",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("session_id", sa.String(64), nullable=True, index=True),
        sa.Column("event", sa.String(64), nullable=False, index=True),
        sa.Column("target_kind", sa.String(32), nullable=True),
        sa.Column("target_id", sa.String(128), nullable=True),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
    )
    op.create_index(
        "ix_event_log_user_created",
        "event_log",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_event_log_user_created", table_name="event_log")
    op.drop_table("event_log")
