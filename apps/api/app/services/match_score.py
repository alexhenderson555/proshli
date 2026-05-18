"""Match-score service: cosine similarity, tier mapping, batch scoring.

Single source of truth for the score tier thresholds — keep them here, not
duplicated in the route layer or the frontend. The frontend receives the
machine key (``strong`` / ``decent`` / ``stretch`` / ``longshot``) and
resolves localized labels via next-intl.

Thresholds are calibrated against voyage-3 cosine distribution observed
during early testing; re-tune in v2 after real-user data.
"""

from __future__ import annotations

import math
from typing import Literal

import structlog
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Resume, Vacancy  # noqa: F401  (Vacancy used in raw SQL)
from app.services.embeddings import get_embedding_service

log = structlog.get_logger(__name__)

Tier = Literal["strong", "decent", "stretch", "longshot"]


def match_tier(score: float) -> Tier:
    """Map a cosine similarity score in [-1, 1] to a human tier label.

    Thresholds (voyage-3 calibrated):
    * >= 0.80  → strong    (clear role match)
    * >= 0.60  → decent    (reasonable overlap)
    * >= 0.40  → stretch   (some alignment)
    * < 0.40   → longshot  (little semantic overlap)
    """
    if score >= 0.80:
        return "strong"
    if score >= 0.60:
        return "decent"
    if score >= 0.40:
        return "stretch"
    return "longshot"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors, returning a value in [-1, 1].

    Returns 0.0 for empty, mismatched-length, or zero-magnitude inputs
    rather than raising — callers can treat 0.0 as "no signal".
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


async def user_resume_embedding(
    db: AsyncSession, user_id: int
) -> list[float] | None:
    """Return the user's most recent resume embedding, lazy-backfilling if null.

    Flow:
    1. Fetch the newest ``Resume`` row for ``user_id`` (ordered by
       ``created_at`` DESC).
    2. If none exists → ``None``.
    3. If ``embedding`` is already populated → return it.
    4. If ``embedding`` is NULL but ``raw_text`` is non-empty → call the
       embedding service, persist the result, return it.
    5. If ``raw_text`` is also empty → ``None`` (nothing to embed).

    No retries or caching are added here — those are deferred to v2 once
    real traffic shapes are known.
    """
    resume = await db.scalar(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(desc(Resume.created_at))
        .limit(1)
    )
    if resume is None:
        return None
    if resume.embedding is not None:
        return [float(x) for x in resume.embedding]
    if not resume.raw_text or not resume.raw_text.strip():
        return None
    try:
        service = get_embedding_service()
        vectors = await service.embed_texts(
            [resume.raw_text[:8000]], input_type="query"
        )
        emb = vectors[0]
    except Exception as exc:
        log.warning(
            "match_score.backfill_failed",
            error=str(exc),
            resume_id=resume.id,
        )
        return None
    resume.embedding = emb
    await db.commit()
    return [float(x) for x in emb]


async def batch_match_scores(
    db: AsyncSession,
    resume_emb: list[float],
    vacancy_ids: list[int],
) -> dict[int, float | None]:
    """Cosine similarity for each vacancy_id against the resume embedding.

    Returns ``id → score`` in [-1, 1]. Vacancies without an embedding map
    to ``None``. Uses pgvector's ``<=>`` (cosine distance operator);
    score = 1 - distance.

    The vector literal is passed as a plain Python list stringified to the
    ``[x, y, …]`` format that pgvector's text parser accepts. SQLAlchemy
    ``text()`` with a named bind parameter keeps the query safe from
    injection (the list comes from our own embedding service, not from user
    input, but the cast pattern is consistent with
    :func:`app.services.semantic_search.search_vacancies_semantic`).
    """
    if not vacancy_ids:
        return {}
    rows = await db.execute(
        text(
            "SELECT id, 1 - (embedding <=> CAST(:emb AS vector)) AS score "
            "FROM vacancies "
            "WHERE id = ANY(:ids) AND embedding IS NOT NULL"
        ),
        {"emb": str(resume_emb), "ids": vacancy_ids},
    )
    scored = {row.id: float(row.score) for row in rows}
    return {vid: scored.get(vid) for vid in vacancy_ids}
