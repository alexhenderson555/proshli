# JobSkout

## Что делает продукт

Production-minded **MVP** платформы вакансий: **веб (Next.js)** + **Telegram-бот**, роли соискатель/работодатель, поиск вакансий с фильтрами, резюме и извлечение текста из PDF, **ИИ-помощник** (только карьерная тематика), дайджесты, ingestion из нескольких источников, **PostgreSQL** + Alembic, планировщик, тесты и CI.

## Преимущества

- Монорепо: API, современный веб, бот, Docker для прода.
- Контроль стоимости ИИ (лимиты), безопасные режимы доставки дайджестов без секретов.

## Установка (кратко)

См. детальные блоки ниже в этом README: **Quick Start (Backend)**, **PostgreSQL + Migrations**, **Quick Start (Next.js Web)**, **Telegram Bot**, **Production Deployment (Docker)**. Общий шаг: скопировать **`backend/.env.example`** → **`backend/.env`**.

## Траблшутинг

| Проблема | Что проверить |
|----------|----------------|
| API не стартует | venv, `pip install -r backend/requirements.txt`, `DATABASE_URL`, миграции Alembic. |
| 401 / 403 на API | JWT, заголовки, `BOT_SERVICE_KEY` для бота. |
| Бот не линкуется с сайтом | Код `/link`, `JOBSKOUT_API_URL`, одинаковый `BOT_SERVICE_KEY` с бэкендом. |
| Дайджест не уходит | `TELEGRAM_BOT_TOKEN`, SMTP vars; без них — dry-run (см. раздел Digest). |
| Docker prod | `docker-compose.prod.yml`, миграции внутри контейнера, бэкапы из `ops/`. |

## Structure

- `backend/` - FastAPI API
- `web/` - Next.js web app (primary UI)
- `frontend/` - lightweight web MVP console
- `bot/` - Telegram bot scaffold
- `docs/` - architecture and product notes

## Environment

- Copy **`backend/.env.example`** → **`backend/.env`** (or use root **`.env.example`** as a reminder).
- Production-style vars: see **`.env.prod.example`**.

## Quick Start (Backend)

1. Create virtual environment:
   - Windows PowerShell:
     - `python -m venv .venv`
     - `.venv\Scripts\Activate.ps1`
2. Install deps:
   - `pip install -r backend/requirements.txt`
3. Run API:
   - `uvicorn app.main:app --reload --app-dir backend`
4. Open docs:
   - <http://127.0.0.1:8000/docs>

## PostgreSQL + Migrations (Production path)

1. Start database:
   - `docker compose up -d postgres`
2. Set env:
   - `DATABASE_URL=postgresql+psycopg2://jobskout:jobskout@localhost:5432/jobskout`
   - `AUTO_CREATE_SCHEMA=false`
3. Run migrations:
   - `alembic -c backend/alembic.ini upgrade head`
4. If you already created tables via `AUTO_CREATE_SCHEMA=true`, mark baseline first:
   - `alembic -c backend/alembic.ini stamp head`
   - then run `alembic -c backend/alembic.ini upgrade head`

## Quality / Tests

- Run backend tests:
  - `set PYTHONPATH=backend`
  - `.venv\Scripts\python -m pytest backend/tests -q`
- Run lint/security checks:
  - `.venv\Scripts\ruff check backend`
  - `.venv\Scripts\bandit -c .bandit -r backend/app`

## Demo Data / Ingestion

- Seed local vacancies:
  - `.venv\Scripts\python backend/scripts/seed_demo_vacancies.py`
- Run digest preview for all users:
  - `.venv\Scripts\python backend/scripts/run_digest_preview.py`
- Ingest demo source via API (employer token required):
  - `POST /ingest/hh`
  - `POST /ingest/company_sites`
  - `POST /ingest/rss` (uses `RSS_SOURCE_URLS`)
- List all configured connectors:
  - `GET /sources`
- Public vacancy search supports archive filtering:
  - `GET /vacancies?include_archived=true`

## Worker / Scheduler

- Run one scheduler iteration (ingestion + digest dispatch):
  - `POST /admin/run-scheduler?frequency=daily`
- Run looped worker from CLI:
  - `.venv\Scripts\python backend/scripts/worker_loop.py --frequency daily --interval-seconds 300 --iterations 5`

