"""AI chat guardrail + streaming endpoint.

The legacy ``POST /ai/chat`` returns a single JSON envelope and stays for
backward-compatibility with existing FE code and tests. Wave 11 added
``POST /ai/chat/stream`` — a Server-Sent Events surface that emits typed
``data-*`` chunks the FE can render incrementally. Wave 3 wires the streaming
path through a real LLM (Anthropic Claude) and makes filters arrive *from*
the model via tool use, rather than from a keyword-only extractor.

Stream event shape (one JSON object per SSE ``data:`` line, plus the SSE
event name for routing on the client):

* ``data-status``      → ``{"phase": "gating"|"extracting"|"composing"|"done", "message": str}``
* ``data-filter``      → ``{"key": str, "value": str}``   (one per filter)
* ``data-content``     → ``{"text": str}``                 (assistant reply tokens)
* ``data-suggestion``  → ``{"text": str}``                 (search-query hints)
* ``data-error``       → ``{"code": str, "message": str}``
* ``data-usage``       → ``{"used_today": int, "limit": int}``

The connection ends with a terminal SSE ``event: data-done`` frame so the
client knows to close the EventSource (browsers auto-reconnect on raw EOF).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.auth import get_current_user
from app.config import settings
from app.deps import DbSession
from app.middleware.rate_limit import RateLimit
from app.models import User
from app.schemas import AiChatRequest, AiChatResponse
from app.services.ai_guardrails import (
    can_use_ai_today,
    extract_basic_filters,
    is_career_related,
    store_ai_usage,
)
from app.services.llm import LLMService, get_llm_service

router = APIRouter(prefix="/ai", tags=["ai"])
log = structlog.get_logger(__name__)


# Search-query suggestions keyed off extracted stack — keeps the demo
# feeling alive. The LLM also produces a natural-language reply via
# ``data-content``; these hints are complementary chips, not a substitute.
_SUGGESTIONS_BY_STACK: dict[str, list[str]] = {
    "python": [
        "FastAPI · Django · asyncio",
        "Senior Python с релокацией",
        "Python + ML",
    ],
    "javascript": ["React + TS", "Node.js backend", "Full-stack JS"],
    "typescript": ["Next.js 16", "React 19 + TS", "Backend на TS (NestJS)"],
    "go": ["Go + Kubernetes", "Backend на Go", "Senior Go в финтехе"],
    "java": ["Java + Spring", "Kotlin/Android", "Senior Java"],
    "kotlin": ["Kotlin/Android", "Backend на Kotlin", "Server-side Kotlin"],
    "c#": [".NET 8 backend", "Unity-разработчик", "Senior C#"],
}


def _sse(event: str, payload: dict[str, Any]) -> bytes:
    """Encode a single Server-Sent Event frame.

    Each frame is ``event: <name>\\ndata: <json>\\n\\n``. Newlines inside
    the JSON are safe — we use ``json.dumps`` which escapes them.
    """
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {body}\n\n".encode()


# ---------------------------------------------------------------------------
# Legacy non-streaming endpoint (kept for FE compatibility and tests)
# ---------------------------------------------------------------------------


@router.post(
    "/chat",
    response_model=AiChatResponse,
    dependencies=[
        Depends(RateLimit("ai-chat", limit=20, window_seconds=60)),
    ],
)
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

    allowed, used_today, limit = await can_use_ai_today(db, current_user)
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
            f"Запрос принят. Использовано сегодня: {used_today + 1}/{limit}. "
            "Фильтры извлечены."
        ),
        extracted_filters=extracted_filters,
    )


# ---------------------------------------------------------------------------
# Streaming endpoint (Wave 11; Wave 3 wires real LLM in)
# ---------------------------------------------------------------------------


async def _stream_chat(
    db: DbSession,
    user: User,
    message: str,
    llm: LLMService,
) -> AsyncIterator[bytes]:
    """Yield SSE frames for a single chat turn.

    We commit to the contract of "always emit ``data-done`` last, even on
    error" so the EventSource on the client doesn't have to handle EOF
    differently from a clean shutdown. ``llm`` is injected so tests can swap
    in a deterministic fake without monkey-patching module globals.
    """

    # 1) Input length gate — emit a typed error and close.
    if len(message) > settings.ai_max_input_chars:
        yield _sse(
            "data-error",
            {"code": "input_too_long", "message": "Сообщение слишком длинное."},
        )
        yield _sse("data-done", {})
        return

    # 2) Career-keyword gate.
    yield _sse("data-status", {"phase": "gating", "message": "Проверяю запрос…"})
    # tiny pause so the FE actually paints the status; the cost is negligible.
    await asyncio.sleep(0.05)
    if not is_career_related(message):
        yield _sse(
            "data-error",
            {
                "code": "off_topic",
                "message": (
                    "Я помогаю только по вопросам работы, вакансий, резюме и карьеры."
                ),
            },
        )
        yield _sse("data-done", {})
        return

    # 3) Per-day budget — now tier-aware (free=5, pro=50, employer=100 by default).
    allowed, used_today, limit = await can_use_ai_today(db, user)
    if not allowed:
        yield _sse(
            "data-error",
            {
                "code": "daily_limit_reached",
                "message": (
                    f"Достигнут дневной лимит AI-запросов ({limit}). "
                    "Попробуй позже или оформи подписку."
                ),
            },
        )
        yield _sse(
            "data-usage",
            {"used_today": used_today, "limit": limit},
        )
        yield _sse("data-done", {})
        return

    # 4) Hand off to the LLM service — it streams ``filter`` and ``content``
    #    tuples. We mirror them onto the SSE surface so the FE can render
    #    filter chips and the assistant reply in parallel.
    yield _sse(
        "data-status",
        {"phase": "extracting", "message": "Извлекаю фильтры…"},
    )

    extracted_keys: set[str] = set()
    saw_content = False
    try:
        async for kind, payload in llm.stream_chat(message):
            if kind == "filter":
                key = str(payload.get("key", ""))
                value = str(payload.get("value", ""))
                if key and value:
                    extracted_keys.add(key)
                    yield _sse("data-filter", {"key": key, "value": value})
            elif kind == "content":
                if not saw_content:
                    yield _sse(
                        "data-status",
                        {"phase": "composing", "message": "Готовлю ответ…"},
                    )
                    saw_content = True
                # ``payload`` is a plain str chunk from the LLM stream.
                yield _sse("data-content", {"text": str(payload)})
            elif kind == "usage":
                # Reserved for cost telemetry; we don't surface model usage
                # over the wire (could leak pricing internals) but logging
                # here keeps cost-per-turn observable in dev.
                log.info(
                    "ai_chat.llm_usage",
                    user_id=user.id,
                    backend=llm.name,
                    **payload,
                )
    except Exception as exc:  # pragma: no cover — defensive: LLM service handles its own errors
        log.warning("ai_chat.llm_unexpected_error", error=str(exc))
        yield _sse(
            "data-error",
            {"code": "llm_error", "message": "Ошибка модели. Попробуй ещё раз."},
        )

    # 5) Suggestions — small static set, complementary to the LLM reply.
    stack_value: str | None = None
    if "stack" in extracted_keys:
        # Re-parse via the legacy extractor to know which stack we surfaced;
        # we don't keep the raw values in the route, only the keys. This is
        # cheap and avoids stashing per-turn state on the request.
        local = extract_basic_filters(message)
        stack_value = local.get("stack")
    if stack_value and stack_value in _SUGGESTIONS_BY_STACK:
        for hint in _SUGGESTIONS_BY_STACK[stack_value]:
            yield _sse("data-suggestion", {"text": hint})
            await asyncio.sleep(0.02)

    # 6) Record usage and emit a final status + usage frame.
    try:
        await store_ai_usage(db, user, prompt_chars=len(message))
    except Exception as exc:  # pragma: no cover — DB outage is rare
        log.warning("ai_chat.store_usage_failed", error=str(exc))
        yield _sse(
            "data-error",
            {
                "code": "usage_log_failed",
                "message": "Запрос обработан, но журнал использования недоступен.",
            },
        )

    yield _sse(
        "data-usage",
        {"used_today": used_today + 1, "limit": limit},
    )
    yield _sse(
        "data-status",
        {
            "phase": "done",
            "message": "Готово. Фильтры применены к поиску.",
        },
    )
    yield _sse("data-done", {})


@router.post(
    "/chat/stream",
    dependencies=[
        Depends(RateLimit("ai-chat-stream", limit=10, window_seconds=60)),
    ],
)
async def ai_chat_stream(
    payload: AiChatRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream the AI gate decision + LLM-driven filters + assistant reply over SSE."""
    llm = get_llm_service()
    return StreamingResponse(
        _stream_chat(db, current_user, payload.message, llm),
        media_type="text/event-stream",
        headers={
            # Disable proxy buffering — important for Nginx / Cloudflare which
            # otherwise wait for the full response before forwarding.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
