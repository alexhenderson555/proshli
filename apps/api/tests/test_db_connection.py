"""Smoke tests for async DB connectivity and pgvector availability.

These tests require a running Postgres+pgvector instance at the DSN configured
in DATABASE_URL (see apps/api/.env / .env.example).
"""

import pytest
from sqlalchemy import text

from app.db import async_session_factory


@pytest.mark.asyncio
async def test_async_session_can_query() -> None:
    async with async_session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_pgvector_extension_available() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        )
        assert result.scalar() == 1
