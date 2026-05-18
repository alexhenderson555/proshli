# Proshli

> AI-агрегатор вакансий для русскоязычного рынка. Один умный поиск
> по десяткам площадок, фильтры на естественном языке и доставка
> подборок в Telegram.

[![Sprint 1](https://img.shields.io/badge/Sprint%201-shipped-success)]()
[![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20Next.js%2016%20%2B%20Celery-blue)]()

## Что внутри

Монорепа на pnpm + Turborepo:

```
apps/
  api/        FastAPI 0.115, async SQLAlchemy 2.0, asyncpg, pgvector, Alembic
  web/        Next.js 16 (App Router), React 19, Tailwind v4, shadcn tokens
  workers/    Celery 5 (ingest + digest), async→sync bridge
  tgbot/      aiogram Telegram bot (scaffold, Sprint 2 hardening)
packages/
  shared-types/   OpenAPI-generated TS SDK
  ui/             Shared shadcn primitives
  tsconfig/       Base + next + react-library TS configs
  eslint-config/  Flat ESLint preset
docs/
  architecture.md
  superpowers/    Plans and specs
ops/
  backup-db.ps1, restore-db.ps1   Postgres backup/restore
```

## Quick start

```bash
# 1) Зависимости
pnpm install
cd apps/api && uv sync && cd -

# 2) Поднять Postgres(+pgvector) и Redis
docker compose up -d postgres redis

# 3) Миграции
cd apps/api && uv run alembic upgrade head && cd -

# 4) Запуск (в трёх терминалах или make-таргетами)
make api     # FastAPI на :8000
make web     # Next.js на :3000
make worker  # Celery worker + beat

# Полный стек одной командой:
make up
```

`http://localhost:3000` — лендинг с живым AI-поиском.
`http://localhost:8000/docs` — Swagger.

## Команды Makefile

| Цель | Что делает |
|------|-----------|
| `make up` | `docker compose up -d` всего стека (pg + redis + api + web + worker + beat) |
| `make down` | остановить и удалить контейнеры |
| `make migrate` | `alembic upgrade head` против запущенного pg |
| `make test` | API pytest + web playwright |
| `make lint` | ruff + eslint + prettier |
| `make format` | автоформат |
| `make gen-types` | генерация TS-типов из OpenAPI |

## Окружение

- `apps/api/.env.example` — серверные переменные FastAPI/Celery
- `apps/web/.env.example` — `NEXT_PUBLIC_*` для Next.js
- `.env.prod.example` — корневые переменные для прод-композа

Валидация — `pydantic-settings` на бэке и `@t3-oss/env-nextjs`+`zod`
на фронте. Отсутствие или неверный формат значения ломает запуск
сразу, а не превращается в 500 в рантайме.

## Документация

- [`docs/architecture.md`](docs/architecture.md) — домены и потоки
- [`docs/superpowers/plans/`](docs/superpowers/plans/) — планы спринтов

## Лицензия / приватность

Репозиторий приватный. Все права на код и бренд — у владельца аккаунта.
