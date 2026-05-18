"""Pytest fixtures for the async API test suite.

The session-scoped event loop is configured globally in ``pyproject.toml``
(``asyncio_default_fixture_loop_scope`` / ``asyncio_default_test_loop_scope``)
so the module-level async engine in :mod:`app.db` can keep its connection pool
across tests.  We dispose the engine once the session ends to avoid
``Event loop is closed`` warnings on Windows.

Alembic migrations land in Task 5; until then we materialise the schema via
``Base.metadata.create_all`` against the live test DB at session startup.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# Importing ``app.models`` ensures every mapper is registered on ``Base.metadata``
# before ``create_all`` runs.
from app import models  # noqa: F401
from app.db import Base, engine
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _bootstrap_schema() -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a bare AsyncSession for unit tests that touch models directly.

    Each test gets its own session; changes are rolled back after the test
    completes so the shared test DB stays clean between runs.
    """
    from app.db import async_session_factory

    async with async_session_factory() as session:
        yield session
