"""Bot-service-keyed endpoints for Phase 2 channel approval.

The tgbot calls these endpoints when the admin clicks the inline
✅ Approve / ❌ Reject buttons on a daily candidate DM. The endpoints
are gated behind the same ``x-bot-service-key`` header used for the
Telegram-link flow — they're not user-facing.

Decision flow on approval:

1. Flip ``channel_candidates.status`` to ``approved``, stamp
   ``decided_at`` and ``admin_message_id``.
2. Insert a ``publication_queue`` row with ``target='channel'``,
   ``topic_id=NULL``, ``scheduled_for`` set to the next available
   posting slot (default: 10:00/12:00/14:00/16:00/18:00 MSK).
3. The existing publisher worker picks it up on its next 15-min tick.

Rejection just flips the status — no queue row created.

Both endpoints are idempotent: a repeat call after a final decision
returns the same response without re-inserting anything.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config import settings
from app.deps import DbSession
from app.models import ChannelCandidate, PublicationQueueItem, Vacancy
from app.services.tg_publication import render_post
from app.services.vacancy_summary import summarise_and_cache
from app.time_utils import now_utc

router = APIRouter(prefix="/internal/channel-approval", tags=["channel-approval"])

# MSK is UTC+3, no DST since 2014. Hard-coded rather than via zoneinfo
# to keep this dependency-free in CI containers without the tz data.
_MSK = timezone(timedelta(hours=3))

# Slot times (MSK) the publisher worker will dispatch to the channel.
# Spread across the working day so the channel feels live without
# spam. The next-slot picker rotates through these.
_POSTING_SLOTS_MSK: tuple[time, ...] = (
    time(10, 0),
    time(12, 0),
    time(14, 0),
    time(16, 0),
    time(18, 0),
)


async def _require_bot_service_key(
    x_bot_service_key: str | None = Header(default=None),
) -> None:
    if not x_bot_service_key or not secrets.compare_digest(
        x_bot_service_key, settings.bot_service_key
    ):
        raise HTTPException(status_code=401, detail="Invalid bot service key")


class ChannelDecisionRequest(BaseModel):
    """Payload from the tgbot callback."""

    candidate_id: int = Field(..., gt=0)
    admin_message_id: int | None = Field(default=None)


class ChannelDecisionResponse(BaseModel):
    """Mirrors the candidate state after the call."""

    candidate_id: int
    status: str
    queue_id: int | None = None
    scheduled_for: datetime | None = None
    detail: str = ""


def _next_posting_slot(now: datetime) -> datetime:
    """Pick the next posting slot after ``now`` in MSK.

    Falls through to tomorrow's first slot when ``now`` is past today's
    last slot. Returned datetime is timezone-aware in MSK; callers
    convert to UTC for storage.
    """
    msk_now = now.astimezone(_MSK)
    for slot in _POSTING_SLOTS_MSK:
        candidate = msk_now.replace(hour=slot.hour, minute=slot.minute, second=0, microsecond=0)
        if candidate > msk_now:
            return candidate
    # All today's slots have passed — schedule the first one tomorrow.
    tomorrow = msk_now + timedelta(days=1)
    first = _POSTING_SLOTS_MSK[0]
    return tomorrow.replace(hour=first.hour, minute=first.minute, second=0, microsecond=0)


@router.post(
    "/approve",
    response_model=ChannelDecisionResponse,
    dependencies=[Depends(_require_bot_service_key)],
)
async def approve_candidate(
    payload: ChannelDecisionRequest,
    db: DbSession,
) -> ChannelDecisionResponse:
    """Approve a candidate → create the matching ``publication_queue`` row."""
    candidate = await db.scalar(
        select(ChannelCandidate).where(ChannelCandidate.id == payload.candidate_id)
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Idempotency: if it's already approved with a queue row, return that.
    if candidate.status == "approved":
        queue_row = await db.scalar(
            select(PublicationQueueItem)
            .where(PublicationQueueItem.vacancy_id == candidate.vacancy_id)
            .where(PublicationQueueItem.target == "channel")
        )
        return ChannelDecisionResponse(
            candidate_id=candidate.id,
            status="approved",
            queue_id=queue_row.id if queue_row else None,
            scheduled_for=queue_row.scheduled_for if queue_row else None,
            detail="already_approved",
        )

    if candidate.status == "rejected":
        # Refuse to flip a final decision — admin can re-issue via a
        # fresh batch if they change their mind.
        raise HTTPException(status_code=409, detail="Candidate already rejected")

    vacancy = await db.scalar(select(Vacancy).where(Vacancy.id == candidate.vacancy_id))
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy gone")

    # Render the channel post. Channel target has no topic; uses the
    # same renderer as the group flow so formatting stays consistent.
    summary = await summarise_and_cache(vacancy) or (vacancy.title or "")
    top_skills = [s.strip() for s in (vacancy.parsed_skills or "").split(",") if s.strip()]
    rendered = render_post(
        vacancy=vacancy,
        ai_summary=summary,
        top_skills=top_skills,
        base_url=settings.app_base_url,
        locale="ru",
    )

    scheduled_msk = _next_posting_slot(now_utc())
    scheduled_utc = scheduled_msk.astimezone(UTC).replace(tzinfo=None)

    queue_row = PublicationQueueItem(
        vacancy_id=candidate.vacancy_id,
        target="channel",
        topic_id=None,
        rendered_text=rendered,
        status="pending",
        scheduled_for=scheduled_utc,
        attempts=0,
    )
    db.add(queue_row)

    candidate.status = "approved"
    candidate.decided_at = now_utc()
    if payload.admin_message_id is not None:
        candidate.admin_message_id = payload.admin_message_id

    await db.flush()
    await db.commit()
    await db.refresh(queue_row)

    return ChannelDecisionResponse(
        candidate_id=candidate.id,
        status="approved",
        queue_id=queue_row.id,
        scheduled_for=queue_row.scheduled_for,
        detail="enqueued",
    )


@router.post(
    "/reject",
    response_model=ChannelDecisionResponse,
    dependencies=[Depends(_require_bot_service_key)],
)
async def reject_candidate(
    payload: ChannelDecisionRequest,
    db: DbSession,
) -> ChannelDecisionResponse:
    """Reject a candidate → flip status, no queue row."""
    candidate = await db.scalar(
        select(ChannelCandidate).where(ChannelCandidate.id == payload.candidate_id)
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if candidate.status == "rejected":
        return ChannelDecisionResponse(
            candidate_id=candidate.id,
            status="rejected",
            detail="already_rejected",
        )
    if candidate.status == "approved":
        raise HTTPException(status_code=409, detail="Candidate already approved")

    candidate.status = "rejected"
    candidate.decided_at = now_utc()
    if payload.admin_message_id is not None:
        candidate.admin_message_id = payload.admin_message_id

    await db.commit()
    return ChannelDecisionResponse(
        candidate_id=candidate.id,
        status="rejected",
        detail="dismissed",
    )
