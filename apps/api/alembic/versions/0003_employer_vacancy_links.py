"""employer vacancy links

Revision ID: 0003_employer_vacancy_links
Revises: 0002_profiles_and_resume_versions
Create Date: 2026-03-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_employer_vacancy_links"
down_revision: Union[str, Sequence[str], None] = "0002_profiles_and_resume_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "employer_vacancies" not in inspector.get_table_names():
        op.create_table(
            "employer_vacancies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("vacancy_id", sa.Integer(), sa.ForeignKey("vacancies.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_employer_vacancies_id", "employer_vacancies", ["id"])
        op.create_index("ix_employer_vacancies_user_id", "employer_vacancies", ["user_id"])
        op.create_index("ix_employer_vacancies_vacancy_id", "employer_vacancies", ["vacancy_id"])


def downgrade() -> None:
    op.drop_table("employer_vacancies")
