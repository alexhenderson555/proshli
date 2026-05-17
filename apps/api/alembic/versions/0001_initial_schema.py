"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "vacancies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=128), nullable=False),
        sa.Column("employment_type", sa.String(length=64), nullable=False),
        sa.Column("experience_level", sa.String(length=64), nullable=False),
        sa.Column("salary_from", sa.Integer(), nullable=True),
        sa.Column("salary_to", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("applications_count", sa.Integer(), nullable=False),
    )
    for idx in [
        "id",
        "source",
        "external_id",
        "title",
        "company",
        "location",
        "published_at",
        "applications_count",
    ]:
        op.create_index(f"ix_vacancies_{idx}", "vacancies", [idx])

    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("parsed_skills", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_resumes_id", "resumes", ["id"])
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    op.create_table(
        "digest_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("via_telegram", sa.Boolean(), nullable=False),
        sa.Column("via_email", sa.Boolean(), nullable=False),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_digest_preferences_id", "digest_preferences", ["id"])
    op.create_index("ix_digest_preferences_user_id", "digest_preferences", ["user_id"], unique=True)

    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("prompt_chars", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_usage_events_id", "ai_usage_events", ["id"])
    op.create_index("ix_ai_usage_events_user_id", "ai_usage_events", ["user_id"])
    op.create_index("ix_ai_usage_events_created_at", "ai_usage_events", ["created_at"])

    op.create_table(
        "raw_vacancies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_raw_vacancies_id", "raw_vacancies", ["id"])
    op.create_index("ix_raw_vacancies_source", "raw_vacancies", ["source"])
    op.create_index("ix_raw_vacancies_external_id", "raw_vacancies", ["external_id"])
    op.create_index("ix_raw_vacancies_ingested_at", "raw_vacancies", ["ingested_at"])

    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False),
        sa.Column("deduped_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ingest_runs_id", "ingest_runs", ["id"])
    op.create_index("ix_ingest_runs_source", "ingest_runs", ["source"])

    op.create_table(
        "digest_dispatch_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("channels_csv", sa.String(length=120), nullable=False),
        sa.Column("items_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_digest_dispatch_events_id", "digest_dispatch_events", ["id"])
    op.create_index("ix_digest_dispatch_events_user_id", "digest_dispatch_events", ["user_id"])
    op.create_index("ix_digest_dispatch_events_frequency", "digest_dispatch_events", ["frequency"])
    op.create_index("ix_digest_dispatch_events_created_at", "digest_dispatch_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("digest_dispatch_events")
    op.drop_table("ingest_runs")
    op.drop_table("raw_vacancies")
    op.drop_table("ai_usage_events")
    op.drop_table("digest_preferences")
    op.drop_table("resumes")
    op.drop_table("vacancies")
    op.drop_table("users")
