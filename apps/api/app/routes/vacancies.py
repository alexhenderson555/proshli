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

from app.auth import get_current_user, get_optional_user
from app.deps import DbSession
from app.models import (
    EmployerActionLog,
    EmployerVacancy,
    MatchReasoning,
    Plan,
    Resume,
    Subscription,
    User,
    Vacancy,
)
from app.schemas import (
    EmployerActionLogOut,
    EmployerVacancyAnalyticsOut,
    EmployerVacancyPageOut,
    MatchScoreOut,
    VacancyCreateRequest,
    VacancyOut,
    VacancyPromoteRequest,
    VacancyStatsOut,
    VacancyUpdateRequest,
)
from app.services.embeddings import get_embedding_service
from app.services.employer import log_employer_action, require_employer_ownership
from app.services.hh_live import fetch_live_hh_vacancies
from app.services.match_rerank import rerank_top_n
from app.services.match_score import batch_match_scores, match_tier, user_resume_embedding
from app.services.semantic_search import embed_vacancy, search_vacancies_semantic
from app.time_utils import now_utc

router = APIRouter(prefix="/vacancies", tags=["vacancies"])


_SORT_FIELDS = {
    "published_at": Vacancy.published_at,
    "applications_count": Vacancy.applications_count,
    "title": Vacancy.title,
}


async def _user_has_semantic_search(db: DbSession, user: User) -> bool:
    """Return True if the user's active plan grants semantic search.

    Resolved via the same Subscription → Plan join used by the AI quota
    code (``app/services/ai_guardrails.py::_resolve_daily_limit``). Users
    without a Subscription row (legacy / unfinished onboarding) fall back
    to the ``semantic_search=False`` of the implicit free tier — that's
    the conservative default for a paid feature.
    """
    plan = await db.scalar(
        select(Plan)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.user_id == user.id)
    )
    return bool(plan is not None and plan.semantic_search)


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
    # Wave 4: index the freshly-published row so semantic search picks it
    # up immediately. Failure is non-fatal — see ``embed_vacancy`` for the
    # degrade-to-NULL behaviour.
    await embed_vacancy(db, vacancy, get_embedding_service())
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
    include_match: bool = Query(default=False),
    current_user: User | None = Depends(get_optional_user),
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

    # Resolve the resume embedding once, shared across all return paths.
    resume_emb: list[float] | None = None
    if include_match and current_user is not None:
        resume_emb = await user_resume_embedding(db, current_user.id)

    async def _apply_scores(items: list[VacancyOut]) -> list[VacancyOut]:
        """Attach match_score / match_tier to DB-backed items in-place.

        hh_live items are external and don't exist in our vacancies table,
        so their scores remain None. Returns the mutated list for convenience.
        """
        if resume_emb is None:
            return items
        scorable_ids = [
            item.id
            for item in items
            if item.id and getattr(item, "source", "") != "hh_live"
        ]
        scores = await batch_match_scores(db, resume_emb, scorable_ids)
        result: list[VacancyOut] = []
        for item in items:
            s = scores.get(item.id) if item.id else None
            if s is not None:
                # Reconstruct with match fields to survive Pydantic's
                # immutability — model_validate on a dict is always safe.
                item = VacancyOut(
                    **{**item.model_dump(), "match_score": s, "match_tier": match_tier(s)}
                )
            result.append(item)
        return result

    if source == "hh_live":
        db_items = []
    elif source and source != "hh_live":
        return await _apply_scores(db_items)
    if not include_live_hh:
        return await _apply_scores(db_items)

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
    return await _apply_scores(combined)


@router.get("/stats", response_model=VacancyStatsOut)
async def vacancy_stats(db: DbSession) -> VacancyStatsOut:
    """Anonymous-readable aggregates for the landing hero metric strip.

    All counts ignore soft-deleted rows and the live-hh.ru pass-through
    (those aren't ours to count). ``last_24h`` is bounded by published_at
    rather than ingestion time so the number tracks what users actually
    see on the feed.
    """
    base = select(func.count()).select_from(Vacancy).where(
        Vacancy.is_deleted.is_(False),
        Vacancy.is_active.is_(True),
    )
    total = await db.scalar(base) or 0
    last_24h = (
        await db.scalar(base.where(Vacancy.published_at >= now_utc() - timedelta(days=1)))
        or 0
    )
    sources = (
        await db.scalar(
            select(func.count(func.distinct(Vacancy.source))).where(
                Vacancy.is_deleted.is_(False),
                Vacancy.is_active.is_(True),
            )
        )
        or 0
    )
    return VacancyStatsOut(total=total, last_24h=last_24h, sources=sources)


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


