# Match-Score MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface a numeric 0–100 match score + tier on every vacancy card for logged-in users with a resume, computed as cosine(resume.embedding, vacancy.embedding) over voyage-3 1024d vectors.

**Architecture:** One nullable column added to `resumes`; embedding generated synchronously on upload; cosine read path served by pgvector's `<=>` operator; one new endpoint + one new query param on `/vacancies`; pill rendered above title row in the existing `VacancyCard`.

**Tech Stack:** SQLAlchemy 2 async + pgvector + voyage-3 (existing `get_embedding_service`) + FastAPI + Next.js 16 + Tailwind 4 + next-intl.

**Spec:** [docs/superpowers/specs/2026-05-18-match-score-design.md](../specs/2026-05-18-match-score-design.md)

---

### Task 1: Resume.embedding column + Alembic migration

**Files:**
- Modify: `apps/api/app/models.py` (Resume class around line 158)
- Create: `apps/api/alembic/versions/0017_resume_embedding.py`
- Test: `apps/api/tests/test_resume_embedding_migration.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_resume_embedding_migration.py
import pytest
from sqlalchemy import inspect, text
from app.db import engine

@pytest.mark.asyncio
async def test_resumes_table_has_embedding_column():
    async with engine.connect() as conn:
        cols = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_columns("resumes")
        )
    names = {c["name"] for c in cols}
    assert "embedding" in names

@pytest.mark.asyncio
async def test_resume_embedding_is_nullable_vector_1024():
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT data_type, udt_name, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'resumes' AND column_name = 'embedding'"
                )
            )
        ).first()
    assert row is not None
    assert row.is_nullable == "YES"
    assert row.udt_name == "vector"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_resume_embedding_migration.py -v`
Expected: FAIL — `"embedding" not in names` (column does not yet exist).

- [ ] **Step 3: Add the column to the model**

In `apps/api/app/models.py`, locate the `Resume` class and add the `embedding` field immediately after `parsed_skills`:

```python
from pgvector.sqlalchemy import Vector  # already imported elsewhere in this file

class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_skills: Mapped[str] = mapped_column(Text, default="")
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(_EMBEDDING_DIM), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    owner: Mapped[User] = relationship(back_populates="resumes")
```

`_EMBEDDING_DIM = 1024` is already defined at the top of `models.py` for `Vacancy.embedding`. Reuse that exact constant — do not redeclare.

- [ ] **Step 4: Create the Alembic migration**

```python
# apps/api/alembic/versions/0017_resume_embedding.py
"""Add nullable embedding column to resumes.

Lazy backfill: existing resumes get embeddings on first /match request.
No HNSW index — we never search resumes by similarity, only fetch by user_id.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0017_resume_embedding"
down_revision = "0016_channel_approval"
branch_labels = None
depends_on = None

_EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.add_column(
        "resumes",
        sa.Column("embedding", Vector(_EMBEDDING_DIM), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resumes", "embedding")
```

- [ ] **Step 5: Apply the migration**

Run: `cd apps/api && alembic upgrade head`
Expected: `INFO  [alembic.runtime.migration] Running upgrade 0016_channel_approval -> 0017_resume_embedding`

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest apps/api/tests/test_resume_embedding_migration.py -v`
Expected: 2 PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/models.py apps/api/alembic/versions/0017_resume_embedding.py apps/api/tests/test_resume_embedding_migration.py
git commit -m "feat(match-score): add nullable Resume.embedding column"
```

---

### Task 2: Generate resume embedding on upload

