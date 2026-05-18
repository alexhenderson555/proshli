"""AI usage guardrails: keyword gating + per-day request budget.

The budget cap is enforced per-user via ``AiUsageEvent`` row counts for the
current calendar date. As of Wave 3 the cap is *tier-aware* — we look up the
user's active ``Subscription`` row and read ``plan.ai_daily_limit`` instead of
the flat process-wide setting. Users without a subscription row (the lazy-
created "free" row is materialised on first ``/billing/me`` hit, so this only
happens for accounts that have never touched billing) fall back to
``settings.ai_daily_request_limit`` to keep behaviour stable for legacy users.

The keyword gate is intentionally loose — it filters obvious off-topic prompts
before they reach the model and is cheaper than a tool-use round trip.
"""

from __future__ import annotations

from app.config import settings
from app.models import AiUsageEvent, Plan, Subscription, User
from app.time_utils import now_utc
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

CAREER_KEYWORDS = {
    "работа",
    "вакансия",
    "резюме",
    "карьера",
    "отклик",
    "интервью",
    "зарплата",
    "позиция",
    "junior",
    "middle",
    "senior",
    "python",
    "frontend",
    "backend",
    "аналитик",
}


def is_career_related(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in CAREER_KEYWORDS)


async def _resolve_daily_limit(db: AsyncSession, user: User) -> int:
    """Return the user's per-day AI-request cap.

    Resolves through the active subscription → plan join. We treat ``pending``
    and ``past_due`` rows as still entitling the user to their tier's limit
    (the alternative — downgrading the moment a charge fails — would punish
    users for transient payment hiccups and is handled by the renewal task on
    a longer time horizon).
    """
    plan = await db.scalar(
        select(Plan)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.user_id == user.id)
    )
    if plan is not None:
        return int(plan.ai_daily_limit)
    return int(settings.ai_daily_request_limit)


async def can_use_ai_today(
    db: AsyncSession, user: User
) -> tuple[bool, int, int]:
    """Return ``(allowed, used_today, limit)`` for the calling user.

    ``limit`` is resolved through the user's plan (Wave 3); callers should
    surface it on ``data-usage`` frames and in error messages so users see
    the cap that applies to *them*, not a generic process-wide constant.

    We store ``AiUsageEvent.created_at`` via :func:`now_utc` (UTC, naive),
    so the "today" comparison must also be UTC. Using ``date.today()`` (local)
    diverged by ±1 day whenever the host TZ wasn't UTC — silently undercounting
    events near the day boundary on developer machines and CI runners alike.
    """
    today_utc = now_utc().date()
    used_today = (
        await db.scalar(
            select(func.count(AiUsageEvent.id))
            .where(AiUsageEvent.user_id == user.id)
            .where(func.date(AiUsageEvent.created_at) == today_utc)
        )
        or 0
    )
    limit = await _resolve_daily_limit(db, user)
    return used_today < limit, used_today, limit


async def store_ai_usage(db: AsyncSession, user: User, prompt_chars: int) -> None:
    event = AiUsageEvent(
        user_id=user.id, prompt_chars=prompt_chars, created_at=now_utc()
    )
    db.add(event)
    await db.commit()


def extract_basic_filters(text: str) -> dict[str, str]:
    lowered = text.lower()
    filters: dict[str, str] = {}

    if "удален" in lowered or "remote" in lowered:
        filters["work_mode"] = "remote"
    if "офис" in lowered:
        filters["work_mode"] = "office"
    if "гибрид" in lowered:
        filters["work_mode"] = "hybrid"

    if "junior" in lowered:
        filters["level"] = "junior"
    elif "middle" in lowered:
        filters["level"] = "middle"
    elif "senior" in lowered:
        filters["level"] = "senior"

    for stack in ("python", "java", "javascript", "typescript", "go", "kotlin", "c#"):
        if stack in lowered:
            filters["stack"] = stack
            break

    return filters