@router.get("/search/semantic", response_model=list[VacancyOut])
async def search_semantic(
    db: DbSession,
    q: str = Query(..., min_length=1, max_length=512, description="Search text"),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> list[VacancyOut]:
    """Semantic vacancy search via pgvector cosine distance.

    Gated on ``plan.semantic_search`` (Pro and Employer plans only). Free
    tier callers get 402 ``payment_required`` so the FE can prompt for an
    upgrade rather than silently degrade to keyword search — that would
    mask why results look "worse" than the user expected.

    The route accepts a single ``q`` plus a ``limit`` and returns up to
    ``limit`` rows ordered by cosine distance. Filters that the keyword
    endpoint exposes (``location``, ``level``, ``stack``) are deliberately
    omitted here — the whole point of semantic search is that the
    embedding model handles those signals natively. A composite endpoint
    that combines both ranking modes can come in a later wave.
    """
    if not await _user_has_semantic_search(db, current_user):
        raise HTTPException(
            status_code=402,
            detail=(
                "Семантический поиск доступен на тарифах Pro и Работодатель."
            ),
        )

    rows = await search_vacancies_semantic(
        db, q, get_embedding_service(), limit=limit
    )
    return [VacancyOut.model_validate(row) for row in rows]


@router.get("/match-feed", response_model=list[VacancyOut])
async def match_feed(
    db: DbSession,
    top: int = Query(default=10, ge=1, le=20),
    pool: int = Query(default=50, ge=10, le=50),
    current_user: User = Depends(get_current_user),
) -> list[VacancyOut]:
    """LLM-reranked "For me" feed.

    Pipeline:

    1. Resolve the caller's most recent resume + embedding.
    2. Pull the cosine top-``pool`` vacancies (default 50) that have an
       embedding and aren't soft-deleted / archived.
    3. Hand them to :func:`app.services.match_rerank.rerank_top_n` —
       cached rows are reused, the missing slice is evaluated in a single
       Claude call.
    4. Return the top ``top`` vacancies enriched with
       ``match_reasoning`` + ``rerank_score``, ordered by rerank score
       DESC. ``match_score`` / ``match_tier`` carry the cosine signal so
       both fields render alongside each other in the UI.

    Degrades gracefully:

    * No resume on file → 404.
    * Cosine candidate set is empty → returns ``[]``.
    * Reranker returns nothing (no Anthropic key, network error) → falls
      back to the cosine-ordered top-``top`` so the tab is never blank.
    """
    resume = await db.scalar(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(desc(Resume.created_at))
        .limit(1)
    )
    if resume is None:
        raise HTTPException(status_code=404, detail="No resume on file")

    resume_emb = await user_resume_embedding(db, current_user.id)
    if resume_emb is None:
        raise HTTPException(status_code=404, detail="No resume embedding available")

    # Fetch the cosine top-``pool`` directly via pgvector. The dedicated
    # ``batch_match_scores`` path takes a fixed id list — here we want
    # the ranking too, so we run the cosine sort in SQL.
    rows = await db.execute(
        select(
            Vacancy,
            (1 - Vacancy.embedding.cosine_distance(resume_emb)).label("score"),  # type: ignore[attr-defined]
        )
        .where(
            Vacancy.embedding.is_not(None),
            Vacancy.is_deleted.is_(False),
            Vacancy.is_active.is_(True),
        )
        .order_by(desc("score"))
        .limit(pool)
    )
    candidates: list[tuple[Vacancy, float]] = [
        (vac, float(score)) for vac, score in rows.all()
    ]
    if not candidates:
        return []

    cosine_by_vid: dict[int, float] = {v.id: s for v, s in candidates}
    vacancy_by_vid: dict[int, Vacancy] = {v.id: v for v, _ in candidates}

    reranked = await rerank_top_n(db, resume, candidates, top_n=top)

    # Fallback path: reranker returned nothing — serve the cosine top-N
    # directly so the tab still loads.
    if not reranked:
        cosine_top = candidates[:top]
        return [
            VacancyOut(
                **{
                    **VacancyOut.model_validate(vac).model_dump(),
                    "match_score": score,
                    "match_tier": match_tier(score),
                }
            )
            for vac, score in cosine_top
        ]

    out: list[VacancyOut] = []
    for reasoning in reranked:
        vac = vacancy_by_vid.get(reasoning.vacancy_id)
        if vac is None:
            continue
        cosine = cosine_by_vid.get(reasoning.vacancy_id)
        base = VacancyOut.model_validate(vac).model_dump()
        base.update(
            {
                "match_score": cosine,
                "match_tier": match_tier(cosine) if cosine is not None else None,
                "match_reasoning": reasoning.reasoning_ru,
                "rerank_score": float(reasoning.rerank_score),
            }
        )
        out.append(VacancyOut(**base))
    return out


@router.get("/{vacancy_id}/match-score", response_model=MatchScoreOut)
async def get_match_score(
    vacancy_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> MatchScoreOut:
    """Return the cosine match score between the caller's resume and a vacancy.

    Always-authed — anonymous callers get 401 from ``get_current_user``.
    404 when the caller has no resume on file, or the vacancy has no embedding.
    Used by the vacancy detail page to load the score after page render without
    re-fetching the full vacancy list. Surfaces cached ``match_reasonings``
    (Match-score 2.0) when one is on file so the FE can render a "Why this
    fits?" blurb without re-running the reranker.
    """
    resume_emb = await user_resume_embedding(db, current_user.id)
    if resume_emb is None:
        raise HTTPException(status_code=404, detail="No resume on file")
    scores = await batch_match_scores(db, resume_emb, [vacancy_id])
    score = scores.get(vacancy_id)
    if score is None:
        raise HTTPException(status_code=404, detail="Vacancy not embedded")

    # Best-effort cached reasoning lookup. We always have a resume here
    # (otherwise ``user_resume_embedding`` would have returned None and we'd
    # have 404'd already), so a small extra SELECT is cheap.
    resume = await db.scalar(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(desc(Resume.created_at))
        .limit(1)
    )
    reasoning_row: MatchReasoning | None = None
    if resume is not None:
        reasoning_row = await db.scalar(
            select(MatchReasoning).where(
                MatchReasoning.resume_id == resume.id,
                MatchReasoning.vacancy_id == vacancy_id,
            )
        )
    return MatchScoreOut(
        score=score,
        tier=match_tier(score),
        reasoning=reasoning_row.reasoning_ru if reasoning_row else None,
        rerank_score=float(reasoning_row.rerank_score) if reasoning_row else None,
    )


@router.get("/{vacancy_id}", response_model=VacancyOut)
async def get_vacancy(
    vacancy_id: int,
    db: DbSession,
) -> Vacancy:
    """Public detail endpoint — replaces the client-side list-scan workaround.

    Returns 404 for missing/soft-deleted rows. Live hh.ru records aren't
    represented here (they're synthesised in :func:`list_vacancies`); IDs from
    that path won't resolve, which is the correct behaviour.
    """
    vacancy = await db.get(Vacancy, vacancy_id)
    if vacancy is None or vacancy.is_deleted:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy


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
    if vacancy is None or vacancy.is_deleted:
        # ``require_employer_ownership`` passed (the join row exists), but the
        # vacancy itself is gone or already soft-deleted.  Surface a clean 404
        # rather than silently writing a phantom audit log row.
        raise HTTPException(status_code=404, detail="Vacancy not found")

    vacancy.is_deleted = True
    vacancy.is_active = False
    vacancy.deleted_at = now_utc()
    await db.commit()
    await log_employer_action(
        db=db,
        user_id=current_user.id,
        vacancy_id=vacancy.id,
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
