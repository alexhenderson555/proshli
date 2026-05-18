"""TG-publication prefilter, post renderer, and enqueue helper.

Phase 1 service for ``docs/superpowers/specs/2026-05-18-tg-publication-design.md``.
Three concerns, kept in one module so the dataflow is readable top-to-bottom:

1. :func:`passes_filter_rules` — the four enqueue gates from the spec
   (description length, recruiter-agency regex, signal-or-salary, dedup).
2. :func:`render_post` — pure function that takes a :class:`Vacancy` + a
   pre-rendered AI summary and produces the HTML body the bot will send.
   Keeps formatting decoupled from DB / LLM concerns; the renderer can
   be unit-tested without spinning either up.
3. :func:`enqueue_vacancy` — orchestrates: filter → classify → render →
   INSERT. Returns the queue id on success, ``None`` if the vacancy
   was rejected (with the reason logged).

The renderer caps the rendered body at 3900 chars (Telegram's hard
limit is 4096; the margin protects against unexpected HTML expansion
in edge-case companies/titles). The AI-summary line gets truncated
first, since it's the only freely sized field.
"""

from __future__ import annotations

import html
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog
from app.models import PublicationQueueItem, Vacancy
from app.services.tg_topics import (
    TopicClassifier,
    get_topic_classifier,
    rule_based_classify,
)
from app.time_utils import now_utc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


# Recruiter / staffing agencies are filtered out — the channel charter
# is direct-employer signal. A handful of common Russian and English
# tokens covers the long tail well enough; we expand on misses.
_RECRUITER_PATTERN = re.compile(
    r"агентств|рекрутинг|подбор персонала|recruit|staffing|hr partner|"
    r"talent partners?",
    re.IGNORECASE,
)

_GRADE_KEYWORDS = re.compile(
    r"\b(middle|senior|lead|principal|staff|tech lead|head of)\b|"
    r"старший|ведущий|тимлид",
    re.IGNORECASE,
)

# Hard cap so the publisher worker never tries to send a >4096-char body.
# The :func:`render_post` truncator targets a margin under this so the
# Telegram API never sees a "MESSAGE_TOO_LONG" error.
_TG_MAX_CHARS = 3900
_AI_SUMMARY_MAX_CHARS = 200


@dataclass(frozen=True, slots=True)
class FilterDecision:
    """Result of running a vacancy through :func:`passes_filter_rules`.

    ``ok`` is True iff the vacancy passes every rule; ``reason`` is a
    short machine-readable code identifying which gate rejected it
    (``"description_too_short"`` etc.). Callers log the reason on
    rejection but never on accept.
    """

    ok: bool
    reason: str = ""


def passes_filter_rules(
    *,
    description: str,
    company: str,
    salary_from: int | None,
    salary_to: int | None,
) -> FilterDecision:
    """Apply the four design-spec gates and return the verdict.

    Order matches the spec § Filter rules — cheap checks first so we
    don't pay for regex compilation against megabyte-sized descriptions
    that will be rejected on the length gate anyway.
    """
    if len(description or "") < 100:
        return FilterDecision(ok=False, reason="description_too_short")

    if _RECRUITER_PATTERN.search(company or ""):
        return FilterDecision(ok=False, reason="recruiter_agency")

    salary_max = salary_to or salary_from or 0
    if salary_max <= 0 and not _GRADE_KEYWORDS.search(description):
        return FilterDecision(ok=False, reason="no_signal")

    return FilterDecision(ok=True)


async def is_duplicate(
    db: AsyncSession, *, vacancy_id: int, target: str
) -> bool:
    """Has this vacancy already been queued for ``target``? Cheap index hit."""
    existing = await db.scalar(
        select(PublicationQueueItem.id)
        .where(PublicationQueueItem.vacancy_id == vacancy_id)
        .where(PublicationQueueItem.target == target)
    )
    return existing is not None


def _truncate(text: str, limit: int) -> str:
    """Trim to ``limit`` chars, appending an ellipsis if cropped."""
    text = text.strip()
    if len(text) <= limit:
        return text
    # 1 char reserved for the ellipsis itself.
    return text[: max(1, limit - 1)].rstrip() + "…"


def _format_salary(
    salary_from: int | None,
    salary_to: int | None,
    currency: str | None,
) -> str:
    """Render the salary range with thin-space-separated thousands.

    The dash means "not specified" — matches the convention RU TG
    aggregators use, so subscribers don't have to learn a new format.
    """
    cur = (currency or "RUB").upper()
    sign = "₽" if cur == "RUB" else cur
    if salary_from and salary_to:
        return f"{salary_from:,} – {salary_to:,} {sign}".replace(",", " ")
    if salary_from:
        return f"от {salary_from:,} {sign}".replace(",", " ")
    if salary_to:
        return f"до {salary_to:,} {sign}".replace(",", " ")
    return "—"


def _format_location(location: str | None) -> str:
    return (location or "").strip() or "—"


