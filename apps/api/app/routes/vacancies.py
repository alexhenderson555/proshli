"""Vacancy CRUD + employer ownership endpoints (async).

Routes are split between:

* Public read (``GET /vacancies``) — merges locally-indexed records with the
  live hh.ru feed, gracefully degrades on upstream failure.
* Employer-scoped read/write — every mutation requires that the caller owns
  the vacancy via the ``employer_vacancies`` join table, and emits an entry
  to ``employer_action_logs`` for the audit trail.

Note: order of route declaration matters in FastAPI — the ``/vacancies/my*``
group must precede ``/vacancies/{vacancy_id}`` so the path matcher resolves
the static prefixes first.  Same for ``/vacancies/my/actions/export``.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import asc, desc, func, select, update

from app.auth import get_current_user
from app.deps import DbSession
from app.models import (
    EmployerActionLog,
    EmployerVacancy,
    User,
    Vacancy,
)
from app.schemas import (
    EmployerActionLogOut,
    EmployerVacancyAnalyticsOut,
    EmployerVacancyPageOut,
    VacancyCreateRequest,
    VacancyOut,
    VacancyPromoteRequest,
    VacancyUpdateRequest,
)
from app.services.employer import log_employer_action, require_employer_ownership
from app.services.hh_live import fetch_live_hh_vacancies
from app.time_utils import now_utc

router = APIRouter(prefix="/vacancies", tags=["vacancies"])


_SORT_FIELDS = {
    "published_at": Vacancy.published_at,
    "applications_count": Vacancy.applications_count,
    "title": Vacancy.title,
}


async def _expire_promotions(db: DbSession) -> None:
    """Clear stale ``is_promoted`` flags whose ``promotion_expires_at`` has passed."""
    await db.execute(
        update(Vacancy)
        .where(Vacancy.is_promoted.is_(True))
        .where(Vacancy.promotion_expires_at.is_not(None))
        .where(Vacancy.promotion_expires_at < now_utc())
        .values(is_promoted=False)
    )
    await db.commit()


@router.post("", response_model=VacancyOut, status_code=status.HTTP_201_CREATED)
async def create_vacancy(
    payload: VacancyCreateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> Vacancy:
    if current_user.role != "employer":
        raise HTTPException(status_code=403, detail="Only employers can create vacancies")

    vacancy = Vacancy(**payload.model_dump(), published_at=now_utc())
    db.add(vacancy)
    await db.commit()
    await db.refresh(vacancy)

    db.add(
        EmployerVacancy(
            user_id=current_user.id,
            vacancy_id=vacancy.id,
            created_at=now_utc(),
        )
    )
    await db.commit()
    await log_employer_action(
        db=db,
        user_id=current_user.id,
        vacancy_id=vacancy.id,
        action="vacancy_created",
        meta={"title": vacancy.title},
    )
    return vacancy


@router.get("", response_model=list[VacancyOut])
async def list_vacancies(
    db: DbSession,
    source: str | None = Query(default=None),
    location: str | None = Query(default=None),
    stack: str | None = Query(default=None),
    level: str | None = Query(default=None),
    min_salary: int | None = Query(default=None),
    max_age_days: int | None = Query(default=None),
    max_applications: int | None = Query(default=None),
    work_mode: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    include_live_hh: bool = Query(default=True),
) -> list[VacancyOut]:
    await _expire_promotions(db)

    stmt = select(Vacancy).where(Vacancy.is_deleted.is_(False))
    if source and source != "hh_live":
        stmt = stmt.where(Vacancy.source == source)
    if not include_archived:
        stmt = stmt.where(Vacancy.is_active.is_(True))
    if location:
        stmt = stmt.where(Vacancy.location.ilike(f"%{location}%"))
    if level:
        stmt = stmt.where(Vacancy.experience_level == level)
    if min_salary is not None:
        stmt = stmt.where(Vacancy.salary_to.is_not(None)).where(
            Vacancy.salary_to >= min_salary
        )
    if max_applications is not None:
        stmt = stmt.where(Vacancy.applications_count <= max_applications)
    if stack:
        stmt = stmt.where(Vacancy.description.ilike(f"%{stack}%"))
    if work_mode == "remote":
        stmt = stmt.where(
            Vacancy.location.ilike("%remote%")
            | Vacancy.description.ilike("%remote%")
            | Vacancy.description.ilike("%удален%")
        )
    elif work_mode == "hybrid":
        stmt = stmt.where(
            Vacancy.description.ilike("%hybrid%")
            | Vacancy.description.ilike("%гибрид%")
        )
    elif work_mode == "office":
        stmt = stmt.where(
            Vacancy.description.ilike("%office%")
            | Vacancy.description.ilike("%офис%")
        )
    elif work_mode is not None:
        raise HTTPException(status_code=400, detail="work_mode must be remote|hybrid|office")
    if max_age_days is not None:
        stmt = stmt.where(Vacancy.published_at >= now_utc() - timedelta(days=max_age_days))

    stmt = stmt.order_by(desc(Vacancy.is_promoted), desc(Vacancy.published_at))

    db_rows = list((await db.scalars(stmt)).all())
    db_items: list[VacancyOut] = [VacancyOut.model_validate(item) for item in db_rows]

    if source == "hh_live":
        db_items = []
    elif source and source != "hh_live":
        return db_items
    if not include_live_hh:
        return db_items

    try:
        live_items = await fetch_live_hh_vacancies(
            location=location,
            stack=stack,
            level=level,
            min_salary=min_salary,
            work_mode=work_mode,
            max_age_days=max_age_days,
        )
    except Exception:
        live_items = []

    combined: list[VacancyOut] = [*db_items, *live_items]
    combined.sort(key=lambda item: (item.is_promoted, item.published_at), reverse=True)
    return combined


@router.get("/my", response_model=list[VacancyOut])
async def list_my_vacancies(
    db: DbSession,
    current_user: User = Depends(get_current_user),
    status_filter: str = Query(default="all", alias="status"),
    sort_by: str = Query(default="published_at"),
    order: str = Query(default="desc"),
) -> list[Vacancy]:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can view owned vacancies"
        )

    await _expire_promotions(db)

    stmt = (
        select(Vacancy)
        .join(EmployerVacancy, EmployerVacancy.vacancy_id == Vacancy.id)
        .where(EmployerVacancy.user_id == current_user.id)
        .where(Vacancy.is_deleted.is_(False))
    )
    if status_filter == "active":
        stmt = stmt.where(Vacancy.is_active.is_(True))
    elif status_filter == "archived":
        stmt = stmt.where(Vacancy.is_active.is_(False))
    elif status_filter != "all":
        raise HTTPException(status_code=400, detail="status must be all|active|archived")

    column = _SORT_FIELDS.get(sort_by)
    if column is None:
        raise HTTPException(
            status_code=400,
            detail="sort_by must be published_at|applications_count|title",
        )
    if order == "asc":
        stmt = stmt.order_by(asc(column))
    elif order == "desc":
        stmt = stmt.order_by(desc(column))
    else:
        raise HTTPException(status_code=400, detail="order must be asc|desc")

    return list((await db.scalars(stmt)).all())


@router.get("/my/page", response_model=EmployerVacancyPageOut)
async def list_my_vacancies_page(
    db: DbSession,
    current_user: User = Depends(get_current_user),
    status_filter: str = Query(default="all", alias="status"),
    sort_by: str = Query(default="published_at"),
    order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> EmployerVacancyPageOut:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can view owned vacancies"
        )

    base_stmt = (
        select(Vacancy)
        .join(EmployerVacancy, EmployerVacancy.vacancy_id == Vacancy.id)
        .where(EmployerVacancy.user_id == current_user.id)
        .where(Vacancy.is_deleted.is_(False))
    )
    if status_filter == "active":
        base_stmt = base_stmt.where(Vacancy.is_active.is_(True))
    elif status_filter == "archived":
        base_stmt = base_stmt.where(Vacancy.is_active.is_(False))
    elif status_filter != "all":
        raise HTTPException(status_code=400, detail="status must be all|active|archived")

    column = _SORT_FIELDS.get(sort_by)
    if column is None:
        raise HTTPException(
            status_code=400,
            detail="sort_by must be published_at|applications_count|title",
        )
    if order not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="order must be asc|desc")

    total = await db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    stmt = base_stmt.order_by(asc(column) if order == "asc" else desc(column))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = list((await db.scalars(stmt)).all())
    return EmployerVacancyPageOut(
        items=[VacancyOut.model_validate(item) for item in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/my/analytics", response_model=EmployerVacancyAnalyticsOut)
async def my_vacancy_analytics(
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> EmployerVacancyAnalyticsOut:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can view vacancy analytics"
        )

    rows = (
        await db.scalars(
            select(Vacancy)
            .join(EmployerVacancy, EmployerVacancy.vacancy_id == Vacancy.id)
            .where(EmployerVacancy.user_id == current_user.id)
            .where(Vacancy.is_deleted.is_(False))
        )
    ).all()
    total = len(rows)
    active = len([item for item in rows if item.is_active])
    return EmployerVacancyAnalyticsOut(
        total=total, active=active, archived=total - active
    )


@router.get("/my/actions", response_model=list[EmployerActionLogOut])
async def my_vacancy_actions(
    db: DbSession,
    current_user: User = Depends(get_current_user),
    vacancy_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[EmployerActionLogOut]:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can view action logs"
        )

    stmt = select(EmployerActionLog).where(EmployerActionLog.user_id == current_user.id)
    if vacancy_id is not None:
        stmt = stmt.where(EmployerActionLog.vacancy_id == vacancy_id)
    if action:
        stmt = stmt.where(EmployerActionLog.action == action)
    if created_from is not None:
        stmt = stmt.where(EmployerActionLog.created_at >= created_from.replace(tzinfo=None))
    if created_to is not None:
        stmt = stmt.where(EmployerActionLog.created_at <= created_to.replace(tzinfo=None))
    stmt = stmt.order_by(desc(EmployerActionLog.created_at)).limit(limit)

    rows = (await db.scalars(stmt)).all()
    return [
        EmployerActionLogOut(
            id=item.id,
            vacancy_id=item.vacancy_id,
            action=item.action,
            meta=json.loads(item.meta_json or "{}"),
            created_at=item.created_at,
        )
        for item in rows
    ]


@router.get("/my/actions/export")
async def export_my_vacancy_actions_csv(
    db: DbSession,
    current_user: User = Depends(get_current_user),
    action: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> Response:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can export action logs"
        )

    stmt = select(EmployerActionLog).where(EmployerActionLog.user_id == current_user.id)
    if action:
        stmt = stmt.where(EmployerActionLog.action == action)
    rows = (
        await db.scalars(stmt.order_by(desc(EmployerActionLog.created_at)).limit(limit))
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "vacancy_id", "action", "created_at", "meta_json"])
    for item in rows:
        writer.writerow(
            [item.id, item.vacancy_id, item.action, item.created_at.isoformat(), item.meta_json]
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="employer-actions.csv"'},
    )


@router.put("/{vacancy_id}", response_model=VacancyOut)
async def update_my_vacancy(
    vacancy_id: int,
    payload: VacancyUpdateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> Vacancy:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can update owned vacancies"
        )
    await require_employer_ownership(db, current_user.id, vacancy_id)

    vacancy = await db.get(Vacancy, vacancy_id)
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    updated = payload.model_dump(exclude_unset=True)
    for key, value in updated.items():
        setattr(vacancy, key, value)

    await db.commit()
    await db.refresh(vacancy)
    await log_employer_action(
        db=db,
        user_id=current_user.id,
        vacancy_id=vacancy.id,
        action="vacancy_updated",
        meta={"updated_fields": list(updated.keys())},
    )
    return vacancy


@router.delete("/{vacancy_id}")
async def delete_my_vacancy(
    vacancy_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can delete owned vacancies"
        )
    await require_employer_ownership(db, current_user.id, vacancy_id)

    vacancy = await db.get(Vacancy, vacancy_id)
    if vacancy:
        vacancy.is_deleted = True
        vacancy.is_active = False
        vacancy.deleted_at = now_utc()
    await db.commit()
    await log_employer_action(
        db=db,
        user_id=current_user.id,
        vacancy_id=vacancy_id,
        action="vacancy_soft_deleted",
        meta={},
    )
    return {"status": "soft_deleted"}


@router.post("/{vacancy_id}/archive")
async def archive_my_vacancy(
    vacancy_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can archive owned vacancies"
        )
    await require_employer_ownership(db, current_user.id, vacancy_id)

    vacancy = await db.get(Vacancy, vacancy_id)
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    vacancy.is_active = False
    vacancy.archived_at = now_utc()
    await db.commit()
    await log_employer_action(
        db=db,
        user_id=current_user.id,
        vacancy_id=vacancy.id,
        action="vacancy_archived",
        meta={},
    )
    return {"status": "archived"}


@router.post("/{vacancy_id}/publish")
async def publish_my_vacancy(
    vacancy_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can publish owned vacancies"
        )
    await require_employer_ownership(db, current_user.id, vacancy_id)

    vacancy = await db.get(Vacancy, vacancy_id)
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    vacancy.is_active = True
    vacancy.archived_at = None
    await db.commit()
    await log_employer_action(
        db=db,
        user_id=current_user.id,
        vacancy_id=vacancy.id,
        action="vacancy_published",
        meta={},
    )
    return {"status": "published"}


@router.post("/{vacancy_id}/promote")
async def promote_my_vacancy(
    vacancy_id: int,
    payload: VacancyPromoteRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can promote vacancies"
        )
    await require_employer_ownership(db, current_user.id, vacancy_id)

    vacancy = await db.get(Vacancy, vacancy_id)
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    vacancy.is_promoted = True
    vacancy.promotion_expires_at = now_utc() + timedelta(days=payload.days)
    await db.commit()
    await log_employer_action(
        db=db,
        user_id=current_user.id,
        vacancy_id=vacancy.id,
        action="vacancy_promoted",
        meta={"days": payload.days},
    )
    return {"status": "promoted"}
