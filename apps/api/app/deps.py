"""FastAPI shared dependencies."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an ``AsyncSession``.

    Commit/rollback semantics are handled per-route (explicit ``await db.commit()``)
    so that route handlers retain control of transaction boundaries.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db)]
