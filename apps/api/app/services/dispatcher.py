from datetime import timedelta

from app.models import DigestDispatchEvent, DigestPreference, User
from app.services.delivery import send_email_digest, send_telegram_digest
from app.services.digest import digest_channels, rank_for_user
from app.time_utils import now_utc
from sqlalchemy import desc, select
from sqlalchemy.orm import Session


def should_dispatch(pref: DigestPreference, frequency: str) -> bool:
    return pref.frequency == frequency


def already_dispatched_recently(db: Session, user_id: int, frequency: str) -> bool:
    now = now_utc()
    lookback = timedelta(hours=23) if frequency == "daily" else timedelta(days=6, hours=23)
    threshold = now - lookback
    existing = db.scalar(
        select(DigestDispatchEvent)
        .where(DigestDispatchEvent.user_id == user_id)
        .where(DigestDispatchEvent.frequency == frequency)
        .where(DigestDispatchEvent.created_at >= threshold)
        .order_by(desc(DigestDispatchEvent.created_at))
    )
    return existing is not None


def dispatch_digest_for_user(db: Session, user: User, pref: DigestPreference, frequency: str) -> DigestDispatchEvent:
    if not should_dispatch(pref, frequency):
        event = DigestDispatchEvent(
            user_id=user.id,
            frequency=frequency,
            channels_csv="",
            items_count=0,
            status="skipped",
            error="Preference frequency does not match run frequency",
            created_at=now_utc(),
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    if already_dispatched_recently(db, user.id, frequency):
        event = DigestDispatchEvent(
            user_id=user.id,
            frequency=frequency,
            channels_csv="",
            items_count=0,
            status="skipped",
            error="Digest already sent in current period",
            created_at=now_utc(),
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    ranked = rank_for_user(db, user, limit=10)
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
    event = DigestDispatchEvent(
        user_id=user.id,
        frequency=frequency,
        channels_csv=",".join(channels),
        items_count=len(ranked),
        status=status,
        error="; ".join(errors) if errors else None,
        created_at=now_utc(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def dispatch_all(db: Session, frequency: str) -> list[DigestDispatchEvent]:
    users = db.scalars(select(User).where(User.role == "seeker")).all()
    events: list[DigestDispatchEvent] = []
    for user in users:
        pref = db.scalar(select(DigestPreference).where(DigestPreference.user_id == user.id))
        if not pref:
            continue
        events.append(dispatch_digest_for_user(db, user, pref, frequency))
    return events
