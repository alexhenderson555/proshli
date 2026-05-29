# Proshli Architecture

This document describes how the system fits together. For repo layout and
quick-start commands see [`README.md`](../README.md); for Sprint plans see
[`docs/superpowers/`](./superpowers/).

## Domains

- **Auth & Roles** — email/password registration, JWT in an `HttpOnly`
  cookie (`proshli_access`, `SameSite=lax`), seeker/employer roles, and a
  Telegram account-link flow guarded by a shared bot-service key.
- **Vacancy Aggregation** — connectors pull from third-party feeds into
  `raw_vacancies`, dedupe and normalize into `vacancies`. Search supports
  keyword filters plus pgvector semantic ranking on Pro/Employer tiers.
- **Resume** — PDF/text upload with skill extraction, plus a versioned
  builder (`ResumeVersion`) the LLM can rewrite via
  `POST /resumes/versions/{id}/improve`.
- **AI Assistant** — Anthropic Claude streams replies and tool-extracted
  filters over Server-Sent Events. Career-only keyword gate runs first;
  every accepted turn counts against a tier-aware daily budget.
- **Billing** — ЮKassa subscriptions with idempotent webhook delivery
  (deterministic SHA-256 keys, `processed_webhook_events` replay guard,
  `SELECT FOR UPDATE` on the subscription row), three plans (`free`,
  `pro`, `employer`), and a Celery beat job that renews on expiry.
- **Digests** — daily/weekly batches scored against the user's resume
  skills, delivered via Telegram or email per `DigestPreference`.

## Components

| App | Stack | Responsibility |
| --- | --- | --- |
| `apps/api` | FastAPI 0.115, async SQLAlchemy 2, asyncpg, pgvector, Alembic | HTTP surface, domain logic, OpenAPI source of truth. |
| `apps/web` | Next.js 16 (App Router), React 19, Tailwind v4, next-intl, next-themes | RU-default UI (`localePrefix: "as-needed"`, EN at `/en/...`), 4 themes (light/dark/system/oled), SSE consumer for `/ai/chat/stream`. |
| `apps/workers` | Celery 5 + beat | Ingestion runs, digest dispatch, subscription renewal. Async DB code runs through an async→sync bridge. |
| `apps/tgbot` | aiogram | `/start`, `/link`, `/search`, `/digest_*`, `/improve_resume`. Talks to the API as a service principal via `X-Bot-Service-Key`. |
| `packages/shared-types` | OpenAPI-generated TS SDK | Single source of FE types; regenerated from `apps/api/openapi.json`. |
| `packages/ui` | shadcn-style primitives | Buttons, inputs, dialog, sheet, etc. with token-driven theming. |
| `packages/tsconfig`, `packages/eslint-config` | — | Base configs + Next/React-library extends + flat ESLint preset. |

## Cross-cutting concerns

- **Rate limiting** — `app/middleware/rate_limit.py` is a Redis-backed
  sliding bucket (atomic `INCR + EXPIRE NX` pipeline) attached per-route
  via `Depends(RateLimit(...))`. Fails open on Redis outage so one
  dependency can't take the API down. Bucket key is per-IP, namespaced
  per endpoint family. Applied to `auth-register`, `auth-login`,
  `auth-telegram-*`, `ai-chat`, `ai-chat-stream`, `resume-improve`.
- **Trust boundaries** — `X-Forwarded-For` is honoured only when the
  immediate peer is a trusted proxy (see `app.config.settings`). Bot
  endpoints under `/auth/telegram/*` require `secrets.compare_digest`
  on the bot-service key in addition to per-IP rate limits.
- **Money-touching code** — webhook handling uses deterministic
  idempotency keys (SHA-256 over event id), a `processed_webhook_events`
  table to drop replays, and `SELECT ... FOR UPDATE` on the subscription
  row to serialize concurrent webhook deliveries.
- **Error shape** — daily-limit and similar gates return structured
  JSON: `{"detail": {"code": "daily_limit_reached", "limit": N,
  "used_today": N}}` for HTTP errors and a matching SSE
  `data-error` frame for the streaming chat. The non-streaming
  `/ai/chat` keeps its legacy 200-with-`accepted=false` shape for FE
  compatibility.
- **Observability** — `structlog` JSON logs, Sentry hooks on the API and
  web app, Bandit + ruff + mypy strict in CI (48 source files pass).

## Key data flows

**Seeker chat → vacancies:** Browser opens an SSE connection to
`/ai/chat/stream`. The route gates length and career-relevance, checks
the per-day budget, then hands the prompt to `LLMService.stream_chat`.
Tool-use frames become `data-filter` events the FE renders as chips;
content tokens become `data-content`. After the stream closes, usage is
written to `AiUsageEvent` and the budget decrements.

**Bot link:** Web `POST /auth/telegram/link-code` mints an 8-char code
(31-char alphabet, ~30 bits) tied to the user. The user sends it to the
bot, which calls `POST /auth/telegram/consume-link` with the bot-service
key. The endpoint marks the code used, creates the
`TelegramAccountLink`, and returns a JWT the bot caches.

**ЮKassa webhook:** Provider POSTs to `/webhooks/yookassa`. The handler
verifies the signature, computes a deterministic idempotency key,
short-circuits if the event is already in `processed_webhook_events`,
locks the subscription row, applies the state change, and commits
atomically with the replay-guard row.

**Digest run:** Beat schedule fires `dispatch_digest`. Workers select
users whose `DigestPreference.frequency` is due, score recent vacancies
against the user's resume skills, and deliver via the channel the user
chose. Failures are isolated per-user — one bad delivery doesn't tank
the batch.

## Sprint progress

- **Sprint 1 (shipped):** auth, vacancies + ingestion, resume upload,
  AI guardrail + chat, basic digests, bot scaffold, CI gates, mypy
  strict, Bandit. Open carryovers: Storybook, Meilisearch experiment,
  YC deploy pipeline, staging.proshli.ru, self-hosted observability.
- **Sprint 2 (in progress):** ЮKassa billing, LLM streaming with
  tool-use, pgvector semantic search, next-intl + next-themes, resume
  builder + AI improve, bot polish.

## Next milestones

1. Production deploy on a single VPS (Docker Compose, Postgres + pgvector, Redis, Traefik/Caddy for routing).
2. Self-hosted GlitchTip / Plausible to replace SaaS observability on the same VPS.
3. Framer Motion for the marketing surfaces called out in the design
   spec.
4. Storybook for `packages/ui` and a visual-regression suite.
5. Meilisearch experiment for keyword-heavy queries that pgvector
   alone underserves.
