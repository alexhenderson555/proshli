"""AI usage guardrails: keyword gating + per-day request budget.

The budget cap is enforced per-user via ``AiUsageEvent`` row counts for the
current calendar date.  The gate is intentionally loose (keyword match) —
it filters out obvious off-topic prompts before they reach the model.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import AiUsageEvent, User
from app.time_utils import now_utc

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


async def can_use_ai_today(db: AsyncSession, user: User) -> tuple[bool, int]:
    today = date.today()
    used_today = (
        await db.scalar(
            select(func.count(AiUsageEvent.id))
            .where(AiUsageEvent.user_id == user.id)
            .where(func.date(AiUsageEvent.created_at) == today)
        )
        or 0
    )
    return used_today < settings.ai_daily_request_limit, used_today


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