def render_post(
    *,
    vacancy: Vacancy,
    ai_summary: str,
    top_skills: list[str],
    base_url: str,
    locale: str = "ru",
) -> str:
    """Render the HTML post body for the bot's ``sendMessage`` call.

    The output is deliberately HTML (not Markdown) because Telegram's
    Markdown parser silently fails on a ``_`` in a company name or a
    parenthesis in a salary range — HTML mode is strictly subsettable
    and easier to escape against. ``html.escape`` is applied to every
    user-controlled field so adversarial titles can't break the layout.
    """
    title = html.escape(vacancy.title or "")
    company = html.escape(vacancy.company or "—")
    salary = _format_salary(
        vacancy.salary_from, vacancy.salary_to, vacancy.currency
    )
    location = html.escape(_format_location(vacancy.location))
    skills_line = " · ".join(html.escape(s) for s in top_skills[:3]) or "—"

    summary_clean = _truncate(ai_summary, _AI_SUMMARY_MAX_CHARS)
    summary_clean = html.escape(summary_clean)

    source = html.escape(vacancy.source or "—")
    base = base_url.rstrip("/")
    cta_url = f"{base}/{locale}/vacancies/{vacancy.id}"

    body = (
        f"🟢 <b>{title}</b> · {company}\n"
        f"💰 {salary} · 📍 {location}\n"
        f"🛠 {skills_line}\n\n"
        f"{summary_clean}\n\n"
        f"🔗 <a href=\"{cta_url}\">Подробнее на Proshli</a>\n"
        f"<i>Источник: {source}</i>"
    )
    return _truncate(body, _TG_MAX_CHARS)


# Type alias for the AI-summary producer the prefilter takes by
# injection. Default impl is a trivial deterministic snippet so the
# function stays unit-testable without an LLM dependency.
SummaryFn = Callable[[Vacancy], Awaitable[str]]


async def _default_summary(vacancy: Vacancy) -> str:
    """Trivial AI-summary stand-in: first sentence of the description.

    Production wiring will swap this for a real LLM call (YandexGPT-Lite
    per the design doc) — keeping the prefilter pluggable means we don't
    have to spin one up in CI / dev.
    """
    description = (vacancy.description or "").strip()
    if not description:
        return ""
    # Split on Russian or Latin sentence boundaries; one trailing dot is
    # restored so the truncated form still reads as a sentence.
    sentence = re.split(r"(?<=[.!?])\s+", description, maxsplit=1)[0]
    return _truncate(sentence, _AI_SUMMARY_MAX_CHARS)


async def enqueue_vacancy(
    db: AsyncSession,
    vacancy: Vacancy,
    *,
    target: str = "group",
    base_url: str,
    locale: str = "ru",
    summary_fn: SummaryFn | None = None,
    classifier: TopicClassifier | None = None,
) -> int | None:
    """Run the full Phase-1 pipeline for one vacancy.

    Returns the new ``publication_queue.id`` on success, or ``None`` if
    the vacancy was rejected. Idempotent for the ``(vacancy_id, target)``
    pair — a second call for the same vacancy returns ``None`` and logs
    ``"duplicate"`` as the reason.
    """
    decision = passes_filter_rules(
        description=vacancy.description or "",
        company=vacancy.company or "",
        salary_from=vacancy.salary_from,
        salary_to=vacancy.salary_to,
    )
    if not decision.ok:
        log.info(
            "tg_publication.rejected",
            vacancy_id=vacancy.id,
            reason=decision.reason,
        )
        return None

    if await is_duplicate(db, vacancy_id=vacancy.id, target=target):
        log.info(
            "tg_publication.rejected",
            vacancy_id=vacancy.id,
            reason="duplicate",
        )
        return None

    # Classify if we don't have a cached topic id, or honour the cached
    # one if the LLM previously placed the vacancy. ``target='channel'``
    # rows have no topic, by design.
    topic_id: int | None = None
    if target == "group":
        if vacancy.topic_id is not None:
            topic_id = vacancy.topic_id
        else:
            cls = classifier or get_topic_classifier()
            topic_id = await cls.classify(
                title=vacancy.title or "",
                description=vacancy.description or "",
            )
            vacancy.topic_id = topic_id
            vacancy.classified_at = now_utc()

    fn = summary_fn or _default_summary
    summary = await fn(vacancy)

    # ``parsed_skills`` is a comma-separated string on the Resume model
    # but Vacancy doesn't carry parsed skills today. We derive a tiny
    # placeholder from the title until the parser ships — keeps the
    # template populated without a separate migration. Production will
    # replace this with extracted skills (Wave 12 of the spec).
    fallback_skills = [
        word
        for word in re.split(r"[ ,/]+", (vacancy.title or ""))
        if len(word) > 2
    ][:3]

    rendered = render_post(
        vacancy=vacancy,
        ai_summary=summary,
        top_skills=fallback_skills,
        base_url=base_url,
        locale=locale,
    )

    item = PublicationQueueItem(
        vacancy_id=vacancy.id,
        target=target,
        topic_id=topic_id,
        rendered_text=rendered,
        status="pending",
        scheduled_for=now_utc(),
        attempts=0,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item.id


def fallback_classify(*, title: str, description: str) -> int:
    """Re-export for callers that want the deterministic path explicitly.

    Useful for backfill scripts that don't want to pay the LLM round-trip
    on millions of historical rows.
    """
    return rule_based_classify(title=title, description=description)
