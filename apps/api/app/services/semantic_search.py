"""Semantic vacancy search + embedding backfill.

Wave 4. Two responsibilities live here:

* :func:`embed_vacancy` — synchronous (per-request) helper that writes the
  embedding for a single ``Vacancy`` row. Called from the employer
  create-vacancy path so a freshly-published listing is immediately
  searchable. Failures degrade silently (we log and leave the row's
  embedding NULL) — semantic recall is a search quality feature, not a
  correctness one.

* :func:`search_vacancies_semantic` — runs the user query through the
  embedding service in ``query`` mode, then ORDER BYs by pgvector cosine
  distance and returns the top-K rows. Pre-filters by ``is_active`` /
  ``is_deleted`` so promoted-but-deleted rows can't bubble up.

* :func:`backfill_vacancy_embeddings` — batch helper used by the
  ingestion path and by an admin tool to fill in vectors for rows that
  arrived before the column existed. Idempotent — only touches rows whose
  ``embedding`` column is still NULL.

The route surface is in ``app/routes/vacancies.py``; this module stays
free of FastAPI types so the same helpers can be reused by Celery workers
when they ingest from external feeds.
"""

from __future__ import annotations

import structlog
from app.models import Vacancy
from app.services.embeddings import EmbeddingService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


def _vacancy_text_for_embedding(vacancy: Vacancy) -> str:
    """Concatenate the searchable surface of a vacancy.

    Order matters for the rule-based fallback (each unique string yields a
    unique vector). For the real embedding model the concatenation is what
    we score against — we lead with the title because that's the highest
    signal-to-noise field, then add company / location for disambiguation,
    then the full description.
    """
    parts = [
        vacancy.title or "",
        vacancy.company or "",
        vacancy.location or "",
        vacancy.description or "",
    ]
    return " | ".join(p for p in parts if p)


async def embed_vacancy(
    db: AsyncSession,
    vacancy: Vacancy,
    embedder: EmbeddingService,
) -> None:
    """Write the embedding for one row, committing the change.

    Safe to call inline from a request handler — embeddings are async and
    cheap to fetch (≤200 ms p50 for a single Voyage call). For bulk paths
    use :func:`backfill_vacancy_embeddings` which batches into a single
    API request.
    """
    text = _vacancy_text_for_embedding(vacancy)
    if not text:
        # No content to embed — leave the column NULL so the search ORDER
        # BY skips this row naturally.
        return
    try:
        [vector] = await embedder.embed_texts([text], input_type="document")
    except Exception as exc:  # pragma: no cover — defensive
        log.warning("semantic.embed_vacancy_failed", error=str(exc), vacancy_id=vacancy.id)
        return
    vacancy.embedding = vector
    await db.commit()


async def backfill_vacancy_embeddings(
    db: AsyncSession,
    embedder: EmbeddingService,
    *,
    batch_size: int = 32,
) -> int:
    """Fill in embeddings for rows where the column is NULL.

    Returns the number of rows updated. Caps the work at ``batch_size`` per
    call so a single Celery beat tick doesn't monopolise the connection or
    blow through the embedding-API quota; the caller can loop.
    """
    stmt = (
        select(Vacancy)
        .where(Vacancy.embedding.is_(None))
        .where(Vacancy.is_deleted.is_(False))
        .limit(batch_size)
    )
    rows = list((await db.scalars(stmt)).all())
    if not rows:
        return 0

    texts = [_vacancy_text_for_embedding(row) for row in rows]
    # Empty strings stay aligned — the embedding service is contractually
    # required to return a zero vector for them. We just skip writing it
    # back so the column stays NULL.
    vectors = await embedder.embed_texts(texts, input_type="document")
    updated = 0
    for row, text, vector in zip(rows, texts, vectors, strict=True):
        if not text:
            continue
        row.embedding = vector
        updated += 1
    await db.commit()
    return updated


async def search_vacancies_semantic(
    db: AsyncSession,
    query: str,
    embedder: EmbeddingService,
    *,
    limit: int = 20,
) -> list[Vacancy]:
    """Return up to ``limit`` vacancies ranked by cosine similarity to ``query``.

    Pre-filters: active, not soft-deleted, embedding present. The ORDER BY
    uses pgvector's ``<=>`` cosine-distance operator, which the IVFFLAT
    index built in migration 0012 accelerates.
    """
    text = query.strip()
    if not text:
        return []

    [query_vec] = await embedder.embed_texts([text], input_type="query")

    stmt = (
        select(Vacancy)
        .where(Vacancy.is_deleted.is_(False))
        .where(Vacancy.is_active.is_(True))
        .where(Vacancy.embedding.is_not(None))
        .order_by(Vacancy.embedding.cosine_distance(query_vec))
        .limit(limit)
    )
    return list((await db.scalars(stmt)).all())
