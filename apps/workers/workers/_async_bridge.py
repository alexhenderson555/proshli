"""Sync→async bridge for Celery tasks.

Celery 5 is not async-native: task functions run on a sync threadpool. Our
service layer is fully async, so each task wraps the call with this helper.

We deliberately use ``asyncio.run`` (creates a fresh loop per task) rather
than caching a loop on the worker: the engine + session are also fresh per
call, which avoids cross-task asyncpg connection sharing — exactly the
mistake the async docs warn about. A worker process executes one task at a
time anyway (prefetch=1), so the small loop-startup cost is negligible
compared to network I/O.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.db import async_session_factory
from sqlalchemy.ext.asyncio import AsyncSession


async def _with_session[T](work: Callable[[AsyncSession], Awaitable[T]]) -> T:
    async with async_session_factory() as session:
        try:
            result = await work(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


def run_with_session[T](work: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Run ``work`` against a fresh ``AsyncSession`` from sync code."""
    return asyncio.run(_with_session(work))
