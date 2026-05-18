"""Channel-approval scoring service (Phase 2 of TG-publication design).

The @proshli curated channel publishes ~5 hand-picked vacancies per
weekday — an order of magnitude tighter than the forum group's
firehose. Phase 2 surfaces the daily top-N to a human admin for
approval rather than auto-publishing.

This module is the pure-function half of that flow: given a candidate
set, compute the composite score and return them sorted descending.
The DB/Telegram side lives in :mod:`workers.tasks.channel_approval`
and the bot callback handlers.

Score weights (from the design spec):

* **salary** 40% — log-scaled ceiling of ``salary_to`` (or
  ``salary_from`` if to is missing) capped at 700k₽ to dampen the
  influence of outliers.
* **prestige** 30% — looked up in :class:`CompanyPrestige`. Misses
  default to ``0.0`` — the daily curation grows that table over time.
* **freshness** 15% — linear decay from "today" (1.0) to "14 days ago"
  (0.0). The publisher already filters anything older than 14 days,
  so this is a tiebreaker between rows already inside the window.
* **topic_demand** 15% — popular topics get a small boost. The
  per-topic factor lives in a module-level dict that mirrors the
  forum group's posting cadence; the design spec calls out the top
  topics by subscriber demand.

All weights sum to 1.0. The pure-function interface (``score_vacancy``)
takes everything it needs as arguments so unit tests don't need a DB.
"""

from __future__ import annotations

import json
import math
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

import structlog
from app.models import ChannelCandidate, CompanyPrestige, Vacancy
from app.time_utils import now_utc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


# Weight schedule. Sum must equal 1.0 — the tests pin this.
WEIGHTS: dict[str, float] = {
    "salary": 0.40,
    "prestige": 0.30,
    "freshness": 0.15,
    "topic_demand": 0.15,
}

# Salary normalisation ceiling — values above 700k₽ saturate to 1.0.
# Captures the top of the realistic IT salary band for Moscow / remote
# without letting a single 2M₽ outlier dominate the score.
_SALARY_CEILING = 700_000.0

# Freshness window in days — anything older saturates to 0.0. Matches
# the prefilter's recency cutoff so the channel never surfaces stale
# rows.
_FRESHNESS_WINDOW_DAYS = 14

# Per-topic demand boost in [0, 1]. Topic ids match
# :mod:`app.services.tg_topics`. Missing entries default to ``0.5``
# (neutral) so unmapped topics aren't penalised.
_TOPIC_DEMAND: dict[int, float] = {
    1: 0.95,  # Python backend
    2: 0.90,  # Go backend
    3: 0.80,  # Frontend
    4: 0.85,  # Data engineering
    5: 0.90,  # ML / AI
    10: 0.75,  # Mobile
    12: 0.70,  # DevOps
    13: 0.75,  # ML Ops
    20: 0.60,  # QA
    24: 0.55,  # Analytics / BI
}


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """Per-component score values for one vacancy. Serialised to JSON."""

    salary: float
    prestige: float
    freshness: float
    topic_demand: float

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    """One scored vacancy. ``total`` is the linear combination of components."""

    vacancy: Vacancy
    total: float
    breakdown: ScoreBreakdown


def normalise_company(name: str | None) -> str:
    """Lowercased, NFKD-normalised, trimmed company name for prestige lookup.

    Pure function — exposed so the curation script can populate
    :class:`CompanyPrestige` with normalised keys without importing
    SQLAlchemy. Doesn't touch case-folding for cyrillic intentionally —
    ``.lower()`` handles cyrillic correctly in modern Python.
    """
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    return decomposed.casefold().strip()


def _salary_score(salary_from: int | None, salary_to: int | None) -> float:
    """Log-scaled salary score in [0, 1]. Returns 0.0 if neither set."""
    raw = salary_to or salary_from or 0
    if raw <= 0:
        return 0.0
    # log scale dampens the top end; cap at ceiling so a 2M₽ outlier
    # doesn't sweep the leaderboard every day.
    capped = min(float(raw), _SALARY_CEILING)
    # log10(1) = 0 maps to 0.0; log10(700_000) maps to 1.0.
    return math.log10(capped) / math.log10(_SALARY_CEILING)


def _freshness_score(published_at: datetime | None, *, now: datetime | None = None) -> float:
    """Linear decay over :data:`_FRESHNESS_WINDOW_DAYS`. Today → 1.0, older → 0."""
    if published_at is None:
        return 0.0
    reference = now or now_utc()
    # ``published_at`` may have been written with naive UTC if the
    # ingester wasn't tz-aware on a given day; treat naive as UTC.
    if published_at.tzinfo is None and reference.tzinfo is not None:
        published_at = published_at.replace(tzinfo=reference.tzinfo)
    elif reference.tzinfo is None and published_at.tzinfo is not None:
        reference = reference.replace(tzinfo=published_at.tzinfo)
    age = reference - published_at
    if age < timedelta(0):
        return 1.0
    if age >= timedelta(days=_FRESHNESS_WINDOW_DAYS):
        return 0.0
    return 1.0 - (age / timedelta(days=_FRESHNESS_WINDOW_DAYS))


