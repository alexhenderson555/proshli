"""vacancy status and archive

Revision ID: 0004_vacancy_status_and_archive
Revises: 0003_employer_vacancy_links
Create Date: 2026-03-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_vacancy_status_and_archive"
down_revision: Union[str, Sequence[str], None] = "0003_employer_vacancy_links"
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


def downgrade() -> None:
    op.drop_index("ix_vacancies_is_active", table_name="vacancies")
    op.drop_column("vacancies", "archived_at")
    op.drop_column("vacancies", "is_active")
