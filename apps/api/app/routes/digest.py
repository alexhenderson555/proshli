"""Digest preferences + preview endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.auth import get_current_user
from app.deps import DbSession
from app.models import DigestPreference, User
from app.schemas import (
    DigestItem,
    DigestPreferenceOut,
    DigestPreferenceUpdate,
    DigestPreviewOut,
)
from app.services.digest import digest_channels, rank_for_user
from app.time_utils import now_utc

router = APIRouter(prefix="/digest", tags=["digest"])


async def _get_or_create_preference(
    db: DbSession, user_id: int
) -> DigestPreference:
    pref = await db.scalar(
        select(DigestPreference).where(DigestPreference.user_id == user_id)
    )
    if not pref:
        pref = DigestPreference(
            user_id=user_id,
            frequency="daily",
            via_telegram=True,
            via_email=False,
        )
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
    return pref


@router.put("/preferences", response_model=DigestPreferenceOut)
async def update_digest_preferences(
    payload: DigestPreferenceUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> DigestPreference:
    pref = await _get_or_create_preference(db, current_user.id)
    pref.frequency = payload.frequency
    pref.via_telegram = payload.via_telegram
    pref.via_email = payload.via_email
    pref.telegram_chat_id = payload.telegram_chat_id
    pref.updated_at = now_utc()
    await db.commit()
    await db.refresh(pref)
    return pref


@router.get("/preferences", response_model=DigestPreferenceOut)
async def get_digest_preferences(
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> DigestPreference:
    return await _get_or_create_preference(db, current_user.id)


@router.get("/preview", response_model=DigestPreviewOut)
async def preview_digest(
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> DigestPreviewOut:
    pref = await _get_or_create_preference(db, current_user.id)
    ranked = await rank_for_user(db, current_user, limit=10)
    items = [
        DigestItem(
            vacancy_id=item.vacancy.id,
            title=item.vacancy.title,
            company=item.vacancy.company,
            location=item.vacancy.location,
            score_reason=item.reason,
        )
        for item in ranked
    ]
    return DigestPreviewOut(
        frequency=pref.frequency,
        channels=digest_channels(pref),
        items=items,
    )