def _topic_demand_score(topic_id: int | None) -> float:
    if topic_id is None:
        return 0.5
    return _TOPIC_DEMAND.get(topic_id, 0.5)


def score_vacancy(
    *,
    vacancy: Vacancy,
    prestige: float,
    now: datetime | None = None,
) -> ScoredCandidate:
    """Compute the composite score for one vacancy. Pure function.

    ``prestige`` is looked up by the caller — typically by joining
    :class:`CompanyPrestige` on a normalised company name. Default
    ``0.0`` for misses keeps the score deterministic without forcing
    a DB call inside this function.
    """
    salary = _salary_score(vacancy.salary_from, vacancy.salary_to)
    fresh = _freshness_score(vacancy.published_at, now=now)
    topic = _topic_demand_score(vacancy.topic_id)

    # Clamp prestige into [0, 1] defensively — the column is unbounded.
    prestige_clamped = max(0.0, min(1.0, prestige))

    breakdown = ScoreBreakdown(
        salary=salary,
        prestige=prestige_clamped,
        freshness=fresh,
        topic_demand=topic,
    )
    total = (
        WEIGHTS["salary"] * salary
        + WEIGHTS["prestige"] * prestige_clamped
        + WEIGHTS["freshness"] * fresh
        + WEIGHTS["topic_demand"] * topic
    )
    return ScoredCandidate(vacancy=vacancy, total=total, breakdown=breakdown)


async def load_prestige_index(db: AsyncSession) -> dict[str, float]:
    """One round-trip — load all prestige rows into an in-memory dict.

    The curated set is small (~100 rows) so loading the lot is much
    cheaper than per-vacancy lookups. Returns a dict keyed by the
    already-normalised company name.
    """
    rows = (await db.scalars(select(CompanyPrestige))).all()
    return {row.company_normalised: row.score for row in rows}


async def select_eligible_vacancies(db: AsyncSession, *, limit: int = 200) -> list[Vacancy]:
    """Pick the candidate set the scorer ranks over.

    Same gates as the group prefilter: active, not deleted, recent
    (≤ 14 days), and not yet decided for the channel target this
    batch. The "already decided" filter is handled at the persistence
    step in :mod:`workers.tasks.channel_approval` — keeps this query
    cheap and lets the scorer be DB-shape-agnostic.
    """
    cutoff = now_utc() - timedelta(days=_FRESHNESS_WINDOW_DAYS)
    rows = (
        await db.scalars(
            select(Vacancy)
            .where(Vacancy.is_active.is_(True))
            .where(Vacancy.is_deleted.is_(False))
            .where(Vacancy.published_at >= cutoff)
            .order_by(Vacancy.published_at.desc())
            .limit(limit)
        )
    ).all()
    return list(rows)


async def score_batch(db: AsyncSession, *, top_n: int = 8) -> list[ScoredCandidate]:
    """End-to-end: load prestige index, score eligible vacancies, return top-N.

    Stable ordering: ties break on ``vacancy.id`` descending (newest
    first) so the daily run is deterministic when scores collide.
    """
    prestige_index = await load_prestige_index(db)
    candidates = await select_eligible_vacancies(db, limit=200)
    scored: list[ScoredCandidate] = []
    for v in candidates:
        prestige = prestige_index.get(normalise_company(v.company), 0.0)
        scored.append(score_vacancy(vacancy=v, prestige=prestige))
    scored.sort(key=lambda s: (s.total, s.vacancy.id), reverse=True)
    return scored[:top_n]


async def persist_candidates(
    db: AsyncSession,
    *,
    batch_date: str,
    scored: list[ScoredCandidate],
) -> list[ChannelCandidate]:
    """Insert ``ChannelCandidate`` rows for the day's top-N, idempotently.

    Skips any (vacancy_id, batch_date) pair that already exists — the
    unique constraint would raise IntegrityError, but checking first
    keeps the round-trip cheap when the task is retried mid-batch.
    """
    if not scored:
        return []

    existing_ids = set(
        (
            await db.scalars(
                select(ChannelCandidate.vacancy_id).where(ChannelCandidate.batch_date == batch_date)
            )
        ).all()
    )

    created: list[ChannelCandidate] = []
    for entry in scored:
        if entry.vacancy.id in existing_ids:
            continue
        row = ChannelCandidate(
            vacancy_id=entry.vacancy.id,
            batch_date=batch_date,
            score=entry.total,
            score_breakdown=entry.breakdown.to_json(),
            status="pending",
        )
        db.add(row)
        created.append(row)

    if created:
        await db.flush()
    return created
