"""Digest dispatch loop: pick which seekers get a digest now and deliver."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DigestDispatchEvent, DigestPreference, User
from app.services.delivery import send_email_digest, send_telegram_digest
from app.services.digest import digest_channels, rank_for_user
from app.time_utils import now_utc


def should_dispatch(pref: DigestPreference, frequency: str) -> bool:
    return pref.frequency == frequency


async def already_dispatched_recently(
    db: AsyncSession, user_id: int, frequency: str
) -> bool:
    now = now_utc()
    lookback = (
        timedelta(hours=23) if frequency == "daily" else timedelta(days=6, hours=23)
    )
    threshold = now - lookback
    existing = await db.scalar(
        select(DigestDispatchEvent)
        .where(DigestDispatchEvent.user_id == user_id)
        .where(DigestDispatchEvent.frequency == frequency)
        .where(DigestDispatchEvent.created_at >= threshold)
        .order_by(desc(DigestDispatchEvent.created_at))
    )
    return existing is not None


async def _record(
    db: AsyncSession,
    user_id: int,
    frequency: str,
    *,
    channels_csv: str,
    items_count: int,
    status: str,
    error: str | None,
) -> DigestDispatchEvent:
    event = DigestDispatchEvent(
        user_id=user_id,
        frequency=frequency,
        channels_csv=channels_csv,
        items_count=items_count,
        status=status,
        error=error,
        created_at=now_utc(),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def dispatch_digest_for_user(
    db: AsyncSession,
    user: User,
    pref: DigestPreference,
    frequency: str,
) -> DigestDispatchEvent:
    if not should_dispatch(pref, frequency):
        return await _record(
            db,
            user.id,
            frequency,
            channels_csv="",
            items_count=0,
            status="skipped",
            error="Preference frequency does not match run frequency",
        )

    if await already_dispatched_recently(db, user.id, frequency):
        return await _record(
            db,
            user.id,
            frequency,
            channels_csv="",
            items_count=0,
            status="skipped",
            error="Digest already sent in current period",
        )

    ranked = await rank_for_user(db, user, limit=10)
    items_payload = [
        {
            "title": item.vacancy.title,
            "company": item.vacancy.company,
            "location": item.vacancy.location,
            "score_reason": item.reason,
        }
        for item in ranked
    ]
    channels = digest_channels(pref)
    errors: list[str] = []

    if "telegram" in channels:
        ok, err = send_telegram_digest(pref.telegram_chat_id or "", items_payload)
        if not ok:
            errors.append(f"telegram: {err}")
    if "email" in channels:
        ok, err = send_email_digest(user.email, items_payload)
        if not ok:
            errors.append(f"email: {err}")

    status = "sent" if not errors else "failed"
    return await _record(
        db,
        user.id,
        frequency,
        channels_csv=",".join(channels),
        items_count=len(ranked),
        status=status,
        error="; ".join(errors) if errors else None,
    )


async def dispatch_all(
    db: AsyncSession, frequency: str
) -> list[DigestDispatchEvent]:
    users = (await db.scalars(select(User).where(User.role == "seeker"))).all()
    events: list[DigestDispatchEvent] = []
    for user in users:
        pref = await db.scalar(
            select(DigestPreference).where(DigestPreference.user_id == user.id)
        )
        if not pref:
            continue
        events.append(await dispatch_digest_for_user(db, user, pref, frequency))
    return events
