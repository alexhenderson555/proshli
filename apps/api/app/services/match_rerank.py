"""Match-score 2.0 — LLM reranker over the cosine top-N.

The cosine match score (``app.services.match_score``) is fast and cheap
but lossy: ``voyage-3`` embeds a 1024-d summary of each side and the dot
product can't tell ``Python backend / FastAPI / AWS`` apart from
``Python data engineer / Spark / Snowflake``. That gap matters when the
seeker is comparing the *top 10* — small ordering errors translate
directly into clicks lost to weaker matches.

This module takes the cosine top-50 and re-ranks them with Claude
(``settings.match_rerank_model`` — defaults to Opus 4.6, the strong-reasoning
default per the api guidelines). For each surviving candidate we get a
``rerank_score`` in [0, 1] and a 1-2 sentence ``reasoning_ru`` that we
surface in the UI ("Why this one?"). Both are persisted in
``match_reasonings`` keyed by ``(resume_id, vacancy_id)`` so the second
visit doesn't burn another Claude call.

The service is best-effort:
* Empty ``anthropic_api_key`` → no rerank, the caller falls back to the
  cosine order. We log once and short-circuit.
* Any exception from the API → same: log, return ``[]``. The match-feed
  route handles ``[]`` by serving the cosine top-N untouched.
* TTL is ``settings.match_reasoning_ttl_days`` (default 14d) — older rows
  are treated as stale and re-evaluated. The cleanup is implicit: we only
  read rows newer than the cutoff, the stale ones are simply ignored
  (a separate housekeeping pass can prune them later if storage grows).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import MatchReasoning, Resume, Vacancy
from app.services.ai_metrics import record_outcome, record_usage

log = structlog.get_logger(__name__)


# Hard cap on the number of vacancies we hand to the model. 50 × ~500 input
# tokens per card ≈ 25K input tokens — well within Opus 4.6's 200K context.
# Pushing this higher delivers diminishing returns: cosine top-50 already
# captures the relevant set 95%+ of the time.
_MAX_CANDIDATES: int = 50

# Default ``top_n`` for callers that don't pass one. 10 fits the "match-feed"
# UI tab and the cover-letter / digest consumers downstream.
_DEFAULT_TOP_N: int = 10

# Max characters from each side we feed into the prompt. Keeps the payload
# predictable and the cache hit rate decent — the resume blob is the cached
# prefix on every request for a given user.
_RESUME_CHARS: int = 4000
_VACANCY_SUMMARY_CHARS: int = 400


_SYSTEM_PROMPT_RU = (
    "Ты — карьерный консультант сервиса Proshli. По резюме кандидата и списку "
    "вакансий ты переранжируешь вакансии по релевантности кандидату: учитываешь "
    "стек, уровень, формат работы, локацию и явные требования вакансии. Для "
    "каждой вакансии возвращаешь оценку 0..1 (rerank_score) и краткую причину "
    "(1–2 предложения на русском, без воды). Не выдумывай факты, опирайся "
    "только на текст резюме и описание вакансии. Всегда вызывай инструмент "
    "emit_rerank ровно один раз и перечисли все полученные вакансии — те, "
    "которые явно не подходят, оцени низким баллом, но не выбрасывай из ответа."
)


# Tool-use schema. We force a single ``emit_rerank`` call so the response
# is structured and predictable — no prose-around-JSON parsing.
_RERANK_TOOL: dict[str, Any] = {
    "name": "emit_rerank",
    "description": (
        "Возвращает переранжированный список вакансий с оценкой релевантности "
        "и кратким обоснованием."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "vacancy_id": {
                            "type": "integer",
                            "description": "id вакансии из входного списка.",
                        },
                        "rerank_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Оценка релевантности кандидату в диапазоне 0..1.",
                        },
                        "reasoning_ru": {
                            "type": "string",
                            "description": "1–2 предложения на русском.",
                        },
                    },
                    "required": ["vacancy_id", "rerank_score", "reasoning_ru"],
                },
            },
        },
        "required": ["items"],
    },
}


@dataclass(slots=True)
class _RerankItem:
    """Parsed tool-use output for a single vacancy."""

    vacancy_id: int
    rerank_score: float
    reasoning_ru: str


def _format_resume(resume: Resume) -> str:
    """Render a compact textual representation of the candidate.

    Skills go first (the model leans on them heavily) followed by the
    truncated raw resume. We deliberately don't include the embedding —
    Claude doesn't speak voyage-3.
    """
    skills = (resume.parsed_skills or "").strip()
    raw = (resume.raw_text or "").strip()[:_RESUME_CHARS]
    parts: list[str] = []
    if skills:
        parts.append(f"Навыки: {skills}")
    if raw:
        parts.append(f"Резюме:\n{raw}")
    return "\n\n".join(parts) if parts else "(пусто)"


def _format_vacancy(vacancy: Vacancy, cosine: float) -> dict[str, Any]:
    """Render a single candidate vacancy as a compact JSON-able dict.

    Salary is formatted as a human-readable range; ``None`` ends are
    rendered as ``"?"`` rather than dropped so the model can tell
    "open-ended salary" apart from "no salary info".
    """
    salary_from = vacancy.salary_from
    salary_to = vacancy.salary_to
    if salary_from or salary_to:
        salary = (
            f"{salary_from or '?'}–{salary_to or '?'} {vacancy.currency}"
        )
    else:
        salary = ""
    summary = (vacancy.description or "")[:_VACANCY_SUMMARY_CHARS].strip()
    return {
        "vacancy_id": vacancy.id,
        "title": vacancy.title or "",
        "company": vacancy.company or "",
        "location": vacancy.location or "",
        "salary": salary,
        "skills": (vacancy.parsed_skills or "").strip(),
        "summary": summary,
        "cosine_score": round(float(cosine), 4),
    }


async def _load_cached(
    db: AsyncSession, resume_id: int, vacancy_ids: list[int]
) -> dict[int, MatchReasoning]:
    """Fetch existing reasoning rows that are still inside the TTL window.

    Returns a ``vacancy_id → MatchReasoning`` map. Stale rows (older than
    ``settings.match_reasoning_ttl_days``) are excluded so the caller
    knows to re-evaluate them.
    """
    if not vacancy_ids:
        return {}
    cutoff = datetime.utcnow() - timedelta(days=settings.match_reasoning_ttl_days)
    rows = await db.execute(
        select(MatchReasoning).where(
            MatchReasoning.resume_id == resume_id,
            MatchReasoning.vacancy_id.in_(vacancy_ids),
            MatchReasoning.created_at >= cutoff,
        )
    )
    return {row.vacancy_id: row for row in rows.scalars()}


async def _persist_items(
    db: AsyncSession,
    *,
    resume_id: int,
    cosine_by_vid: dict[int, float],
    items: list[_RerankItem],
    model: str,
) -> dict[int, MatchReasoning]:
    """Upsert reasoning rows and return the freshly persisted entities.

    Uses Postgres ``INSERT ... ON CONFLICT (resume_id, vacancy_id) DO UPDATE``
    so concurrent reruns are safe and the ``created_at`` clock refreshes on
    every successful call (which is what the TTL relies on).
    """
    if not items:
        return {}
    now = datetime.utcnow()
    payloads = [
        {
            "resume_id": resume_id,
            "vacancy_id": item.vacancy_id,
            "rerank_score": item.rerank_score,
            "cosine_score": float(cosine_by_vid.get(item.vacancy_id, 0.0)),
            "reasoning_ru": item.reasoning_ru,
            "reasoning_en": None,
            "model": model,
            "created_at": now,
        }
        for item in items
    ]
    stmt = pg_insert(MatchReasoning).values(payloads)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_match_reasonings_resume_vacancy",
        set_={
            "rerank_score": stmt.excluded.rerank_score,
            "cosine_score": stmt.excluded.cosine_score,
            "reasoning_ru": stmt.excluded.reasoning_ru,
            "model": stmt.excluded.model,
            "created_at": stmt.excluded.created_at,
        },
    )
    await db.execute(stmt)
    await db.commit()

    # Re-read so the caller gets fully-loaded ORM rows (with ids etc.).
    vacancy_ids = [item.vacancy_id for item in items]
    rows = await db.execute(
        select(MatchReasoning).where(
            MatchReasoning.resume_id == resume_id,
            MatchReasoning.vacancy_id.in_(vacancy_ids),
        )
    )
    return {row.vacancy_id: row for row in rows.scalars()}


def _parse_tool_output(response: Any) -> list[_RerankItem]:
    """Extract ``_RerankItem``s from a Claude messages.create response.

    Defensive against partial inputs — the model occasionally swaps an
    integer for a string id or returns floats outside [0, 1]; we clamp
    and skip malformed rows so a single bad item can't blank the whole
    response.
    """
    parsed: list[_RerankItem] = []
    for block in getattr(response, "content", []):
        if getattr(block, "type", "") != "tool_use":
            continue
        raw = getattr(block, "input", {}) or {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raw = {}
        if not isinstance(raw, dict):
            continue
        items = raw.get("items")
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            try:
                vid = int(it.get("vacancy_id"))
            except (TypeError, ValueError):
                continue
            try:
                score = float(it.get("rerank_score") or 0.0)
            except (TypeError, ValueError):
                score = 0.0
            score = max(0.0, min(1.0, score))
            reasoning = it.get("reasoning_ru")
            if not isinstance(reasoning, str) or not reasoning.strip():
                continue
            parsed.append(
                _RerankItem(
                    vacancy_id=vid,
                    rerank_score=score,
                    reasoning_ru=reasoning.strip(),
                )
            )
        # Only the first tool_use block matters; bail out.
        break
    return parsed


async def rerank_top_n(
    db: AsyncSession,
    resume: Resume,
    candidates: list[tuple[Vacancy, float]],
    *,
    top_n: int = _DEFAULT_TOP_N,
) -> list[MatchReasoning]:
    """Rerank ``candidates`` and return the top ``top_n`` reasoning rows.

    ``candidates`` is the cosine top-N as ``(vacancy, cosine_score)``
    tuples — the caller is expected to feed at most ``_MAX_CANDIDATES``
    (currently 50). Excess candidates are truncated; we don't sort by
    cosine inside this function because the caller already does.

    Behaviour:

    * Empty ``candidates`` → ``[]``.
    * ``anthropic_api_key`` unset → log once and return ``[]``. Callers
      should treat this as "no rerank available" and serve the cosine
      order untouched.
    * Per-(resume, vacancy) cache: rows newer than the TTL are reused;
      stale or missing ones are re-evaluated in a single Claude call.
    * Any model / network error → log and return whatever cache we have
      (potentially ``[]``). Never raises.

    The returned list is sorted by ``rerank_score`` DESC and trimmed to
    ``top_n`` entries.
    """
    if not candidates:
        return []

    # Truncate before the cache lookup so we don't churn the DB on
    # overlong inputs from misbehaving callers.
    bounded = candidates[:_MAX_CANDIDATES]
    cosine_by_vid: dict[int, float] = {v.id: float(score) for v, score in bounded}
    vacancy_by_vid: dict[int, Vacancy] = {v.id: v for v, _ in bounded}
    vacancy_ids = list(vacancy_by_vid.keys())

    cached = await _load_cached(db, resume.id, vacancy_ids)
    to_eval = [vid for vid in vacancy_ids if vid not in cached]

    fresh: dict[int, MatchReasoning] = {}
    if to_eval:
        if not settings.anthropic_api_key:
            log.info(
                "match_rerank.skipped",
                reason="no_api_key",
                cached=len(cached),
                requested=len(to_eval),
            )
        else:
            fresh = await _call_anthropic(
                db,
                resume=resume,
                vacancies=[vacancy_by_vid[v] for v in to_eval],
                cosine_by_vid=cosine_by_vid,
            )

    combined: dict[int, MatchReasoning] = {**cached, **fresh}
    ordered = sorted(
        combined.values(),
        key=lambda r: float(r.rerank_score),
        reverse=True,
    )
    return ordered[:top_n]


async def _call_anthropic(
    db: AsyncSession,
    *,
    resume: Resume,
    vacancies: list[Vacancy],
    cosine_by_vid: dict[int, float],
) -> dict[int, MatchReasoning]:
    """Single Claude call → persisted ``MatchReasoning`` rows.

    Failures are swallowed (logged + metric recorded) so the caller can
    still serve the cached / cosine-only path. Returns the freshly
    persisted rows or ``{}`` on any error.
    """
    try:
        from anthropic import AsyncAnthropic
    except ImportError:  # pragma: no cover — exercised in stripped images
        log.warning("match_rerank.anthropic_sdk_missing")
        return {}

    resume_text = _format_resume(resume)
    candidate_blob = [_format_vacancy(v, cosine_by_vid.get(v.id, 0.0)) for v in vacancies]
    user_message = (
        f"Резюме кандидата:\n{resume_text}\n\n"
        f"Кандидатные вакансии (JSON-массив):\n{json.dumps(candidate_blob, ensure_ascii=False)}"
    )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        # ``thinking: adaptive`` lets Opus 4.6 decide how much reasoning it
        # needs — usually a couple hundred tokens for this kind of bounded
        # ranking task. ``effort: medium`` keeps the overall response terse;
        # we don't need the model to enumerate its full reasoning, just the
        # 1-2 sentence per-item justification.
        response = await client.messages.create(
            model=settings.match_rerank_model,
            max_tokens=settings.match_rerank_max_tokens,
            thinking=cast(Any, {"type": "adaptive"}),
            output_config=cast(Any, {"effort": "medium"}),
            system=cast(
                Any,
                [
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT_RU,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            ),
            tools=cast(Any, [_RERANK_TOOL]),
            tool_choice=cast(Any, {"type": "tool", "name": "emit_rerank"}),
            messages=cast(Any, [{"role": "user", "content": user_message}]),
        )
        record_usage("match_rerank", getattr(response, "usage", None))
    except TypeError:
        # Older anthropic SDK doesn't know about ``output_config`` or
        # adaptive thinking. Retry without those kwargs so dev environments
        # on an outdated pin still produce a useful result.
        try:
            response = await client.messages.create(
                model=settings.match_rerank_model,
                max_tokens=settings.match_rerank_max_tokens,
                system=cast(
                    Any,
                    [
                        {
                            "type": "text",
                            "text": _SYSTEM_PROMPT_RU,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                ),
                tools=cast(Any, [_RERANK_TOOL]),
                tool_choice=cast(Any, {"type": "tool", "name": "emit_rerank"}),
                messages=cast(Any, [{"role": "user", "content": user_message}]),
            )
            record_usage("match_rerank", getattr(response, "usage", None))
        except Exception as exc:  # pragma: no cover
            log.warning("match_rerank.fallback_failed", error=str(exc))
            record_outcome("match_rerank", "error")
            return {}
    except Exception as exc:  # pragma: no cover — network / quota faults
        log.warning("match_rerank.call_failed", error=str(exc))
        record_outcome("match_rerank", "error")
        return {}

    items = _parse_tool_output(response)
    # Drop items the model invented (ids it wasn't given) — defensive
    # against schema drift, costs nothing.
    valid_ids = set(cosine_by_vid.keys())
    items = [it for it in items if it.vacancy_id in valid_ids]
    if not items:
        log.warning("match_rerank.empty_tool_call")
        record_outcome("match_rerank", "error")
        return {}

    record_outcome("match_rerank", "success")
    return await _persist_items(
        db,
        resume_id=resume.id,
        cosine_by_vid=cosine_by_vid,
        items=items,
        model=settings.match_rerank_model,
    )
