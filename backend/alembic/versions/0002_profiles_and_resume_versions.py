"""profiles and resume versions

Revision ID: 0002_profiles_and_resume_versions
Revises: 0001_initial_schema
Create Date: 2026-03-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_profiles_and_resume_versions"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "seeker_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("target_role", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("location", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("about", sa.Text(), nullable=False, server_default=""),
        sa.Column("skills_csv", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_seeker_profiles_id", "seeker_profiles", ["id"])
    op.create_index("ix_seeker_profiles_user_id", "seeker_profiles", ["user_id"], unique=True)

    op.create_table(
        "employer_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("website", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_employer_profiles_id", "employer_profiles", ["id"])
    op.create_index("ix_employer_profiles_user_id", "employer_profiles", ["user_id"], unique=True)

    op.create_table(
        "resume_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("target_role", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("content_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_resume_versions_id", "resume_versions", ["id"])
    op.create_index("ix_resume_versions_user_id", "resume_versions", ["user_id"])


def downgrade() -> None:
    op.drop_table("resume_versions")
    op.drop_table("employer_profiles")
    op.drop_table("seeker_profiles")
