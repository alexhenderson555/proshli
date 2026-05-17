"""Alembic env for Otklik.ai — async-mode.

Pattern adapted from ``reference-vault/backend-python/fastapi-clean-example``:
online mode uses ``async_engine_from_config`` + ``asyncio.run`` so the engine
speaks ``asyncpg`` like the running app. Offline mode renders SQL using the
plain URL.

The database URL comes from :mod:`app.config.settings`. We override
``sqlalchemy.url`` in the in-memory config rather than the .ini file so secrets
never live in source control.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context

# Importing app.models registers every ORM class against the shared Base.
from app import models  # noqa: F401
from app.config import settings
from app.db import Base
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

# Inject the runtime DSN (asyncpg flavour) before fileConfig runs.
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without opening a DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    # Pre-create alembic_version with a wider column than the default
    # VARCHAR(32) — our revision ids include descriptive suffixes such as
    # "0002_profiles_and_resume_versions" that would otherwise truncate.
    connection.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS alembic_version ("
        "version_num VARCHAR(255) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
    )
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    """Open an async engine, run migrations through a sync-adapter connection."""
    section = config.get_section(config.config_ini_section, {}) or {}
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
