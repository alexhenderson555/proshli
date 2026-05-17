"""Resume upload + versioned-resume builder endpoints (async)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import desc, select

from app.auth import get_current_user
from app.deps import DbSession
from app.models import Resume, ResumeVersion, User
from app.schemas import (
    ResumeOut,
    ResumeVersionCreate,
    ResumeVersionOut,
)
from app.services.resume_parser import extract_skills, extract_text_from_pdf_bytes
from app.time_utils import now_utc

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
    resume = Resume(
        user_id=current_user.id,
        name=name,
        raw_text=raw_text,
        parsed_skills=", ".join(skills),
        created_at=now_utc(),
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
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
