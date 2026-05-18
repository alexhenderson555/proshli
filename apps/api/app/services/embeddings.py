"""Text embeddings for semantic vacancy search.

Wave 4 introduces a small abstraction over the embedding backend so the
rest of the codebase doesn't have to know whether the deployment is talking
to Voyage AI (Anthropic's recommended embeddings provider) or to a local
deterministic fallback:

* :class:`VoyageEmbeddingService` — wraps ``voyageai.AsyncClient``. Uses
  ``voyage-3`` by default (1024 dims) which is the sweet spot of cost/recall
  for short Russian + English job-board text. Inputs are batched per call;
  the SDK handles backoff and retries.

* :class:`RuleBasedEmbeddingService` — fallback used when the API key is
  empty *or* the SDK isn't installed. Produces a deterministic pseudo-
  embedding via SHA-256 → 1024 floats in ``[-1, 1]``. Useless for actual
  semantic recall, but keeps every code path that depends on
  ``embed_texts`` runnable in CI without provisioning a key, and gives the
  semantic-search endpoint a stable ordering for tests.

The selector :func:`get_embedding_service` is cached for the process
lifetime; tests that need a fresh decision call
``get_embedding_service.cache_clear()`` (same pattern as the LLM service).

Embedding dimensions are fixed at module load so the pgvector column type
in migration ``0012_vacancy_embeddings`` can hard-code the value — a
runtime mismatch between ``EMBEDDING_DIM`` and the column type would surface
as a SQL error on the first INSERT, which is the loud failure mode we want.
"""

from __future__ import annotations

import hashlib
import math
from functools import lru_cache
from typing import Protocol

import structlog
from app.config import settings

log = structlog.get_logger(__name__)

# Hard-pinned. ``voyage-3`` outputs 1024-d vectors; the pgvector column type
# in migration 0012 must match. Changing this constant requires a new
# migration that drops + re-creates the column (no in-place dim change in
# pgvector).
EMBEDDING_DIM: int = 1024


class EmbeddingService(Protocol):
    """Protocol shared by the real and fallback embedding backends."""

    name: str
    dim: int

    async def embed_texts(
        self, texts: list[str], *, input_type: str = "document"
    ) -> list[list[float]]:
        """Return one ``dim``-length embedding per input string.

        Implementations must preserve order and handle empty strings without
        raising — empty input should produce a zero vector (callers rely on
        this to skip cosine ranking for rows without descriptions).

        ``input_type`` ∈ {``"document"``, ``"query"``} mirrors the Voyage
        convention. The rule-based fallback ignores it; the real backend
        uses it to pick the matching tower of the asymmetric embedding
        model (queries and documents live in different subspaces of the
        joint encoder).
        """
        ...


def _normalise(vec: list[float]) -> list[float]:
    """Scale a vector to unit length so cosine distance == 1 - dot product.

    Callers that store these in pgvector and use ``<=>`` benefit either way,
    but pre-normalising the *query* lets the rule-based fallback give stable
    rankings without depending on the index choice.
    """
    mag = math.sqrt(sum(x * x for x in vec))
    if mag == 0.0:
        return vec
    return [x / mag for x in vec]


class RuleBasedEmbeddingService:
    """Deterministic SHA-256-derived pseudo-embeddings.

    The output is *not* semantically meaningful — two paraphrases of the same
    sentence will produce uncorrelated vectors. That's fine: this backend
    exists so the rest of the stack stays exercisable without a Voyage key,
    and so tests can monkeypatch the service with a tiny lookup table to
    verify ordering.

    Determinism guarantees:

    * Same input string → same vector across processes
    * Different inputs → different vectors (collision probability negligible
      for our scale)
    * Output is L2-normalised so cosine and dot product coincide
    """

    name = "rule_based"
    dim = EMBEDDING_DIM

    async def embed_texts(
        self, texts: list[str], *, input_type: str = "document"
    ) -> list[list[float]]:
        # ``input_type`` ignored — the rule-based path has nothing to gain
        # from distinguishing query vs document tower since the vectors
        # are derived from a hash, not a model.
        del input_type
        return [self._embed_one(text) for text in texts]

    @staticmethod
    def _embed_one(text: str) -> list[float]:
        if not text:
            return [0.0] * EMBEDDING_DIM
        # SHA-256 gives us 256 bits → 32 bytes. Repeat-hash four extension
        # chunks to fill 1024 bytes, then map each byte to a float in
        # ``[-1, 1]``. Cheap and stable.
        material = bytearray()
        seed = text.encode("utf-8")
        for i in range(EMBEDDING_DIM // 32):
            h = hashlib.sha256(seed + i.to_bytes(2, "big")).digest()
            material.extend(h)
        vec = [(b - 128) / 128.0 for b in material[:EMBEDDING_DIM]]
        return _normalise(vec)


class VoyageEmbeddingService:
    """Real embedding path via Voyage AI's async SDK.

    Voyage is Anthropic's recommended embeddings vendor and is more accurate
    on Russian text than OpenAI's ``text-embedding-3-small`` in our internal
    spot-checks. We use ``voyage-3`` (1024-d, ~$0.06 / 1M tokens) for both
    indexing and querying — production stays on a single model so cosine
    comparisons remain meaningful (mixing models invalidates the vector
    space).
    """

    name = "voyage"
    dim = EMBEDDING_DIM

    def __init__(self, *, api_key: str, model: str) -> None:
        # Lazy import — environments without ``voyageai`` installed still
        # boot via the rule-based fallback.
        import voyageai  # type: ignore[import-not-found]

        self._client = voyageai.AsyncClient(api_key=api_key)
        self._model = model

    async def embed_texts(
        self, texts: list[str], *, input_type: str = "document"
    ) -> list[list[float]]:
        if not texts:
            return []
        # Voyage requires non-empty strings; substitute a single space for
        # empty entries so the indices stay aligned with the input list.
        prepared = [t if t else " " for t in texts]
        try:
            result = await self._client.embed(
                texts=prepared,
                model=self._model,
                # ``input_type="document"`` for stored vacancy descriptions,
                # ``"query"`` for user search text. The search route calls
                # with the query variant when scoring user input.
                input_type=input_type,
            )
            return [list(map(float, v)) for v in result.embeddings]
        except Exception as exc:  # pragma: no cover — network / quota faults
            log.warning("embeddings.voyage_failed", error=str(exc))
            # Degrade to rule-based so the caller still gets *something*
            # back; a zero result would break the ORDER BY in the search
            # route. Tests cover the happy path; this branch is the
            # defensive ramp.
            return await RuleBasedEmbeddingService().embed_texts(texts)


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return the active embedding backend.

    Mirror of :func:`app.services.llm.get_llm_service`: cached, selects the
    real client when the API key is present, falls back to deterministic
    pseudo-embeddings otherwise. A failed import of ``voyageai`` also falls
    back so the API is bootable in light CI images that don't carry the
    SDK.
    """
    api_key = getattr(settings, "voyage_api_key", "") or ""
    if not api_key:
        log.info("embeddings.using_rule_based", reason="no_api_key")
        return RuleBasedEmbeddingService()
    model = getattr(settings, "voyage_model", "voyage-3") or "voyage-3"
    try:
        return VoyageEmbeddingService(api_key=api_key, model=model)
    except ImportError:  # pragma: no cover — exercised in stripped images
        log.warning("embeddings.voyage_sdk_missing")
        return RuleBasedEmbeddingService()
