"""employer action table and vacancy filters

Revision ID: 0006_employer_action_and_filters
Revises: 0005_employer_action_logs
Create Date: 2026-03-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_employer_action_and_filters"
down_revision: Union[str, Sequence[str], None] = "0005_employer_action_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {column["name"] for column in inspector.get_columns("vacancies")}
    if "is_active" not in columns:
        op.add_column("vacancies", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "archived_at" not in columns:
        op.add_column("vacancies", sa.Column("archived_at", sa.DateTime(), nullable=True))
    indexes = {index["name"] for index in inspector.get_indexes("vacancies")}
    if "ix_vacancies_is_active" not in indexes:
        op.create_index("ix_vacancies_is_active", "vacancies", ["is_active"])

    if "employer_action_logs" not in inspector.get_table_names():
        op.create_table(
            "employer_action_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("vacancy_id", sa.Integer(), sa.ForeignKey("vacancies.id"), nullable=True),
            sa.Column("action", sa.String(length=64), nullable=False),
            sa.Column("meta_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_employer_action_logs_id", "employer_action_logs", ["id"])
        op.create_index("ix_employer_action_logs_user_id", "employer_action_logs", ["user_id"])
        op.create_index("ix_employer_action_logs_vacancy_id", "employer_action_logs", ["vacancy_id"])
        op.create_index("ix_employer_action_logs_action", "employer_action_logs", ["action"])
        op.create_index("ix_employer_action_logs_created_at", "employer_action_logs", ["created_at"])


def downgrade() -> None:
    pass
