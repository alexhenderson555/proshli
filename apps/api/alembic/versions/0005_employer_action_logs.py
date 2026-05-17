"""employer action logs

Revision ID: 0005_employer_action_logs
Revises: 0004_vacancy_status_and_archive
Create Date: 2026-03-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_employer_action_logs"
down_revision: Union[str, Sequence[str], None] = "0004_vacancy_status_and_archive"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
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
    op.drop_table("employer_action_logs")
