"""Resume upload + versioned-resume builder endpoints (async)."""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, desc, select

from app.auth import get_current_user
from app.deps import DbSession
from app.middleware.rate_limit import RateLimit
from app.models import MatchReasoning, Resume, ResumeVersion, User
from app.schemas import (
    ResumeImproveRequest,
    ResumeImproveResponse,
    ResumeOut,
    ResumeVersionCreate,
    ResumeVersionOut,
)
from app.services.ai_guardrails import can_use_ai_today, store_ai_usage
from app.services.embeddings import get_embedding_service
from app.services.llm import get_llm_service
from app.services.resume_parser import extract_skills, extract_text_from_pdf_bytes
from app.time_utils import now_utc

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post(
    "/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED
)
async def upload_resume(
    db: DbSession,
    name: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> Resume:
    if current_user.role != "seeker":
        raise HTTPException(status_code=403, detail="Only seekers can upload resumes")

    content = await file.read()
    filename = (file.filename or "").lower()

    if filename.endswith(".pdf"):
        raw_text = extract_text_from_pdf_bytes(content)
    else:
        raw_text = content.decode("utf-8", errors="ignore")

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from resume")

    skills = extract_skills(raw_text)

    try:
        embedding_service = get_embedding_service()
        # voyage-3 hard limit is ~32k tokens; 8000 chars is a safe + cheap cap.
        vectors = await embedding_service.embed_texts([raw_text[:8000]])
        embedding = vectors[0]
    except Exception as exc:
        log.warning("resume.embedding_failed", error=str(exc))
        embedding = None

    resume = Resume(
        user_id=current_user.id,
        name=name,
        raw_text=raw_text,
        parsed_skills=", ".join(skills),
        embedding=embedding,
        created_at=now_utc(),
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    # Match-score 2.0 cache invalidation. A new resume invalidates every
    # cached (resume_id, vacancy_id) reasoning row for that user — the
    # rerank prompt embeds the resume blob, so stale rows would surface
    # explanations grounded in the old skills/experience. We scope the
    # delete to the user's *previous* resumes (everything except the row
    # we just inserted) — keeps it cheap and avoids racing with concurrent
    # match-feed requests that may have just landed for the new resume.
    await db.execute(
        delete(MatchReasoning).where(
            MatchReasoning.resume_id.in_(
                select(Resume.id).where(
                    Resume.user_id == current_user.id,
                    Resume.id != resume.id,
                )
            )
        )
    )
    await db.commit()
    return resume


@router.post(
    "/versions",
    response_model=ResumeVersionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_resume_version(
    payload: ResumeVersionCreate,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> ResumeVersionOut:
    if current_user.role != "seeker":
        raise HTTPException(
            status_code=403, detail="Only seekers can create resume versions"
        )
    version = ResumeVersion(
        user_id=current_user.id,
        name=payload.name,
        target_role=payload.target_role,
        content_json=json.dumps(payload.content, ensure_ascii=False),
        created_at=now_utc(),
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return ResumeVersionOut(
        id=version.id,
        name=version.name,
        target_role=version.target_role,
        content=json.loads(version.content_json or "{}"),
        created_at=version.created_at,
    )


@router.get("/versions", response_model=list[ResumeVersionOut])
async def list_resume_versions(
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> list[ResumeVersionOut]:
    if current_user.role != "seeker":
        raise HTTPException(
            status_code=403, detail="Only seekers can list resume versions"
        )
    rows = (
        await db.scalars(
            select(ResumeVersion)
            .where(ResumeVersion.user_id == current_user.id)
            .order_by(desc(ResumeVersion.created_at))
        )
    ).all()
    return [
        ResumeVersionOut(
            id=item.id,
            name=item.name,
            target_role=item.target_role,
            content=json.loads(item.content_json or "{}"),
            created_at=item.created_at,
        )
        for item in rows
    ]


@router.post(
    "/versions/{version_id}/improve",
    response_model=ResumeImproveResponse,
    dependencies=[
        # Resume-improve is heavier than chat (longer prompts, more output);
        # keep the per-minute knob tight so a runaway client can't drain
        # the daily LLM budget in seconds.
        Depends(RateLimit("resume-improve", limit=5, window_seconds=60)),
    ],
)
async def improve_resume_version(
    version_id: int,
    payload: ResumeImproveRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> ResumeImproveResponse:
    """Return an LLM-tightened summary + bullet suggestions for one version.

    Seeker-only; counts against the same per-day AI budget as ``/ai/chat``
    so the pro/free tier caps stay honest. The version blob is read from
    ``content_json`` and passed to the LLM as-is — the model decides what's
    worth rewriting.
    """
    if current_user.role != "seeker":
        raise HTTPException(
            status_code=403, detail="Only seekers can improve resume versions"
        )

    version = await db.scalar(
        select(ResumeVersion)
        .where(ResumeVersion.id == version_id)
        .where(ResumeVersion.user_id == current_user.id)
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Resume version not found")

    allowed, used_today, limit = await can_use_ai_today(db, current_user)
    if not allowed:
        # Mirror the streaming /ai/chat error shape: machine-readable ``code``
        # plus the numbers the client needs to render a tier-aware nudge.
        raise HTTPException(
            status_code=429,
            detail={
                "code": "daily_limit_reached",
                "limit": limit,
                "used_today": used_today,
            },
        )

    try:
        content_blob = json.loads(version.content_json or "{}")
    except json.JSONDecodeError as exc:
        # Stored JSON is corrupt — bail out clearly rather than feed
        # garbage to the model.
        raise HTTPException(
            status_code=500, detail="Stored resume content is malformed"
        ) from exc

    llm = get_llm_service()
    improvement = await llm.improve_resume(
        content=content_blob,
        target_role=payload.target_role or (version.target_role or ""),
        focus=payload.focus,
    )

    # Charge the budget after a successful call. We treat this as one AI
    # request, identical to /ai/chat — the user sees a single decrement.
    await store_ai_usage(
        db, current_user, prompt_chars=len(version.content_json or "")
    )

    return ResumeImproveResponse(
        summary=improvement.summary,
        suggestions=improvement.suggestions,
        used_today=used_today + 1,
        limit=limit,
        backend=llm.name,
    )
