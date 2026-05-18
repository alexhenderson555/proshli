"""vacancies.embedding column + ivfflat index

Revision ID: 0012_vacancy_embeddings
Revises: 0011_billing_tables
Create Date: 2026-05-18

Wave 4: semantic search. We add a nullable ``vector(1024)`` column on
``vacancies`` plus an IVFFLAT cosine-distance index for fast top-K
retrieval. The column stays nullable because:

1. Existing rows have no embedding yet — backfill is a separate (Celery)
   step driven by :func:`app.services.embeddings.get_embedding_service`.
2. The fallback rule-based service can't produce semantically meaningful
   vectors, so a deployment without ``VOYAGE_API_KEY`` should be free to
   leave the column NULL on every row without forcing a server-side
   default that would lie about quality.

Index choice notes:

* ``ivfflat`` with ``lists = 100`` is the pgvector-recommended starting
  point for tables in the 10k–1M row range. Recall ~ 95% at 10 probes;
  we can tune via ``SET ivfflat.probes`` at query time later.
* ``vector_cosine_ops`` matches the embeddings we produce
  (L2-normalised), so cosine distance is identity ≈ Euclidean / 2.
* The index is built CONCURRENTLY because vacancies is a write-hot
  table; an exclusive lock for ``CREATE INDEX`` would briefly stall
  ingestion. CONCURRENTLY can't run inside a transaction → we issue
  raw SQL with ``op.execute`` and rely on autocommit.

The migration is idempotent: it checks for column/index presence before
issuing DDL, so re-running ``alembic upgrade head`` on an environment
that already has the schema is safe.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_vacancy_embeddings"
down_revision: str | Sequence[str] | None = "0011_billing_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_EMBEDDING_DIM = 1024
_INDEX_NAME = "ix_vacancies_embedding_cosine"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("vacancies")}
    if "embedding" not in columns:
        # Raw SQL: SA's ``sa.Column(Vector(...))`` requires the pgvector
        # ORM extension which isn't a hard dep of alembic. Going through
        # text() keeps the migration self-contained.
        op.execute(
            f"ALTER TABLE vacancies "
            f"ADD COLUMN embedding vector({_EMBEDDING_DIM})"
        )

    index_names = {idx["name"] for idx in inspector.get_indexes("vacancies")}
    if _INDEX_NAME not in index_names:
        # Bare index (not CONCURRENTLY) — alembic runs migrations inside a
        # transaction by default, and CREATE INDEX CONCURRENTLY can't live
        # there. For a fresh deployment this is fine; for hot-table
        # rebuilds, ops can drop+recreate concurrently outside alembic.
        op.execute(
            f"CREATE INDEX {_INDEX_NAME} ON vacancies "
            f"USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
        )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_INDEX_NAME}")
    op.execute("ALTER TABLE vacancies DROP COLUMN IF EXISTS embedding")
