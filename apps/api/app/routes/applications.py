"""Seeker kanban — saved + applied + interview + offer + rejected.

Single resource: ``vacancy_applications``. The "Saved" lane and the four
post-application lanes are different rows of the same table, separated
by ``status``. The endpoints are deliberately small:

* ``POST /applications`` — start tracking a vacancy (status defaults to saved)
* ``GET  /applications`` — list the caller's pipeline, optional status filter
* ``PATCH /applications/{id}`` — move lanes or edit notes
* ``DELETE /applications/{id}`` — remove (hard delete; pipeline is short-lived state)
* ``GET  /applications/counts`` — one number per lane for the dashboard overview

All routes are seeker-only — employers don't have a pipeline. Anonymous
callers get 401 from ``get_current_user``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import desc, func, select

from app.auth import get_current_user
from app.deps import DbSession
from app.models import User, Vacancy, VacancyApplication
from app.schemas import (
    ApplicationCountsOut,
    ApplicationCreateRequest,
    ApplicationOut,
    ApplicationStatus,
    ApplicationUpdateRequest,
    VacancyOut,
)
from app.time_utils import now_utc

router = APIRouter(prefix="/applications", tags=["applications"])

_LANES: tuple[ApplicationStatus, ...] = (
    "saved",
    "applied",
    "interview",
    "offer",
    "rejected",
)


def _require_seeker(user: User) -> None:
    if user.role != "seeker":
        raise HTTPException(status_code=403, detail="Only seekers track applications")


async def _hydrate(db: DbSession, row: VacancyApplication) -> ApplicationOut:
    """Attach the nested ``VacancyOut`` so the kanban can render cards."""
    vacancy = await db.get(Vacancy, row.vacancy_id)
    if vacancy is None:
        # The CASCADE on vacancy delete should prevent this, but if it ever
        # happens (admin hard-delete via SQL bypass) we surface a 410 rather
        # than crash the kanban — let the FE skip the row.
        raise HTTPException(status_code=410, detail="Vacancy no longer exists")
    return ApplicationOut(
        id=row.id,
        vacancy_id=row.vacancy_id,
        status=row.status,  # type: ignore[arg-type]
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
        vacancy=VacancyOut.model_validate(vacancy),
    )


@router.post(
    "", response_model=ApplicationOut, status_code=http_status.HTTP_201_CREATED
)
async def create_application(
    payload: ApplicationCreateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> ApplicationOut:
    _require_seeker(current_user)

    vacancy = await db.get(Vacancy, payload.vacancy_id)
    if vacancy is None or vacancy.is_deleted:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    # Pre-flight existence check makes POST idempotent without relying on
    # IntegrityError recovery — asyncpg leaves the session in a state that
    # can't be reused after a unique-violation rollback, so we never try.
    existing = await db.scalar(
        select(VacancyApplication).where(
            VacancyApplication.user_id == current_user.id,
            VacancyApplication.vacancy_id == payload.vacancy_id,
        )
    )
    if existing is not None:
        return await _hydrate(db, existing)

    row = VacancyApplication(
        user_id=current_user.id,
        vacancy_id=payload.vacancy_id,
        status=payload.status,
        notes=payload.notes,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return await _hydrate(db, row)


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    db: DbSession,
    status: ApplicationStatus | None = Query(default=None),
    current_user: User = Depends(get_current_user),
) -> list[ApplicationOut]:
    _require_seeker(current_user)
    stmt = (
        select(VacancyApplication)
        .where(VacancyApplication.user_id == current_user.id)
        .order_by(desc(VacancyApplication.updated_at))
    )
    if status is not None:
        stmt = stmt.where(VacancyApplication.status == status)
    rows = list((await db.scalars(stmt)).all())
    return [await _hydrate(db, row) for row in rows]


@router.get("/counts", response_model=ApplicationCountsOut)
async def application_counts(
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> ApplicationCountsOut:
    _require_seeker(current_user)
    stmt = (
        select(VacancyApplication.status, func.count())
        .where(VacancyApplication.user_id == current_user.id)
        .group_by(VacancyApplication.status)
    )
    result = dict((await db.execute(stmt)).all())
    return ApplicationCountsOut(
        saved=int(result.get("saved", 0)),
        applied=int(result.get("applied", 0)),
        interview=int(result.get("interview", 0)),
        offer=int(result.get("offer", 0)),
        rejected=int(result.get("rejected", 0)),
    )


@router.patch("/{application_id}", response_model=ApplicationOut)
async def update_application(
    application_id: int,
    payload: ApplicationUpdateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> ApplicationOut:
    _require_seeker(current_user)

    row = await db.get(VacancyApplication, application_id)
    if row is None or row.user_id != current_user.id:
        # 404 (not 403) for the foreign-id case so we don't leak the
        # existence of other users' rows.
        raise HTTPException(status_code=404, detail="Application not found")

    changed = False
    if payload.status is not None and payload.status in _LANES:
        row.status = payload.status
        changed = True
    if payload.notes is not None:
        row.notes = payload.notes
        changed = True
    if changed:
        row.updated_at = now_utc()
        await db.commit()
        await db.refresh(row)
    return await _hydrate(db, row)


@router.delete("/{application_id}")
async def delete_application(
    application_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    _require_seeker(current_user)
    row = await db.get(VacancyApplication, application_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Application not found")
    await db.delete(row)
    await db.commit()
    return {"status": "deleted"}