**Files:**
- Modify: `apps/api/app/routes/resumes.py` (upload_resume around line 32)
- Test: `apps/api/tests/test_resume_upload_embedding.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_resume_upload_embedding.py
import io
import pytest
from httpx import AsyncClient

from app.models import Resume
from sqlalchemy import select

@pytest.mark.asyncio
async def test_upload_resume_persists_embedding(
    auth_client_seeker: AsyncClient, db_session
):
    files = {"file": ("cv.txt", io.BytesIO(b"Python developer, 5 years FastAPI"), "text/plain")}
    resp = await auth_client_seeker.post("/resumes/upload?name=cv", files=files)
    assert resp.status_code == 201
    resume_id = resp.json()["id"]

    row = await db_session.scalar(select(Resume).where(Resume.id == resume_id))
    assert row.embedding is not None
    assert len(row.embedding) == 1024


@pytest.mark.asyncio
async def test_upload_resume_embedding_failure_does_not_block_upload(
    auth_client_seeker: AsyncClient, db_session, monkeypatch
):
    from app.services import embeddings as emb_mod

    class BrokenService:
        async def embed(self, text):
            raise RuntimeError("voyage-3 down")

    monkeypatch.setattr(emb_mod, "get_embedding_service", lambda: BrokenService())

    files = {"file": ("cv.txt", io.BytesIO(b"Some resume text"), "text/plain")}
    resp = await auth_client_seeker.post("/resumes/upload?name=cv", files=files)
    assert resp.status_code == 201  # Upload still succeeds

    resume_id = resp.json()["id"]
    row = await db_session.scalar(select(Resume).where(Resume.id == resume_id))
    assert row.embedding is None  # Fallback to None on failure
```

`auth_client_seeker` is the existing test fixture in `apps/api/tests/conftest.py` (verify name matches the fixture; if not, copy the pattern from `test_resume_upload.py`).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_resume_upload_embedding.py -v`
Expected: FAIL — first test fails because `embedding` is `None` (no generation yet).

- [ ] **Step 3: Wire embedding generation into upload**

In `apps/api/app/routes/resumes.py`, after the existing `skills = extract_skills(raw_text)` line and before the `Resume(...)` construction, add:

```python
import structlog
log = structlog.get_logger(__name__)

from app.services.embeddings import get_embedding_service

# ... inside upload_resume, after skills extraction:
try:
    embedding_service = get_embedding_service()
    # voyage-3 hard limit is ~32k tokens; 8000 chars is a safe + cheap cap.
    embedding = await embedding_service.embed(raw_text[:8000])
except Exception as exc:
    log.warning("resume.embedding_failed", error=str(exc))
    embedding = None

resume = Resume(
    user_id=current_user.id,
    name=name,
    raw_text=raw_text,
    parsed_skills=", ".join(skills),
    embedding=embedding,
    created_at=now_utc(),
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/test_resume_upload_embedding.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/routes/resumes.py apps/api/tests/test_resume_upload_embedding.py
git commit -m "feat(match-score): embed resume text on upload"
```

---

### Task 3: Match-score service module (cosine + tiers + lazy backfill)

**Files:**
- Create: `apps/api/app/services/match_score.py`
- Test: `apps/api/tests/test_match_score_service.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_match_score_service.py
import pytest
import numpy as np

from app.services.match_score import (
    cosine_similarity,
    match_tier,
    user_resume_embedding,
    batch_match_scores,
)
from app.models import Resume, User
from app.time_utils import now_utc


def test_match_tier_thresholds():
    assert match_tier(0.95) == "strong"
    assert match_tier(0.80) == "strong"
    assert match_tier(0.799) == "decent"
    assert match_tier(0.60) == "decent"
    assert match_tier(0.59) == "stretch"
    assert match_tier(0.40) == "stretch"
    assert match_tier(0.39) == "longshot"
    assert match_tier(0.0) == "longshot"


def test_cosine_similarity_known_vectors():
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(1.0)
    c = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, c) == pytest.approx(0.0)
    d = [-1.0, 0.0, 0.0]
    assert cosine_similarity(a, d) == pytest.approx(-1.0)


@pytest.mark.asyncio
async def test_user_resume_embedding_returns_most_recent(db_session):
    user = User(email="u@test", password_hash="x", role="seeker", created_at=now_utc())
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    older = Resume(user_id=user.id, name="old", raw_text="x", parsed_skills="",
                   embedding=[0.1] * 1024, created_at=now_utc())
    db_session.add(older)
    await db_session.commit()

    # Newer resume with different embedding
    import asyncio
    await asyncio.sleep(0.01)
    newer = Resume(user_id=user.id, name="new", raw_text="y", parsed_skills="",
                   embedding=[0.2] * 1024, created_at=now_utc())
    db_session.add(newer)
    await db_session.commit()

    emb = await user_resume_embedding(db_session, user.id)
    assert emb[0] == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_user_resume_embedding_none_when_no_resume(db_session):
    user = User(email="empty@test", password_hash="x", role="seeker", created_at=now_utc())
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    emb = await user_resume_embedding(db_session, user.id)
    assert emb is None


