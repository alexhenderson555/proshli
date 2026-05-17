"""Pytest fixtures for the async API test suite.

The session-scoped event loop is configured globally in ``pyproject.toml``
(``asyncio_default_fixture_loop_scope`` / ``asyncio_default_test_loop_scope``)
so the module-level async engine in :mod:`app.db` can keep its connection pool
across tests.  We dispose the engine once the session ends to avoid
``Event loop is closed`` warnings on Windows.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio

from app.db import engine


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _dispose_engine() -> AsyncIterator[None]:
    yield
    await engine.dispose()