## Production Deployment (Docker)

1. Copy env template:
   - `copy .env.prod.example .env.prod`
2. Start stack:
   - `docker compose -f docker-compose.prod.yml up -d --build`
3. Run migrations:
   - `docker compose -f docker-compose.prod.yml exec api alembic -c backend/alembic.ini upgrade head`
4. DB backup / restore:
   - `.\ops\backup-db.ps1`
   - `.\ops\restore-db.ps1 -BackupFile .\backups\jobskout-YYYYMMDD-HHMMSS.sql`
5. If local tables were created before latest revisions:
   - `alembic -c backend/alembic.ini stamp head`

## Digest Delivery Channels

- Telegram: uses `TELEGRAM_BOT_TOKEN` + `telegram_chat_id` from user preferences.
- Email: uses SMTP env vars from `backend/.env.example`.
- If channel credentials are missing, delivery runs in safe dry-run mode (for local dev).

## Profile & Resume Builder API

- Seeker profile:
  - `GET /profiles/seeker`
  - `PUT /profiles/seeker`
- Employer profile:
  - `GET /profiles/employer`
  - `PUT /profiles/employer`
- Employer vacancy ownership:
  - `POST /vacancies` auto-links vacancy to current employer
  - `GET /vacancies/my?status=all|active|archived&sort_by=published_at|applications_count|title&order=asc|desc`
  - `GET /vacancies/my/page?page=1&page_size=10&status=...&sort_by=...&order=...`
  - `PUT /vacancies/{vacancy_id}` (owner only)
  - `POST /vacancies/{vacancy_id}/archive` (owner only)
  - `POST /vacancies/{vacancy_id}/publish` (owner only)
  - `POST /vacancies/{vacancy_id}/promote` (owner only, paid placement hook)
  - `DELETE /vacancies/{vacancy_id}` (owner only, soft delete)
  - `GET /vacancies/my/analytics`
  - `GET /vacancies/my/actions?limit=30&action=vacancy_archived&vacancy_id=123&created_from=<ISO>&created_to=<ISO>`
  - `GET /vacancies/my/actions/export?limit=200&action=vacancy_updated`
- Resume constructor versions:
  - `POST /resumes/versions`
  - `GET /resumes/versions`
- Telegram account linking (one-time code flow):
  - `POST /auth/telegram/link-code` (authorized seeker on website)
  - `POST /auth/telegram/consume-link` (bot service, by code)
  - `POST /auth/telegram/login` (bot service, by telegram user id)

## Quick Start (Next.js Web)

1. Install deps:
   - `cd web`
   - `npm install`
2. Set env:
   - `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`
3. Run:
   - `npm run dev`
4. Open:
   - <http://127.0.0.1:3000/vacancies>

### Web smoke checks

- Lint:
  - `npm run lint`
- Build:
  - `npm run build`
- E2E smoke:
  - `npm run test:e2e`

## Quick Start (Legacy Frontend Console)

- Open `frontend/index.html` in browser after API is running.
- Frontend supports:
  - auth (register/login)
  - AI filter parsing
  - vacancy search
  - source ingestion and scheduler run
  - digest preview
  - resume upload (PDF/TXT)

## Quick Start (Telegram Bot)

1. Set env vars:
   - `TELEGRAM_BOT_TOKEN`
   - `JOBSKOUT_API_URL=http://127.0.0.1:8000`
   - `BOT_SERVICE_KEY=<same key as backend BOT_SERVICE_KEY>`
   - `REQUIRE_CHANNEL_SUBSCRIPTION=true`
   - `REQUIRED_CHANNEL_USERNAME=@iischnaya`
   - `EMPLOYER_PROMO_URL=https://t.me/your_channel_or_landing`
2. Run:
   - `python bot/main.py`
3. Linking flow:
   - login on website as seeker
   - click "Сгенерировать код привязки Telegram"
   - send code to bot: `/link ABCD1234`

## Initial Product Principles

- AI assistant answers only career and job-search related requests.
- AI usage is cost-controlled with per-user daily limits.
- Digest delivery is configurable:
  - Telegram bot: daily / weekly
  - Website: email daily / weekly

