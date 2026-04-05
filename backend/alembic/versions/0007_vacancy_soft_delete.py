"""vacancy soft delete columns

Revision ID: 0007_vacancy_soft_delete
Revises: 0006_employer_action_and_filters
Create Date: 2026-03-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_vacancy_soft_delete"
down_revision: Union[str, Sequence[str], None] = "0006_employer_action_and_filters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("vacancies")}

    if "is_deleted" not in columns:
        op.add_column("vacancies", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "deleted_at" not in columns:
        op.add_column("vacancies", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("vacancies")}
    if "ix_vacancies_is_deleted" not in indexes:
        op.create_index("ix_vacancies_is_deleted", "vacancies", ["is_deleted"])


def downgrade() -> None:
    pass
