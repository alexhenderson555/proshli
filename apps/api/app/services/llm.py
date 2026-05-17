"""Anthropic Claude integration for the conversational job-search assistant.

Wave 3 replaces the rule-based extractor with a real LLM call. Two services
are exposed via the :class:`LLMService` protocol so the rest of the codebase
doesn't have to care which is active:

* :class:`AnthropicLLMService` — wraps ``anthropic.AsyncAnthropic``. Uses tool
  use for filter extraction (so the model emits *structured* output we can
  trust) and streams the assistant reply token-by-token via ``messages.stream``.
  System prompt is cached (``cache_control={"type": "ephemeral"}``) so the
  per-turn cost stays predictable.

* :class:`RuleBasedLLMService` — fallback used when ``settings.anthropic_api_key``
  is empty. It defers filter extraction to the legacy keyword path from
  ``ai_guardrails`` and synthesises a short scripted reply. Keeps local dev
  unbroken without forcing every contributor to provision a key.

The selector in :func:`get_llm_service` is cached for the process lifetime; it
runs once at first import and is cheap to call from request handlers.

The Anthropic SDK is imported lazily so the rule-based path stays usable even
in environments where ``anthropic`` isn't installed (e.g. light CI images).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol, cast

import structlog
from app.config import settings
from app.services.ai_guardrails import extract_basic_filters

log = structlog.get_logger(__name__)

# The system prompt is a stable string — keep it module-level so the cached
# prefix on Anthropic's side hashes consistently across requests. Any
# interpolation (timestamps, user IDs) would invalidate the cache; we
# deliberately push dynamic context into ``messages`` instead.
_SYSTEM_PROMPT_RU = (
    "Ты — ассистент по поиску работы на сервисе Otklik.ai. "
    "Помогаешь пользователям формулировать запросы к базе вакансий: "
    "уточняешь стек, грейд, формат работы (удалёнка/офис/гибрид), город. "
    "Отвечай кратко (1–3 предложения) и только по вопросам, связанным с "
    "карьерой, вакансиями, резюме, собеседованиями и оплатой труда. "
    "Если запрос off-topic — вежливо откажи. "
    "Всегда вызывай инструмент extract_job_filters, чтобы зафиксировать "
    "извлечённые фильтры структурированно."
)

# Tool-use schema. The model emits one call per turn — we parse the input
# into the same ``dict[str, str]`` shape the legacy extractor produced so
# downstream consumers (search filter chips, SSE `data-filter` frames) don't
# have to branch on which extractor was used.
_EXTRACT_FILTERS_TOOL: dict[str, Any] = {
    "name": "extract_job_filters",
    "description": (
        "Извлекает структурированные фильтры из запроса пользователя по "
        "поиску работы. Заполняй только те поля, которые явно упомянуты — "
        "остальные оставляй пустыми."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "stack": {
                "type": "string",
                "description": (
                    "Технологический стек: python, javascript, typescript, "
                    "go, java, kotlin, c#, или пусто."
                ),
            },
            "level": {
                "type": "string",
                "enum": ["junior", "middle", "senior", ""],
                "description": "Грейд позиции; пустая строка если не указан.",
            },
            "work_mode": {
                "type": "string",
                "enum": ["remote", "office", "hybrid", ""],
                "description": "Формат работы; пустая строка если не указан.",
            },
            "city": {
                "type": "string",
                "description": "Город (на русском или английском); пусто если не указан.",
            },
        },
        "required": ["stack", "level", "work_mode", "city"],
    },
}


@dataclass(slots=True)
class LLMResult:
    """Aggregated result of a single chat turn.

    ``filters`` is what we surface to the search index; ``text_chunks`` is the
    list of streamed text fragments (already emitted to the client via SSE).
    ``raw_input_tokens`` / ``raw_output_tokens`` are populated when the
    Anthropic path is taken — the rule-based path leaves them at zero.
    """

    filters: dict[str, str] = field(default_factory=dict)
    text_chunks: list[str] = field(default_factory=list)
    raw_input_tokens: int = 0
    raw_output_tokens: int = 0


class LLMService(Protocol):
    """Protocol implemented by both the real and fallback services.

    ``stream_chat`` is intentionally a *plain* ``def`` returning an
    ``AsyncIterator``, not ``async def`` — both implementations are async
    generator functions (use ``yield``), and calling them returns the
    iterator synchronously (no ``await``). Typing it as ``async def`` would
    say "this returns a coroutine that resolves to an iterator", which is
    the Anthropic-SDK shape, not ours. mypy with strict settings flags the
    mismatch.
    """

    name: str

    def stream_chat(self, message: str) -> AsyncIterator[tuple[str, Any]]:
        """Yield ``(event_kind, payload)`` tuples.

        ``event_kind`` ∈ {``"filter"``, ``"content"``, ``"usage"``}.

        * ``"filter"`` — payload is ``{"key": str, "value": str}`` for a
          single extracted filter (route emits as ``data-filter``).
        * ``"content"`` — payload is a str text chunk (route emits as
          ``data-content``).
        * ``"usage"`` — payload is ``{"input_tokens": int, "output_tokens": int}``
          (route uses this for cost telemetry; not currently emitted on the
          wire).
        """
        ...


class RuleBasedLLMService:
    """Deterministic fallback so dev without an API key still works.

    Filter extraction goes through the same keyword path the legacy
    ``/ai/chat`` endpoint used; the "assistant reply" is a short scripted
    Russian acknowledgement that mentions the picked-up filters. Yields a few
    text chunks to keep the SSE shape symmetric with the Anthropic path —
    the FE renders them identically.
    """

    name = "rule_based"

    async def stream_chat(self, message: str) -> AsyncIterator[tuple[str, Any]]:
        filters = extract_basic_filters(message)
        for key, value in filters.items():
            yield "filter", {"key": key, "value": value}

        # Compose a short canned reply. Doing it in two chunks gives the FE
        # something to render incrementally — the chunk boundaries don't
        # matter, they're an artifact of streaming UX.
        if filters:
            picked = ", ".join(f"{k}={v}" for k, v in filters.items())
            yield "content", "Фильтры распознаны: "
            yield "content", f"{picked}. Применяю их к поиску."
        else:
            yield "content", "Не удалось извлечь явные фильтры — "
            yield "content", "уточни стек, грейд или формат работы."

        yield "usage", {"input_tokens": 0, "output_tokens": 0}


class AnthropicLLMService:
    """Real LLM path. Uses tool-use for filters + streaming for the reply.

    Construction is cheap — the async client is lazy and lives for the
    process lifetime via :func:`get_llm_service`. We don't bother with
    connection-pool tuning; the SDK's defaults are fine for our QPS.
    """

    name = "anthropic"

    def __init__(self, *, api_key: str, model: str, max_tokens: int) -> None:
        # Lazy import so environments without ``anthropic`` installed can
        # still load the module (the selector picks the fallback instead).
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def stream_chat(self, message: str) -> AsyncIterator[tuple[str, Any]]:
        # System prompt carries a ``cache_control`` breakpoint — the entire
        # system block sits before any volatile content, so caching it gives
        # us a ~10× discount on the prefix on every subsequent turn. The
        # tool definition renders before system, so the cache marker also
        # covers it as a side effect.
        system_blocks = [
            {
                "type": "text",
                "text": _SYSTEM_PROMPT_RU,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": message},
        ]

        # The Anthropic SDK's stream() signature uses TypedDict shapes for
        # ``system``, ``tools``, and ``messages``. Our runtime dicts conform
        # structurally but mypy can't prove it without a verbose TypedDict
        # ladder; cast through Any for the call site. The SDK still
        # validates at runtime.
        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=self._max_tokens,
                system=cast(Any, system_blocks),
                tools=cast(Any, [_EXTRACT_FILTERS_TOOL]),
                # ``tool_choice=any`` would force a tool call every turn,
                # which is exactly what we want — every user message in this
                # endpoint is a search query, so filters should always be
                # produced even if some fields end up empty.
                tool_choice=cast(Any, {"type": "any"}),
                messages=cast(Any, messages),
            ) as stream:
                async for event in stream:
                    # The SDK yields typed events; we only care about two:
                    # text deltas (for ``data-content``) and tool-use input
                    # JSON deltas (which we accumulate and parse at end).
                    et = getattr(event, "type", "")
                    if et == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        dtype = getattr(delta, "type", "")
                        if dtype == "text_delta":
                            text = getattr(delta, "text", "")
                            if text:
                                yield "content", text
                        # input_json_delta chunks accumulate inside the
                        # stream helper; we read the final block on stop.

                final = await stream.get_final_message()

            # Walk the final content blocks for the tool_use input; this is
            # already fully assembled by the SDK so we don't have to handle
            # partial JSON ourselves.
            for block in getattr(final, "content", []):
                if getattr(block, "type", "") == "tool_use":
                    raw_input = getattr(block, "input", {}) or {}
                    # Defensive: the SDK gives us a dict, but if anyone
                    # injects a string later we still want to recover.
                    if isinstance(raw_input, str):
                        try:
                            raw_input = json.loads(raw_input)
                        except json.JSONDecodeError:
                            raw_input = {}
                    for key in ("stack", "level", "work_mode", "city"):
                        value = raw_input.get(key)
                        if isinstance(value, str) and value.strip():
                            yield "filter", {"key": key, "value": value.strip()}

            usage = getattr(final, "usage", None)
            if usage is not None:
                yield "usage", {
                    "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                    "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
                }

        except Exception as exc:  # pragma: no cover — network / quota faults
            # We log and degrade to a single scripted apology — the route
            # layer wraps this into a ``data-error`` frame plus a terminal
            # ``data-done``. Letting the exception bubble would tear down
            # the SSE generator without telling the FE why.
            log.warning("llm.anthropic_failed", error=str(exc))
            yield "content", "Сейчас не удаётся достучаться до модели. Попробуй ещё раз через минуту."


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    """Return the active LLM backend.

    Selection happens once per process. If the API key is missing we wire up
    the rule-based fallback; otherwise we instantiate the Anthropic client.
    A failed import of ``anthropic`` also falls back — keeps the API bootable
    in light CI containers where the SDK isn't installed.
    """
    if not settings.anthropic_api_key:
        log.info("llm.using_rule_based", reason="no_api_key")
        return RuleBasedLLMService()
    try:
        return AnthropicLLMService(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
        )
    except ImportError:  # pragma: no cover — exercised in stripped images
        log.warning("llm.anthropic_sdk_missing")
        return RuleBasedLLMService()