@pytest.mark.asyncio
async def test_user_resume_embedding_backfills_when_null(db_session, monkeypatch):
    from app.services import embeddings as emb_mod

    class FakeService:
        async def embed(self, text):
            return [0.5] * 1024

    monkeypatch.setattr(emb_mod, "get_embedding_service", lambda: FakeService())

    user = User(email="bf@test", password_hash="x", role="seeker", created_at=now_utc())
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    r = Resume(user_id=user.id, name="r", raw_text="content for embed",
               parsed_skills="", embedding=None, created_at=now_utc())
    db_session.add(r)
    await db_session.commit()
    await db_session.refresh(r)

    emb = await user_resume_embedding(db_session, user.id)
    assert emb is not None
    assert emb[0] == pytest.approx(0.5)

    # Verify the backfill was persisted
    await db_session.refresh(r)
    assert r.embedding is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_match_score_service.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.match_score`.

- [ ] **Step 3: Implement the service**

```python
# apps/api/app/services/match_score.py
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

from app.models import Resume, Vacancy
from app.services.embeddings import get_embedding_service

log = structlog.get_logger(__name__)

Tier = Literal["strong", "decent", "stretch", "longshot"]


def match_tier(score: float) -> Tier:
    if score >= 0.80:
        return "strong"
    if score >= 0.60:
        return "decent"
    if score >= 0.40:
        return "stretch"
    return "longshot"


def cosine_similarity(a: list[float], b: list[float]) -> float:
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
    """Return the user's most recent resume embedding, lazy-backfilling if null."""
    resume = await db.scalar(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(desc(Resume.created_at))
        .limit(1)
    )
    if resume is None:
        return None
    if resume.embedding is not None:
        return list(resume.embedding)
    if not resume.raw_text.strip():
        return None
    try:
        service = get_embedding_service()
        emb = await service.embed(resume.raw_text[:8000])
    except Exception as exc:
        log.warning("match_score.backfill_failed", error=str(exc), resume_id=resume.id)
        return None
    resume.embedding = emb
    await db.commit()
    return list(emb)


