"""billing tables (plans + subscriptions) + seed three tiers

Revision ID: 0011_billing_tables
Revises: 0010_pgvector_extension
Create Date: 2026-05-17

Wave 2 wires ЮKassa billing for the RU market. We pre-seed three tier rows
(free / pro / employer) so the ``/billing/plans`` endpoint has stable IDs
and slugs from day one. The seed step is idempotent — it inserts only if the
slug is missing — so re-running ``alembic upgrade`` on an environment that
already has the rows is a no-op.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision: str = "0011_billing_tables"
down_revision: str | Sequence[str] | None = "0010_pgvector_extension"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PLAN_SEED = [
    {
        "slug": "free",
        "name_ru": "Бесплатный",
        "price_rub": 0,
        "ai_daily_limit": 5,
        "semantic_search": False,
        "digest_frequency": "weekly",
    },
    {
        "slug": "pro",
        "name_ru": "Pro",
        "price_rub": 490,
        "ai_daily_limit": 50,
        "semantic_search": True,
        "digest_frequency": "daily",
    },
    {
        "slug": "employer",
        "name_ru": "Работодатель",
        "price_rub": 2490,
        "ai_daily_limit": 100,
        "semantic_search": True,
        "digest_frequency": "daily",
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "plans" not in tables:
        op.create_table(
            "plans",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(length=32), nullable=False),
            sa.Column("name_ru", sa.String(length=120), nullable=False),
            sa.Column("price_rub", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "ai_daily_limit",
                sa.Integer(),
                nullable=False,
                server_default="5",
            ),
            sa.Column(
                "semantic_search",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "digest_frequency",
                sa.String(length=20),
                nullable=False,
                server_default="weekly",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_plans_id", "plans", ["id"])
        op.create_index("ix_plans_slug", "plans", ["slug"], unique=True)

    if "subscriptions" not in tables:
        op.create_table(
            "subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column(
                "plan_id",
                sa.Integer(),
                sa.ForeignKey("plans.id"),
                nullable=False,
            ),
            sa.Column(
                "yookassa_payment_method_id",
                sa.String(length=128),
                nullable=True,
            ),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("current_period_end", sa.DateTime(), nullable=True),
            sa.Column("last_payment_id", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_subscriptions_id", "subscriptions", ["id"])
        op.create_index(
            "ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=True
        )
        op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])
        op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
        op.create_index(
            "ix_subscriptions_current_period_end",
            "subscriptions",
            ["current_period_end"],
        )
        op.create_index(
            "ix_subscriptions_updated_at", "subscriptions", ["updated_at"]
        )

    # Idempotent seed: insert only the slugs that don't yet exist.
    plans = sa.table(
        "plans",
        sa.column("slug", sa.String),
        sa.column("name_ru", sa.String),
        sa.column("price_rub", sa.Integer),
        sa.column("ai_daily_limit", sa.Integer),
        sa.column("semantic_search", sa.Boolean),
        sa.column("digest_frequency", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    existing_slugs = set(
        bind.execute(sa.text("SELECT slug FROM plans")).scalars().all()
    )
    # Use a Python timestamp rather than ``sa.func.now()`` — asyncpg's
    # ``executemany`` rejects SQL expressions as bound parameters with
    # ``invalid input for query argument $N`` (only datetime instances
    # are accepted positionally). The semantic is identical: the row's
    # creation moment captured at migration time.
    now = datetime.now(timezone.utc)
    to_insert = [
        {**row, "created_at": now}
        for row in _PLAN_SEED
        if row["slug"] not in existing_slugs
    ]
    if to_insert:
        op.bulk_insert(plans, to_insert)


def downgrade() -> None:
    # Intentionally permissive — drop the user-facing tables.
    op.drop_table("subscriptions")
    op.drop_table("plans")
