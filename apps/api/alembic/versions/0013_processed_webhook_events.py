"""processed_webhook_events: webhook replay-protection

Revision ID: 0013_processed_webhook_events
Revises: 0012_vacancy_embeddings
Create Date: 2026-05-18

Adds a single-purpose append-only table that records each external
webhook event we've already consumed. Used by ``/webhooks/yookassa`` to
short-circuit duplicate deliveries — without this, a replayed
``payment.succeeded`` extended the subscription period by another 30
days *every* time, which is the same as giving the customer a free
month per replay.

The unique index on ``(source, event_id)`` is what makes the guard
atomic: the insert either succeeds (first time we see the event) or
raises ``IntegrityError`` (replay). The webhook handler catches the
latter and returns ``200 OK`` so the provider stops retrying.

Idempotent — re-running ``alembic upgrade head`` on an environment that
already has the table is a no-op.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_processed_webhook_events"
down_revision: str | Sequence[str] | None = "0012_vacancy_embeddings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "processed_webhook_events" not in set(inspector.get_table_names()):
        op.create_table(
            "processed_webhook_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("event_id", sa.String(length=128), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("object_id", sa.String(length=128), nullable=True),
            sa.Column("processed_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_processed_webhook_events_id",
            "processed_webhook_events",
            ["id"],
        )
        op.create_index(
            "ix_processed_webhook_events_source",
            "processed_webhook_events",
            ["source"],
        )
        op.create_index(
            "ix_processed_webhook_events_event_id",
            "processed_webhook_events",
            ["event_id"],
        )
        op.create_index(
            "ix_processed_webhook_events_processed_at",
            "processed_webhook_events",
            ["processed_at"],
        )
        # The atomicity hinge: the (source, event_id) pair is what the
        # webhook handler INSERTs first; a duplicate raises IntegrityError
        # and short-circuits the rest of the handler.
        op.create_index(
            "uq_processed_webhook_events_source_event",
            "processed_webhook_events",
            ["source", "event_id"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index(
        "uq_processed_webhook_events_source_event",
        table_name="processed_webhook_events",
    )
    op.drop_table("processed_webhook_events")
