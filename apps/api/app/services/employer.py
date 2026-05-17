"""Employer-side helper services.

Shared by the vacancies + profiles routes for ownership enforcement and
action logging.  Logging always commits immediately so a route that
subsequently raises still leaves an audit trail.
"""

from __future__ import annotations

import json
from typing import Any

from app.models import EmployerActionLog, EmployerVacancy
from app.time_utils import now_utc
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def log_employer_action(
    db: AsyncSession,
    user_id: int,
    action: str,
    vacancy_id: int | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    db.add(
        EmployerActionLog(
            user_id=user_id,
            vacancy_id=vacancy_id,
            action=action,
            meta_json=json.dumps(meta or {}, ensure_ascii=False),
            created_at=now_utc(),
        )
    )
    await db.commit()


async def require_employer_ownership(
    db: AsyncSession, user_id: int, vacancy_id: int
) -> EmployerVacancy:
    ownership = await db.scalar(
        select(EmployerVacancy)
        .where(EmployerVacancy.user_id == user_id)
        .where(EmployerVacancy.vacancy_id == vacancy_id)
    )
    if not ownership:
        raise HTTPException(
            status_code=404, detail="Vacancy not found in your ownership scope"
        )
    return ownership
