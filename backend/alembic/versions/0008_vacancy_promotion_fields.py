"""vacancy promotion fields

Revision ID: 0008_vacancy_promotion_fields
Revises: 0007_vacancy_soft_delete
Create Date: 2026-03-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_vacancy_promotion_fields"
down_revision: Union[str, Sequence[str], None] = "0007_vacancy_soft_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("vacancies")}

    if "is_promoted" not in columns:
        op.add_column("vacancies", sa.Column("is_promoted", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "promotion_expires_at" not in columns:
        op.add_column("vacancies", sa.Column("promotion_expires_at", sa.DateTime(), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("vacancies")}
    if "ix_vacancies_is_promoted" not in indexes:
        op.create_index("ix_vacancies_is_promoted", "vacancies", ["is_promoted"])


def downgrade() -> None:
    pass
