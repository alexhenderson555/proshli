"""Vacancy AI-summary generator — 1-2 sentence Claude-rendered blurb.

The TG-post template has three lines: title/company, salary/location,
then a short summary that's supposed to give the reader the *gist* of
the vacancy without reading the full description. The deterministic
"first sentence" fallback in :mod:`app.services.tg_publication` is too
literal — it tends to copy a generic opener like "Команда X ищет
сильного инженера" instead of summarising what makes the role
interesting.

This service runs a Claude tool_use call that takes the
title + description + salary range and emits a tightened 1-2 sentence
summary in Russian. The result is cached on ``vacancy.ai_summary`` +
``summary_generated_at`` so a re-publish never pays the LLM cost twice
— same caching pattern as the skill extractor.

Behaviour mirrors :class:`SkillExtractor`:

* No ``ANTHROPIC_API_KEY`` → short-circuits to the first-sentence
  fallback (caller's responsibility — we just return ``""`` and let
  the caller's ``_default_summary`` kick in).
* SDK import failure → same short-circuit.
* LLM exception → log + empty string. Never raises.

The tool schema constrains output to a single short string so we don't
have to parse free-form prose.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

import structlog
from app.config import settings
from app.models import Vacancy
from app.services.ai_metrics import record_outcome, record_usage
from app.time_utils import now_utc

log = structlog.get_logger(__name__)


_TOOL_SCHEMA: dict[str, Any] = {
    "name": "emit_summary",
    "description": (
        "Generate a tight 1-2 sentence Russian summary of an IT vacancy "
        "suitable for a Telegram post. Focus on what makes the role "
        "concrete: stack, team scope, product. Avoid filler ('ищем "
        "сильного инженера'), avoid quoting salary (it's shown elsewhere "
        "in the post), avoid bullet points."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": (
                    "Russian, 1-2 sentences, ≤ 200 chars. No emoji, no markdown, no salary numbers."
                ),
                "maxLength": 240,
            }
        },
        "required": ["summary"],
    },
}

_LLM_SYSTEM = (
    "Ты — редактор Telegram-канала вакансий Proshli. По описанию "
    "вакансии формируешь 1-2 коротких предложения, которые сжимают "
    "суть позиции: продукт, команда, ключевой стек. Не цитируешь "
    "зарплату, не используешь маркетинговые штампы ('ищем сильного'), "
    "не пишешь bullet-листы. Всегда вызываешь инструмент emit_summary."
)


@dataclass(frozen=True, slots=True)
class SummaryResult:
    """One run's output. ``ok`` is False when LLM didn't run or returned empty."""

    text: str
    ok: bool


class VacancySummaryGenerator:
    """Production entry point — Claude tool_use with caching contract.

    Stateless aside from the lazily-built Anthropic client. Same
    ``api_key=""`` short-circuit pattern as :class:`SkillExtractor`.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int = 300,
    ) -> None:
        # Fall back to settings when caller doesn't override. Production
        # construction is parameter-less (``VacancySummaryGenerator()``)
        # so the settings-injected defaults reach the SDK. Tests still
        # pass an empty string to force the short-circuit path.
        self._api_key = settings.anthropic_api_key if api_key is None else api_key
        self._model = settings.anthropic_model if model is None else model
        self._max_tokens = max_tokens
        self._client: Any | None = None

    def _ensure_client(self) -> Any | None:
        if not self._api_key:
            return None
        if self._client is not None:
            return self._client
        try:
            from anthropic import AsyncAnthropic
        except ImportError:  # pragma: no cover
            log.warning("vacancy_summary.anthropic_sdk_missing")
            return None
        self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def generate(self, *, vacancy: Vacancy) -> SummaryResult:
        """Generate a summary; never raises.

        Returns ``SummaryResult(ok=False, text="")`` when the LLM path
        isn't available — callers fall through to their deterministic
        fallback in that case.
        """
        client = self._ensure_client()
        if client is None:
            return SummaryResult(text="", ok=False)

        try:
            text = await self._llm_summarise(client, vacancy)
        except Exception as exc:  # noqa: BLE001 - intentional: never raise
            log.warning("vacancy_summary.llm_failed", error=str(exc))
            record_outcome("vacancy_summary", "error")
            return SummaryResult(text="", ok=False)

        if not text:
            record_outcome("vacancy_summary", "error")
            return SummaryResult(text="", ok=False)
        record_outcome("vacancy_summary", "success")
        return SummaryResult(text=text, ok=True)

    async def _llm_summarise(self, client: Any, vacancy: Vacancy) -> str:
        title = (vacancy.title or "").strip()
        company = (vacancy.company or "").strip()
        # Cap description: Claude doesn't need the whole novel to write
        # a 2-sentence summary, and the prompt cache is friendlier when
        # the user message stays small.
        description = (vacancy.description or "").strip()[:3000]

        user_message = (
            f"Компания: {company or '—'}\nДолжность: {title or '—'}\n\nОписание:\n{description}"
        )

        response = await client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=cast(
                Any,
                [
                    {
                        "type": "text",
                        "text": _LLM_SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            ),
            tools=cast(Any, [_TOOL_SCHEMA]),
            tool_choice=cast(Any, {"type": "tool", "name": "emit_summary"}),
            messages=cast(Any, [{"role": "user", "content": user_message}]),
        )
        record_usage("vacancy_summary", getattr(response, "usage", None))

        for block in getattr(response, "content", []):
            if getattr(block, "type", "") == "tool_use":
                raw = getattr(block, "input", {}) or {}
                if isinstance(raw, str):
                    try:
                        raw = json.loads(raw)
                    except json.JSONDecodeError:
                        return ""
                if isinstance(raw, dict):
                    summary = raw.get("summary")
                    if isinstance(summary, str):
                        return summary.strip()
        return ""


_generator_singleton: VacancySummaryGenerator | None = None


def get_summary_generator() -> VacancySummaryGenerator:
    """Process-wide cached generator instance."""
    global _generator_singleton
    if _generator_singleton is None:
        _generator_singleton = VacancySummaryGenerator(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=300,
        )
    return _generator_singleton


async def summarise_and_cache(vacancy: Vacancy) -> str:
    """High-level helper: returns the cached summary or generates + caches.

    Wires the generator into the Vacancy model: if ``ai_summary`` is
    already populated, returns it untouched. Otherwise runs the LLM
    path and writes ``ai_summary`` + ``summary_generated_at`` on the
    SQLAlchemy object. The caller is responsible for committing.

    Returns the summary text (possibly empty if the LLM path wasn't
    available — caller falls through to their deterministic fallback).
    """
    if vacancy.ai_summary:
        return vacancy.ai_summary

    result = await get_summary_generator().generate(vacancy=vacancy)
    if result.ok:
        vacancy.ai_summary = result.text
        vacancy.summary_generated_at = now_utc()
        return result.text
    return ""