async def batch_match_scores(
    db: AsyncSession, resume_emb: list[float], vacancy_ids: list[int]
) -> dict[int, float | None]:
    """Compute cosine similarity for each vacancy_id against the resume embedding.

    Returns a dict id→score in [-1, 1]. Vacancies without an embedding map to None.
    Uses pgvector's ``<=>`` (cosine distance) operator; score = 1 - distance.
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest apps/api/tests/test_match_score_service.py -v`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/services/match_score.py apps/api/tests/test_match_score_service.py
git commit -m "feat(match-score): cosine + tiers + lazy resume backfill"
```

---

### Task 4: API — extend GET /vacancies with include_match

**Files:**
- Modify: `apps/api/app/routes/vacancies.py`
- Modify: `apps/api/app/schemas.py` (VacancyOut)
- Test: `apps/api/tests/test_vacancies_include_match.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_vacancies_include_match.py
import pytest
from httpx import AsyncClient

from app.models import Resume, Vacancy
from app.time_utils import now_utc


@pytest.mark.asyncio
async def test_anonymous_request_omits_match_score(client: AsyncClient, db_session):
    v = Vacancy(title="Python", company="Acme", location="Remote",
                description="...", embedding=[0.1] * 1024,
                published_at=now_utc(), is_active=True, source="manual")
    db_session.add(v)
    await db_session.commit()

    resp = await client.get("/vacancies?include_match=true")
    assert resp.status_code == 200
    for item in resp.json():
        assert item.get("match_score") is None
        assert item.get("match_tier") is None


@pytest.mark.asyncio
async def test_authed_user_with_resume_gets_match_score(
    auth_client_seeker: AsyncClient, db_session, seeker_user
):
    db_session.add_all([
        Resume(user_id=seeker_user.id, name="cv", raw_text="x",
               parsed_skills="", embedding=[0.5] * 1024, created_at=now_utc()),
        Vacancy(title="Python", company="Acme", location="Remote",
                description="...", embedding=[0.5] * 1024,
                published_at=now_utc(), is_active=True, source="manual"),
    ])
    await db_session.commit()

    resp = await auth_client_seeker.get("/vacancies?include_match=true")
    items = resp.json()
    assert len(items) >= 1
    item = items[0]
    assert item["match_score"] is not None
    assert item["match_score"] == pytest.approx(1.0, abs=0.01)
    assert item["match_tier"] == "strong"


@pytest.mark.asyncio
async def test_authed_user_no_resume_returns_null_match(
    auth_client_seeker: AsyncClient, db_session
):
    v = Vacancy(title="Go", company="Beta", location="Remote",
                description="...", embedding=[0.1] * 1024,
                published_at=now_utc(), is_active=True, source="manual")
    db_session.add(v)
    await db_session.commit()

    resp = await auth_client_seeker.get("/vacancies?include_match=true")
    assert resp.status_code == 200
    for item in resp.json():
        assert item["match_score"] is None
        assert item["match_tier"] is None


@pytest.mark.asyncio
async def test_include_match_default_false_returns_no_score_field(
    auth_client_seeker: AsyncClient, db_session
):
    resp = await auth_client_seeker.get("/vacancies")
    # Field can be absent or null; we accept either, as long as it's not a number
    for item in resp.json():
        score = item.get("match_score")
        assert score is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_vacancies_include_match.py -v`
Expected: FAIL — `match_score` field doesn't exist on response.

- [ ] **Step 3: Add fields to VacancyOut schema**

In `apps/api/app/schemas.py`, locate `VacancyOut` and add:

```python
class VacancyOut(BaseModel):
    ...existing fields...
    match_score: float | None = None
    match_tier: Literal["strong", "decent", "stretch", "longshot"] | None = None
```

Add `Literal` to the imports if not present.

- [ ] **Step 4: Wire match-score into the list endpoint**

In `apps/api/app/routes/vacancies.py`, find the `list_vacancies` (or equivalent) handler. Add `include_match: bool = False` to the signature and, after the items are fetched, run:

```python
from app.services.match_score import (
    batch_match_scores, match_tier, user_resume_embedding,
)
# At the top of the file:
from app.auth import optional_current_user  # if not already importing

# Inside the handler, after items are loaded:
if include_match and current_user is not None:
    resume_emb = await user_resume_embedding(db, current_user.id)
    if resume_emb is not None:
        scores = await batch_match_scores(
            db, resume_emb, [item.id for item in items]
        )
        for item in items:
            s = scores.get(item.id)
            if s is not None:
                item.match_score = s
                item.match_tier = match_tier(s)
```

If `optional_current_user` does not exist, copy the pattern from any route that supports anonymous access (likely `/vacancies` already supports anonymous; verify the existing auth dep — if it's `get_current_user_optional`, use that). The dependency must NOT raise on missing token; it must return `None`.

If the handler currently returns ORM objects directly via `response_model=list[VacancyOut]`, you must convert to dicts/Pydantic before attaching match fields (Pydantic v2 may not pick up dynamic attributes on ORM rows). Build the response list as `VacancyOut.model_validate(item, from_attributes=True)`, then mutate the resulting Pydantic objects:

```python
out: list[VacancyOut] = [VacancyOut.model_validate(it, from_attributes=True) for it in items]
if include_match and current_user is not None:
    resume_emb = await user_resume_embedding(db, current_user.id)
    if resume_emb is not None:
        scores = await batch_match_scores(db, resume_emb, [o.id for o in out])
        for o in out:
            s = scores.get(o.id)
            if s is not None:
                o.match_score = s
                o.match_tier = match_tier(s)
return out
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest apps/api/tests/test_vacancies_include_match.py -v`
Expected: 4 PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/routes/vacancies.py apps/api/app/schemas.py apps/api/tests/test_vacancies_include_match.py
git commit -m "feat(match-score): include_match query param on GET /vacancies"
```

---

### Task 5: API — dedicated GET /vacancies/{id}/match-score

**Files:**
- Modify: `apps/api/app/routes/vacancies.py`
- Modify: `apps/api/app/schemas.py` (add MatchScoreOut)
- Test: `apps/api/tests/test_vacancy_match_score_endpoint.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_vacancy_match_score_endpoint.py
import pytest
from httpx import AsyncClient

from app.models import Resume, Vacancy
from app.time_utils import now_utc


@pytest.mark.asyncio
async def test_match_score_endpoint_strong_tier(
    auth_client_seeker: AsyncClient, db_session, seeker_user
):
    db_session.add(Resume(user_id=seeker_user.id, name="cv", raw_text="x",
                          parsed_skills="", embedding=[0.5] * 1024,
                          created_at=now_utc()))
    v = Vacancy(title="Python", company="Acme", location="Remote",
                description="...", embedding=[0.5] * 1024,
                published_at=now_utc(), is_active=True, source="manual")
    db_session.add(v)
    await db_session.commit()
    await db_session.refresh(v)

    resp = await auth_client_seeker.get(f"/vacancies/{v.id}/match-score")
    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] == pytest.approx(1.0, abs=0.01)
    assert body["tier"] == "strong"


@pytest.mark.asyncio
async def test_match_score_endpoint_no_resume_returns_404(
    auth_client_seeker: AsyncClient, db_session
):
    v = Vacancy(title="Go", company="Beta", location="Remote",
                description="...", embedding=[0.1] * 1024,
                published_at=now_utc(), is_active=True, source="manual")
    db_session.add(v)
    await db_session.commit()
    await db_session.refresh(v)

    resp = await auth_client_seeker.get(f"/vacancies/{v.id}/match-score")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_match_score_endpoint_anonymous_returns_401(
    client: AsyncClient
):
    resp = await client.get("/vacancies/1/match-score")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_match_score_endpoint_vacancy_without_embedding_returns_404(
    auth_client_seeker: AsyncClient, db_session, seeker_user
):
    db_session.add(Resume(user_id=seeker_user.id, name="cv", raw_text="x",
                          parsed_skills="", embedding=[0.5] * 1024,
                          created_at=now_utc()))
    v = Vacancy(title="Old", company="Z", location="Remote",
                description="...", embedding=None,
                published_at=now_utc(), is_active=True, source="manual")
    db_session.add(v)
    await db_session.commit()
    await db_session.refresh(v)

    resp = await auth_client_seeker.get(f"/vacancies/{v.id}/match-score")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_vacancy_match_score_endpoint.py -v`
Expected: FAIL — `404 Not Found` (endpoint doesn't exist).

- [ ] **Step 3: Add the schema**

In `apps/api/app/schemas.py`:

```python
class MatchScoreOut(BaseModel):
    score: float
    tier: Literal["strong", "decent", "stretch", "longshot"]
```

- [ ] **Step 4: Add the endpoint**

In `apps/api/app/routes/vacancies.py`:

```python
from app.schemas import MatchScoreOut
from app.services.match_score import (
    batch_match_scores, match_tier, user_resume_embedding,
)

@router.get("/{vacancy_id}/match-score", response_model=MatchScoreOut)
async def get_match_score(
    vacancy_id: int,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> MatchScoreOut:
    resume_emb = await user_resume_embedding(db, current_user.id)
    if resume_emb is None:
        raise HTTPException(status_code=404, detail="No resume on file")
    scores = await batch_match_scores(db, resume_emb, [vacancy_id])
    score = scores.get(vacancy_id)
    if score is None:
        raise HTTPException(status_code=404, detail="Vacancy not embedded")
    return MatchScoreOut(score=score, tier=match_tier(score))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest apps/api/tests/test_vacancy_match_score_endpoint.py -v`
Expected: 4 PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/routes/vacancies.py apps/api/app/schemas.py apps/api/tests/test_vacancy_match_score_endpoint.py
git commit -m "feat(match-score): GET /vacancies/{id}/match-score endpoint"
```

---

### Task 6: Frontend types + API client method

**Files:**
- Modify: `apps/web/lib/types.ts`
- Modify: `apps/web/lib/api.ts`

- [ ] **Step 1: Extend Vacancy type**

In `apps/web/lib/types.ts`, locate the `Vacancy` interface (or type) and add:

```ts
export interface Vacancy {
  // ...existing fields...
  match_score?: number | null;
  match_tier?: "strong" | "decent" | "stretch" | "longshot" | null;
}

export interface MatchScoreOut {
  score: number;
  tier: "strong" | "decent" | "stretch" | "longshot";
}
```

- [ ] **Step 2: Add includeMatch param to api.vacancies + new matchScore method**

In `apps/web/lib/api.ts`:

```ts
async vacancies(params: {
  location?: string;
  stack?: string;
  level?: string;
  source?: string;
  work_mode?: string;
  min_salary?: number;
  include_match?: boolean;
  token?: string;
}): Promise<Vacancy[]> {
  const qs = new URLSearchParams();
  if (params.location) qs.set("location", params.location);
  if (params.stack) qs.set("stack", params.stack);
  if (params.level) qs.set("level", params.level);
  if (params.source) qs.set("source", params.source);
  if (params.work_mode) qs.set("work_mode", params.work_mode);
  if (params.min_salary != null) qs.set("min_salary", String(params.min_salary));
  if (params.include_match) qs.set("include_match", "true");

  const headers: Record<string, string> = {};
  if (params.token) headers["Authorization"] = `Bearer ${params.token}`;

  const resp = await fetch(`${BASE}/vacancies?${qs}`, { headers });
  if (!resp.ok) throw new Error(`vacancies: ${resp.status}`);
  return resp.json();
},

async matchScore(token: string, vacancyId: number): Promise<MatchScoreOut> {
  const resp = await fetch(`${BASE}/vacancies/${vacancyId}/match-score`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error(`match-score: ${resp.status}`);
  return resp.json();
},
```

Do NOT add a test for the API client — it's a thin fetch wrapper and is covered by the e2e + integration tests in later tasks.

- [ ] **Step 3: Type-check**

Run: `cd apps/web && pnpm tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/lib/types.ts apps/web/lib/api.ts
git commit -m "feat(match-score): web types + api client method"
```

---

### Task 7: MatchPill component + i18n labels

**Files:**
- Create: `apps/web/components/match-pill.tsx`
- Modify: `apps/web/messages/ru.json`
- Modify: `apps/web/messages/en.json`

- [ ] **Step 1: Add localized labels**

In `apps/web/messages/ru.json`, locate the top-level (do NOT nest under `vacancyCard`) and add:

```json
{
  "matchScore": {
    "strong": "Сильное совпадение",
    "decent": "Хорошее совпадение",
    "stretch": "Стоит попробовать",
    "longshot": "Слабое совпадение",
    "noResume": "Загрузи резюме — увидишь match-score"
  }
}
```

In `apps/web/messages/en.json`:

```json
{
  "matchScore": {
    "strong": "Strong match",
    "decent": "Decent match",
    "stretch": "Stretch",
    "longshot": "Long shot",
    "noResume": "Upload your resume to see match-score"
  }
}
```

- [ ] **Step 2: Create the MatchPill component**

```tsx
// apps/web/components/match-pill.tsx
"use client";

// Visual weight follows tier: strong = accent (loud), decent = primary text,
// stretch / longshot = quiet greys. We don't shout about bad matches —
// they're still useful as filtering signal but shouldn't compete with title.

import { useTranslations } from "next-intl";

export type MatchTier = "strong" | "decent" | "stretch" | "longshot";

const TIER_CLASS: Record<MatchTier, string> = {
  strong: "border-accent/30 bg-accent/10 text-accent",
  decent: "border-border bg-elevated text-text-primary",
  stretch: "border-border bg-elevated text-text-secondary",
  longshot: "border-border bg-elevated text-text-tertiary",
};

export function MatchPill({
  score,
  tier,
}: {
  score: number;
  tier: MatchTier;
}) {
  const t = useTranslations("matchScore");
  const percent = Math.round(Math.max(0, Math.min(1, score)) * 100);
  return (
    <span
      className={
        "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 " +
        "text-[11px] font-[510] tabular-nums " +
        TIER_CLASS[tier]
      }
      data-tier={tier}
    >
      {percent}% · {t(tier)}
    </span>
  );
}
```

- [ ] **Step 3: Type-check + lint**

Run: `cd apps/web && pnpm tsc --noEmit && pnpm lint`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/components/match-pill.tsx apps/web/messages/ru.json apps/web/messages/en.json
git commit -m "feat(match-score): MatchPill component + i18n labels"
```

---

### Task 8: Render MatchPill in VacancyCard

**Files:**
- Modify: `apps/web/components/vacancy-card.tsx`

- [ ] **Step 1: Slot the pill above the title row**

In `apps/web/components/vacancy-card.tsx`, locate the header line (`<div className="flex flex-wrap items-center gap-1.5 text-text-tertiary">`). Add the pill as a *first child of that same row* so it sits beside the source badge (most visible spot, no layout shift when null):

```tsx
import { MatchPill, type MatchTier } from "@/components/match-pill";

// ... inside the component, in the header row JSX:
<div className="flex flex-wrap items-center gap-1.5 text-text-tertiary">
  {vacancy.match_score != null && vacancy.match_tier ? (
    <MatchPill
      score={vacancy.match_score}
      tier={vacancy.match_tier as MatchTier}
    />
  ) : null}
  <Badge text={sourceLabel} />
  ...
</div>
```

- [ ] **Step 2: Type-check**

Run: `cd apps/web && pnpm tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/vacancy-card.tsx
git commit -m "feat(match-score): render MatchPill in VacancyCard"
```

---

### Task 9: Vacancies page — pass include_match + handle no-resume CTA

**Files:**
- Modify: `apps/web/app/[locale]/vacancies/page.tsx`

- [ ] **Step 1: Pass token + include_match to the search call**

In `apps/web/app/[locale]/vacancies/page.tsx`, modify the `search` callback to read the token at call time and pass `include_match: true` only when a token exists:

```tsx
import { getToken } from "@/lib/session";

// inside `search`:
const token = getToken();
const data = await api.vacancies({
  location, stack, level, source,
  work_mode: workMode,
  min_salary: minSalary ? Number(minSalary) : undefined,
  include_match: Boolean(token),
  token: token ?? undefined,
});
setVacancies(data);
```

- [ ] **Step 2: Inline no-resume CTA on the first card**

After the existing `orderedVacancies` memo, add:

```tsx
const hasToken = typeof window !== "undefined" && Boolean(getToken());
const allMissingScore = hasToken
  && orderedVacancies.length > 0
  && orderedVacancies.every((v) => v.match_score == null);
```

(Note: this client-only check is fine — the component is already `"use client"` and `getToken()` reads localStorage.)

Then, in the feed render section, before the `<Stagger>`, conditionally render the CTA banner:

```tsx
{allMissingScore && (
  <Link
    href="/resume"
    className="mb-2 inline-flex w-fit items-center gap-1 rounded border border-accent/30 bg-accent/10 px-2 py-1 text-[12px] font-[510] text-accent transition-colors hover:bg-accent/15"
  >
    {t("noResumeCta")} →
  </Link>
)}
```

Add `noResumeCta` to the `vacancies` namespace in both `ru.json` and `en.json`:

- ru: `"noResumeCta": "Загрузи резюме — увидишь match-score"`
- en: `"noResumeCta": "Upload your resume to see match-score"`

Use `Link` from `@/i18n/navigation` (the file already imports it elsewhere; if not, add the import).

- [ ] **Step 3: Type-check + dev-server smoke**

Run: `cd apps/web && pnpm tsc --noEmit && pnpm build`
Expected: 0 errors. Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add apps/web/app/[locale]/vacancies/page.tsx apps/web/messages/ru.json apps/web/messages/en.json
git commit -m "feat(match-score): pass include_match from vacancies page + no-resume CTA"
```

---

### Task 10: Vacancy detail page — fetch match-score after mount

**Files:**
- Find via Glob: `apps/web/app/[locale]/vacancies/[id]/page.tsx` (verify path; if structure differs, adapt)
- Test: manual smoke (no unit test — UI render)

- [ ] **Step 1: Locate the detail page**

Run: Glob `apps/web/app/[locale]/vacancies/[id]/**/*.tsx`
If no `[id]` route exists yet, create `apps/web/app/[locale]/vacancies/[id]/page.tsx` is **out of scope for this plan** — leave a TODO comment in the vacancies page and skip Task 10. (We don't ship half a feature; if there's no detail page, the list-pill is sufficient for MVP.)

- [ ] **Step 2: If the detail page exists, add the match-score fetch**

```tsx
"use client";

import { useEffect, useState } from "react";
import { MatchPill, type MatchTier } from "@/components/match-pill";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { MatchScoreOut } from "@/lib/types";

export function MatchScoreBlock({ vacancyId }: { vacancyId: number }) {
  const [data, setData] = useState<MatchScoreOut | null>(null);
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    let cancelled = false;
    api.matchScore(token, vacancyId)
      .then((res) => { if (!cancelled) setData(res); })
      .catch(() => { /* swallow — render nothing on error */ });
    return () => { cancelled = true; };
  }, [vacancyId]);

  if (!data) return null;
  return (
    <div className="rounded border border-border bg-surface p-3">
      <MatchPill score={data.score} tier={data.tier as MatchTier} />
    </div>
  );
}
```

Render `<MatchScoreBlock vacancyId={vacancy.id} />` in the detail page's sidebar / top of action panel.

- [ ] **Step 3: Type-check**

Run: `cd apps/web && pnpm tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/app/[locale]/vacancies/[id]/
git commit -m "feat(match-score): vacancy detail page match-score block"
```

---

### Task 11: E2E smoke — full path

**Files:**
- Modify or create: `apps/web/e2e/match-score.spec.ts` (depending on whether Playwright is wired)

- [ ] **Step 1: Add the smoke test**

```ts
// apps/web/e2e/match-score.spec.ts
import { test, expect } from "@playwright/test";

test("logged-out user sees no match pill on vacancy list", async ({ page }) => {
  await page.goto("/en/vacancies");
  await expect(page.locator('[data-tier]')).toHaveCount(0);
});

test("logged-in user without resume sees no-resume CTA", async ({ page, context }) => {
  // Seed token via localStorage; the test backend must have a user without a resume.
  // If e2e auth seeding doesn't exist yet, skip this test with .skip.
  test.skip(true, "Requires e2e auth seeding — covered by manual smoke for now");
});

test("logged-in user with resume sees match pill", async ({ page }) => {
  test.skip(true, "Requires e2e resume + vacancy seeding — covered by API tests");
});
```

This test file is intentionally minimal — the API-level coverage in Tasks 1–5 is the real safety net. The skipped tests document the intent and remain as a placeholder for full seeding in a future iteration.

- [ ] **Step 2: Run Playwright (if configured)**

Run: `cd apps/web && pnpm test:e2e -- match-score.spec.ts`
Expected: 1 pass, 2 skipped. If Playwright isn't wired in this repo, leave the file as documentation and skip this step.

- [ ] **Step 3: Commit**

```bash
git add apps/web/e2e/match-score.spec.ts
git commit -m "feat(match-score): e2e smoke skeleton"
```

---

### Task 12: Manual smoke + docs touch-up

- [ ] **Step 1: Manual smoke locally**

Start the dev stack (`docker-compose up` or whatever the repo uses), then:
1. Anonymous: visit `/ru/vacancies` → confirm no pills, no CTA.
2. Sign up + log in, no resume yet → visit `/ru/vacancies` → confirm CTA banner appears above the feed on the first card.
3. Upload a resume via `/ru/resume` → return to `/ru/vacancies` → confirm pills appear on cards with a percentage.

- [ ] **Step 2: Update the spec status header**

In `docs/superpowers/specs/2026-05-18-match-score-design.md`, change the status line from `Draft for execution.` to `Implemented YYYY-MM-DD.` with the actual date.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-05-18-match-score-design.md
git commit -m "docs(match-score): mark spec implemented"
```

---

## Definition of Done

- Migration applied; existing resumes are nullable-embedding rows; new uploads persist 1024d embeddings.
- `GET /vacancies?include_match=true` returns `match_score` + `match_tier` for vacancies that have embeddings; anonymous requests get `null`.
- `GET /vacancies/{id}/match-score` returns score + tier; 404 when user has no resume or vacancy has no embedding; 401 when anonymous.
- `MatchPill` renders in the vacancy card header row when score is non-null.
- Logged-in users with no resume see exactly one inline CTA banner above the feed.
- Anonymous users see no match UI at all.
- All new tests pass; existing tests still pass.
