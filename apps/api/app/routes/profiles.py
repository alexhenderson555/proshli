"""Seeker / employer profile upsert endpoints (async).

Profiles are auto-created on first read so the FE never has to handle a 404
for the "I haven't filled this in yet" case.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth import get_current_user
from app.deps import DbSession
from app.models import EmployerProfile, SeekerProfile, User
from app.schemas import (
    EmployerProfileOut,
    EmployerProfileUpdate,
    SeekerProfileOut,
    SeekerProfileUpdate,
)
from app.time_utils import now_utc

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _seeker_out(profile: SeekerProfile) -> SeekerProfileOut:
    return SeekerProfileOut(
        full_name=profile.full_name,
        target_role=profile.target_role,
        location=profile.location,
        about=profile.about,
        skills=[s.strip() for s in profile.skills_csv.split(",") if s.strip()],
        updated_at=profile.updated_at,
    )


@router.put("/seeker", response_model=SeekerProfileOut)
async def upsert_seeker_profile(
    payload: SeekerProfileUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> SeekerProfileOut:
    if current_user.role != "seeker":
        raise HTTPException(
            status_code=403, detail="Only seekers can edit seeker profile"
        )

    profile = await db.scalar(
        select(SeekerProfile).where(SeekerProfile.user_id == current_user.id)
    )
    if not profile:
        profile = SeekerProfile(user_id=current_user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    profile.full_name = payload.full_name
    profile.target_role = payload.target_role
    profile.location = payload.location
    profile.about = payload.about
    profile.skills_csv = ", ".join(payload.skills)
    profile.updated_at = now_utc()
    await db.commit()
    await db.refresh(profile)

    return _seeker_out(profile)


@router.get("/seeker", response_model=SeekerProfileOut)
async def get_seeker_profile(
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> SeekerProfileOut:
    if current_user.role != "seeker":
        raise HTTPException(
            status_code=403, detail="Only seekers can read seeker profile"
        )
    profile = await db.scalar(
        select(SeekerProfile).where(SeekerProfile.user_id == current_user.id)
    )
    if not profile:
        profile = SeekerProfile(user_id=current_user.id, updated_at=now_utc())
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return _seeker_out(profile)


@router.put("/employer", response_model=EmployerProfileOut)
async def upsert_employer_profile(
    payload: EmployerProfileUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> EmployerProfile:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can edit employer profile"
        )

    profile = await db.scalar(
        select(EmployerProfile).where(EmployerProfile.user_id == current_user.id)
    )
    if not profile:
        profile = EmployerProfile(user_id=current_user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    profile.company_name = payload.company_name
    profile.website = payload.website
    profile.description = payload.description
    profile.updated_at = now_utc()
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/employer", response_model=EmployerProfileOut)
async def get_employer_profile(
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> EmployerProfile:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can read employer profile"
        )
    profile = await db.scalar(
        select(EmployerProfile).where(EmployerProfile.user_id == current_user.id)
    )
    if not profile:
        profile = EmployerProfile(user_id=current_user.id, updated_at=now_utc())
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile
