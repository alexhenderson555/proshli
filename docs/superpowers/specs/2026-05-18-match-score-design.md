# Match-Score MVP — Design

**Status:** Draft for execution. Decisions pre-committed per "делай как лучше" mandate.

## Goal

Show users a numeric compatibility score (0–100) + tier label on every vacancy card, computed from their resume vs the vacancy. Score is the single most-visible reason a logged-in user with a resume opens a vacancy. Without it Proshli looks like a search box; with it Proshli looks like a recommender.

## Why now

- Embedding infrastructure for vacancies already exists (voyage-3 → 1024d, stored on `Vacancy.embedding`).
- Resume upload already exists and persists `raw_text` + `parsed_skills`.
- The single missing piece is one column (`Resume.embedding`), one compute call at upload time, and the cosine read path. Everything else is wiring.

## Architecture

```
PDF upload ─► extract_text ─► generate embedding (voyage-3) ─► Resume row {raw_text, parsed_skills, embedding}
                                                                          │
                                                                          ▼
GET /vacancies (include_match=true) ──► resolve current user's latest resume ──► pgvector cosine
                                                                                          │
                                                                                          ▼
                                                       VacancyOut + match_score: float | null
```

- **Source of truth for match:** cosine similarity between `Resume.embedding` and `Vacancy.embedding`.
- **Why pure cosine for v1:** voyage-3 is trained for retrieval; cosine on it is already strong baseline. LLM reranking deferred to v2 (would gate behind premium tier).
- **No background recomputation table.** Compute on demand; pgvector handles per-query cosine in <10 ms for 100k rows with HNSW index.

## Data model

### Resume — add embedding column

```python
class Resume(Base):
    ...
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM),  # 1024
        nullable=True,
    )
```

- Nullable: existing resumes won't be backfilled synchronously; first /match request for them triggers a one-time backfill (cheap — just one embed call).
- No HNSW index on `resumes.embedding` — we never search resumes by similarity, we only fetch by user_id.

### Migration `0017_resume_embedding.py`

```python
op.add_column(
    "resumes",
    sa.Column("embedding", Vector(1024), nullable=True),
)
# No backfill — done lazily on first read.
```

## Backend

### Upload path — `apps/api/app/routes/resumes.py`

Existing `/resumes/upload` writes `raw_text` and `parsed_skills`. Extend it:

```python
embedding_service = get_embedding_service()
emb = await embedding_service.embed(raw_text[:8000])  # voyage-3 input cap
resume.embedding = emb
```

- Truncate at 8000 chars — voyage-3 hard limit is ~32k tokens, but resumes longer than 8k chars are usually noise (project lists). Keeps cost predictable.
- Embedding is generated synchronously inside the upload request. Adds ~300 ms; acceptable for a once-per-resume action.
- Fallback: if `voyage-3` call raises, log + persist `embedding=None`; the lazy-backfill path will retry on first match request.

### List endpoint — `GET /vacancies?include_match=true`

```python
@router.get("/vacancies")
async def list_vacancies(
    ...,
    include_match: bool = False,
    user: User | None = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await _query_vacancies(db, filters)

    if include_match and user:
        resume_emb = await _user_resume_embedding(db, user.id)  # backfills if missing
        if resume_emb is not None:
            scores = await _batch_match_scores(db, resume_emb, [v.id for v in items])
            for v, s in zip(items, scores):
                v.match_score = s
    return items
```

- `_user_resume_embedding`: fetches most recent resume; if `embedding IS NULL`, regenerates from `raw_text` and persists. If user has zero resumes, returns `None`.
- `_batch_match_scores`: single SQL `SELECT id, 1 - (embedding <=> :resume_emb) AS score FROM vacancies WHERE id = ANY(:ids) AND embedding IS NOT NULL`. Returns dict id→score, missing IDs map to `None`.

### Single endpoint — `GET /vacancies/{id}/match-score`

Returns `{"score": 0.92, "tier": "strong"}` or `404` if vacancy not embedded or user has no resume.

Why a dedicated endpoint exists alongside `include_match=true`: the vacancy **detail** page (separate from list) needs the score after page load and we don't want to re-fetch the whole list.

