"""AI chat guardrail endpoint.

This is a *gate*, not the chat itself — the heavy LLM call lands in a later
sprint.  Today the endpoint enforces the keyword filter + the per-day budget
and returns extracted basic filters that the FE can wire into the search.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.config import settings
from app.deps import DbSession
from app.models import User
from app.schemas import AiChatRequest, AiChatResponse
from app.services.ai_guardrails import (
    can_use_ai_today,
    extract_basic_filters,
    is_career_related,
    store_ai_usage,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=AiChatResponse)
async def ai_chat(
    payload: AiChatRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> AiChatResponse:
    if len(payload.message) > settings.ai_max_input_chars:
        raise HTTPException(status_code=400, detail="Message is too long")

    if not is_career_related(payload.message):
        return AiChatResponse(
            accepted=False,
            message="Я помогаю только по вопросам работы, вакансий, резюме и карьеры.",
            extracted_filters=None,
        )

    allowed, used_today = await can_use_ai_today(db, current_user)
    if not allowed:
        return AiChatResponse(
            accepted=False,
            message=(
                "Достигнут дневной лимит AI-запросов. "
                "Попробуйте позже или уточните фильтры в ручном режиме."
            ),
            extracted_filters=None,
        )

    extracted_filters = extract_basic_filters(payload.message)
    await store_ai_usage(db, current_user, prompt_chars=len(payload.message))
    return AiChatResponse(
        accepted=True,
        message=(
            f"Запрос принят. Использовано сегодня: {used_today + 1}/"
            f"{settings.ai_daily_request_limit}. Фильтры извлечены."
        ),
        extracted_filters=extracted_filters,
    )
