"""telegram account linking

Revision ID: 0009_telegram_account_linking
Revises: 0008_vacancy_promotion_fields
Create Date: 2026-03-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_telegram_account_linking"
down_revision: Union[str, Sequence[str], None] = "0008_vacancy_promotion_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "telegram_link_codes" not in tables:
        op.create_table(
            "telegram_link_codes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("code", sa.String(length=32), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_telegram_link_codes_id", "telegram_link_codes", ["id"])
        op.create_index("ix_telegram_link_codes_user_id", "telegram_link_codes", ["user_id"])
        op.create_index("ix_telegram_link_codes_code", "telegram_link_codes", ["code"], unique=True)
        op.create_index("ix_telegram_link_codes_expires_at", "telegram_link_codes", ["expires_at"])
        op.create_index("ix_telegram_link_codes_created_at", "telegram_link_codes", ["created_at"])

    if "telegram_account_links" not in tables:
        op.create_table(
            "telegram_account_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("telegram_user_id", sa.String(length=64), nullable=False),
            sa.Column("telegram_chat_id", sa.String(length=64), nullable=False),
            sa.Column("telegram_username", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_telegram_account_links_id", "telegram_account_links", ["id"])
        op.create_index("ix_telegram_account_links_user_id", "telegram_account_links", ["user_id"], unique=True)
        op.create_index(
            "ix_telegram_account_links_telegram_user_id",
            "telegram_account_links",
            ["telegram_user_id"],
            unique=True,
        )
        op.create_index(
            "ix_telegram_account_links_telegram_chat_id",
            "telegram_account_links",
            ["telegram_chat_id"],
        )
        op.create_index("ix_telegram_account_links_updated_at", "telegram_account_links", ["updated_at"])


def downgrade() -> None:
    pass