### Tier mapping (single source of truth — server-side helper)

```python
def match_tier(score: float) -> str:
    if score >= 0.80: return "strong"
    if score >= 0.60: return "decent"
    if score >= 0.40: return "stretch"
    return "longshot"
```

Reasoning for thresholds: voyage-3 cosine for genuinely matching docs sits ~0.75–0.90; weakly related docs ~0.55. Calibrated against the dataset spec — re-tune in v2 after we observe distribution from real users.

Localized labels live in next-intl messages (`matchScore.strong` / `.decent` / `.stretch` / `.longshot`), not on the API. API returns the machine key.

## Frontend

### Vacancy type — `apps/web/lib/types.ts`

Add optional fields:

```ts
match_score?: number | null;  // 0..1
match_tier?: "strong" | "decent" | "stretch" | "longshot" | null;
```

### Vacancy list query

The vacancies page calls `api.vacancies({ ..., include_match: true })` only when `getToken()` returns a token. Anonymous request stays exactly as today.

### Vacancy card — match pill

Slot the pill **above the title row** (it's the loudest signal):

```tsx
{vacancy.match_score != null && (
  <MatchPill score={vacancy.match_score} tier={vacancy.match_tier} />
)}
```

Pill format: `{percent}% · {label}` where `label = t(`matchScore.${tier}`)`. Color via tier:

- strong → accent (Proshli green)
- decent → text-primary on neutral bg
- stretch → text-secondary on neutral bg
- longshot → text-tertiary on neutral bg (deliberately quiet — we don't shout about bad matches)

### Empty / no-resume state

If `getToken()` returns a token but `match_score` comes back `null` for every vacancy (signal: user has no resume), replace the pill area on the **first card only** with an inline upload CTA:

```
[Загрузи резюме чтобы видеть match-score →]
```

Why only the first card: repeating it on every card is nagging.

### Anonymous

No pill anywhere; no inline CTA. Anonymous users are pre-conversion — we sell with the demo on landing, not match-scores in the list.

### Vacancy detail page

After mount, fetch `GET /vacancies/{id}/match-score` and render a larger pill block in the sidebar (or top of action panel).

## Edge cases

| Case | Behavior |
| --- | --- |
| User has multiple resumes | Use most recent (`ORDER BY created_at DESC LIMIT 1`). No "active" flag for MVP. |
| Resume has no embedding (legacy or upload failure) | Lazy backfill from `raw_text` on first match request. If `raw_text` is also empty, return `null` scores. |
| Vacancy has no embedding (rare — most parsers fill it) | Score is `null` for that vacancy; card renders without pill. |
| Resume `raw_text` empty / unparseable PDF | `parsed_skills=""` already happens today; we set `embedding=None`. Frontend treats null as no-score. |
| User just signed up, no resume | Inline CTA on first card as above. |
| Score = 0.0 exactly | Treat as `longshot`. Never hide a valid score. |

## Out of scope (deferred to v2)

- LLM reranking ("explain why this is a match").
- Skill-tag overlap visualization.
- Salary expectation overlay (user said "I want ≥350k" → score multiplied).
- Resume "active" flag with multiple-resume picker.
- Match-score-based default sort (we keep promoted-first for now).

## Test plan

- Unit: `match_tier(0.79) == "decent"`, `match_tier(0.80) == "strong"`, etc.
- Unit: cosine math via fixtures (two synthetic vectors, known cosine).
- Integration: upload PDF resume → assert `Resume.embedding` is non-null and length 1024.
- Integration: `GET /vacancies?include_match=true` returns `match_score` for vacancies that have embeddings, `null` for those that don't.
- Integration: anonymous request to `?include_match=true` is silently ignored (no score returned).
- E2E: logged-in user with resume sees pill on `/vacancies` page. Logged-in user without resume sees CTA. Anonymous sees neither.

## Rollout

1. Migration adds nullable column (zero downtime).
2. Upload path starts generating embeddings on every new resume.
3. Endpoints ship behind `include_match` flag (default `false`) so old web client keeps working.
4. Frontend updates the list query + adds pill component.
5. Detail-page fetch wired last.

No feature flag needed — `include_match` opt-in is enough.
