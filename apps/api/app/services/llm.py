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
from app.services.ai_metrics import record_outcome, record_usage

log = structlog.get_logger(__name__)

# The system prompt is a stable string — keep it module-level so the cached
# prefix on Anthropic's side hashes consistently across requests. Any
# interpolation (timestamps, user IDs) would invalidate the cache; we
# deliberately push dynamic context into ``messages`` instead.
_SYSTEM_PROMPT_RU = (
    "Ты — ассистент по поиску работы на сервисе Proshli. "
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


@dataclass(slots=True)
class ResumeImprovement:
    """Structured response from :meth:`LLMService.improve_resume`.

    ``summary`` is the rewritten 1–2 sentence pitch; ``suggestions`` is a
    short list of concrete actionable rewrites (≤ 5 items). The route
    layer wraps this into :class:`app.schemas.ResumeImproveResponse` and
    adds usage telemetry.
    """

    summary: str
    suggestions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CoverLetter:
    """Single-shot cover letter draft.

    ``body`` is the full text (3–5 short paragraphs, plain prose, no
    salutation/sign-off — the FE adds those around the body so the
    seeker can replace the addressee without rerunning the model).
    """

    body: str


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

    async def improve_resume(
        self, *, content: dict[str, Any], target_role: str, focus: str
    ) -> ResumeImprovement:
        """Produce a tightened summary + suggestion list for a resume version.

        ``content`` is the seeker's ``ResumeVersion.content`` blob (free-form
        JSON — typically ``{"summary": ..., "experience": [...], "skills":
        [...]}``). ``target_role`` is the role they're tailoring for; ``focus``
        is a free-form hint (e.g. "сделай акцент на ML"). Implementations
        must never raise — fall back to a scripted answer if the model
        errors so the route layer can surface a clean response.
        """
        ...

    async def cover_letter(
        self,
        *,
        seeker: dict[str, Any],
        vacancy: dict[str, Any],
        tone: str,
        language: str,
    ) -> CoverLetter:
        """Draft a tailored cover letter for a vacancy.

        ``seeker`` is a compact dict of the seeker's profile + most recent
        resume (``full_name``, ``target_role``, ``skills``, ``about``,
        ``resume_text``). ``vacancy`` carries the role's ``title``,
        ``company``, ``location``, and ``description``. ``tone`` is
        ``"formal"`` or ``"friendly"``; ``language`` is ``"ru"`` or
        ``"en"``. Implementations must never raise — return a sensible
        scripted fallback so the route layer can always reply.
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

    async def improve_resume(
        self, *, content: dict[str, Any], target_role: str, focus: str
    ) -> ResumeImprovement:
        """Deterministic fallback resume coach.

        We don't have a real model — but we can still emit *useful* advice
        by inspecting the structure of ``content`` and pointing out common
        gaps. Keeps the endpoint behaviour-equivalent in CI / offline dev
        without forcing every contributor to provision an Anthropic key.
        """
        suggestions: list[str] = []
        skills = content.get("skills") if isinstance(content, dict) else None
        if not skills or (isinstance(skills, list) and len(skills) < 3):
            suggestions.append(
                "Добавь раздел skills с 5–10 ключевыми технологиями — рекрутеры сканируют его в первую очередь."
            )
        experience = content.get("experience") if isinstance(content, dict) else None
        if not experience:
            suggestions.append(
                "Опиши 2–3 последних проекта в формате «что сделал → какой эффект» — это сильно повышает отклик."
            )
        summary_field = content.get("summary") if isinstance(content, dict) else None
        if not isinstance(summary_field, str) or len(summary_field.strip()) < 40:
            suggestions.append(
                "Напиши короткий summary (1–2 предложения) — позиционирование + ключевая компетенция."
            )
        if focus.strip():
            suggestions.append(
                f"Сделай явный акцент на: {focus.strip()} — выноси это в summary и первый bullet опыта."
            )
        if not suggestions:
            suggestions.append(
                "Резюме выглядит цельно — отполируй формулировки в bullet-ах: глагол действия + измеримый результат."
            )

        role_phrase = target_role.strip() or "выбранную роль"
        summary = (
            f"Опытный кандидат на {role_phrase}: фокус на результат, "
            "ключевые технологии и поддающиеся проверке достижения."
        )
        return ResumeImprovement(summary=summary, suggestions=suggestions[:5])

    async def cover_letter(
        self,
        *,
        seeker: dict[str, Any],
        vacancy: dict[str, Any],
        tone: str,
        language: str,
    ) -> CoverLetter:
        """Scripted fallback. Composes a plausible 3-paragraph letter using
        what's known about the seeker and the role. No model — but it's
        coherent enough that the UI is testable without an API key.
        """
        target = str(seeker.get("target_role") or vacancy.get("title") or "")
        company = str(vacancy.get("company") or "вашей компании")
        title = str(vacancy.get("title") or target or "позицию")
        skills_raw = seeker.get("skills")
        if isinstance(skills_raw, list):
            skills = ", ".join(str(s) for s in skills_raw[:5] if s)
        else:
            skills = ""
        about = str(seeker.get("about") or "").strip()

        if language == "en":
            opener = (
                f"I'm writing to express interest in the {title} role at {company}."
            )
            mid = (
                f"My background centers on {skills}. {about}"
                if skills or about
                else "My background includes hands-on work on similar problems."
            )
            close = (
                "I'd welcome the chance to discuss how my experience could fit."
                if tone == "formal"
                else "Happy to chat anytime — let me know what works."
            )
        else:
            opener = (
                f"Пишу вам с интересом к позиции «{title}» в {company}."
            )
            mid = (
                f"Мой опыт связан с {skills}. {about}".strip()
                if skills or about
                else "За плечами — опыт на похожих задачах и измеримые результаты."
            )
            close = (
                "Буду рад обсудить, как мой опыт может усилить команду."
                if tone == "formal"
                else "Готов созвониться в удобное время — дайте знать."
            )
        body = f"{opener}\n\n{mid}\n\n{close}"
        return CoverLetter(body=body)


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
            record_usage("chat", usage)
            record_outcome("chat", "success")
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
            record_outcome("chat", "error")
            yield "content", "Сейчас не удаётся достучаться до модели. Попробуй ещё раз через минуту."

    async def improve_resume(
        self, *, content: dict[str, Any], target_role: str, focus: str
    ) -> ResumeImprovement:
        """Call Claude to produce a structured resume improvement.

        We use tool-use with a single required tool (``emit_resume_improvement``)
        so the model returns JSON that matches :class:`ResumeImprovement`'s
        shape directly — no fragile prose parsing. If anything goes wrong
        we fall back to :class:`RuleBasedLLMService.improve_resume` so the
        endpoint stays usable.
        """
        from anthropic import AsyncAnthropic  # noqa: F401  # ensure import path exists

        resume_blob = json.dumps(content, ensure_ascii=False)
        role_hint = target_role.strip() or "не указана"
        focus_hint = focus.strip() or "—"

        system_prompt = (
            "Ты — карьерный консультант сервиса Proshli. По JSON-резюме и "
            "целевой роли формируешь: (1) summary в 1–2 предложения на русском, "
            "(2) 3–5 конкретных рекомендаций по улучшению. Каждая рекомендация — "
            "≤ 1 предложения, в форме «что сделать» (повелительное наклонение). "
            "Не упоминай отсутствующие факты, не сочиняй опыт. Всегда вызывай "
            "инструмент emit_resume_improvement."
        )
        tool: dict[str, Any] = {
            "name": "emit_resume_improvement",
            "description": (
                "Возвращает улучшенное summary и список конкретных рекомендаций "
                "по правке резюме."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "1–2 предложения, русский. Без воды.",
                    },
                    "suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 5,
                        "description": "3–5 конкретных рекомендаций.",
                    },
                },
                "required": ["summary", "suggestions"],
            },
        }
        user_message = (
            f"Целевая роль: {role_hint}\n"
            f"Дополнительный фокус: {focus_hint}\n\n"
            f"JSON-резюме:\n{resume_blob}"
        )

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=cast(
                    Any,
                    [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                ),
                tools=cast(Any, [tool]),
                tool_choice=cast(Any, {"type": "tool", "name": "emit_resume_improvement"}),
                messages=cast(Any, [{"role": "user", "content": user_message}]),
            )
            record_usage("improve_resume", getattr(response, "usage", None))
        except Exception as exc:  # pragma: no cover — network / quota faults
            log.warning("llm.improve_resume_failed", error=str(exc))
            record_outcome("improve_resume", "error")
            return await RuleBasedLLMService().improve_resume(
                content=content, target_role=target_role, focus=focus
            )

        summary = ""
        suggestions: list[str] = []
        for block in getattr(response, "content", []):
            if getattr(block, "type", "") == "tool_use":
                raw_input = getattr(block, "input", {}) or {}
                if isinstance(raw_input, str):
                    try:
                        raw_input = json.loads(raw_input)
                    except json.JSONDecodeError:
                        raw_input = {}
                if isinstance(raw_input, dict):
                    s = raw_input.get("summary")
                    if isinstance(s, str):
                        summary = s.strip()
                    items = raw_input.get("suggestions")
                    if isinstance(items, list):
                        suggestions = [
                            str(item).strip()
                            for item in items
                            if isinstance(item, str) and item.strip()
                        ][:5]
                break

        if not summary or not suggestions:
            # Fell through without a usable tool call — defer to the rule-based
            # backend rather than emit a blank response.
            log.warning(
                "llm.improve_resume_empty_tool_call",
                summary_len=len(summary),
                suggestion_count=len(suggestions),
            )
            record_outcome("improve_resume", "error")
            return await RuleBasedLLMService().improve_resume(
                content=content, target_role=target_role, focus=focus
            )

        record_outcome("improve_resume", "success")
        return ResumeImprovement(summary=summary, suggestions=suggestions)

    async def cover_letter(
        self,
        *,
        seeker: dict[str, Any],
        vacancy: dict[str, Any],
        tone: str,
        language: str,
    ) -> CoverLetter:
        """Generate a tailored cover letter via tool-use.

        We force a single ``emit_cover_letter`` tool call so the model
        returns plain text in a predictable shape (no prose-around-JSON
        parsing). Fallback to the rule-based draft on any error keeps
        the endpoint usable.
        """
        seeker_blob = json.dumps(seeker, ensure_ascii=False)
        vacancy_blob = json.dumps(vacancy, ensure_ascii=False)
        lang_label = "русском" if language == "ru" else "английском"
        tone_label = (
            "официальный, деловой"
            if tone == "formal"
            else "дружелюбный, разговорный, но профессиональный"
        )

        system_prompt = (
            "Ты — карьерный консультант сервиса Proshli. По данным кандидата и "
            "вакансии составляешь короткое сопроводительное письмо: 3 абзаца "
            f"на {lang_label} языке, тон — {tone_label}. Без приветствия и "
            "подписи (их добавит интерфейс). Не выдумывай факты: опирайся "
            "только на то, что есть в данных кандидата. Всегда вызывай "
            "инструмент emit_cover_letter."
        )
        tool: dict[str, Any] = {
            "name": "emit_cover_letter",
            "description": "Возвращает текст сопроводительного письма.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "body": {
                        "type": "string",
                        "description": (
                            "Текст письма (3 абзаца, разделённые двойным "
                            "переносом строки). Без приветствия/подписи."
                        ),
                    },
                },
                "required": ["body"],
            },
        }
        user_message = (
            f"Кандидат:\n{seeker_blob}\n\nВакансия:\n{vacancy_blob}"
        )

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=cast(
                    Any,
                    [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                ),
                tools=cast(Any, [tool]),
                tool_choice=cast(Any, {"type": "tool", "name": "emit_cover_letter"}),
                messages=cast(Any, [{"role": "user", "content": user_message}]),
            )
            record_usage("cover_letter", getattr(response, "usage", None))
        except Exception as exc:  # pragma: no cover — network / quota faults
            log.warning("llm.cover_letter_failed", error=str(exc))
            record_outcome("cover_letter", "error")
            return await RuleBasedLLMService().cover_letter(
                seeker=seeker, vacancy=vacancy, tone=tone, language=language
            )

        body = ""
        for block in getattr(response, "content", []):
            if getattr(block, "type", "") == "tool_use":
                raw_input = getattr(block, "input", {}) or {}
                if isinstance(raw_input, str):
                    try:
                        raw_input = json.loads(raw_input)
                    except json.JSONDecodeError:
                        raw_input = {}
                if isinstance(raw_input, dict):
                    value = raw_input.get("body")
                    if isinstance(value, str):
                        body = value.strip()
                break

        if not body:
            log.warning("llm.cover_letter_empty_tool_call")
            record_outcome("cover_letter", "error")
            return await RuleBasedLLMService().cover_letter(
                seeker=seeker, vacancy=vacancy, tone=tone, language=language
            )

        record_outcome("cover_letter", "success")
        return CoverLetter(body=body)


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
