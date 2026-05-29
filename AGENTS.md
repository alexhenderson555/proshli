# Jobskout Agent Guide

This is a pnpm + Turborepo monorepo for an AI job aggregator.

## Project Shape

- `apps/api` is the FastAPI backend with async SQLAlchemy, Alembic, Redis, and Celery settings.
- `apps/web` is the Next.js 16 App Router frontend on React 19 and Tailwind v4. Also read `apps/web/AGENTS.md` before editing web code.
- `apps/workers` contains Celery jobs for ingestion and digest workflows.
- `apps/tgbot` contains the Telegram bot.
- `packages/shared-types` contains OpenAPI-generated TypeScript types.

## Common Commands

- Install JS dependencies from the repo root: `pnpm install`
- Run the full dev stack: `make up`
- Run backend migrations: `make migrate`
- Run all tests: `make test`
- Run lint/format checks: `make lint`
- Regenerate OpenAPI TypeScript types: `make gen-types`

## Working Rules

- Make small, reviewable changes and verify them before moving on.
- Do not remove the existing Anthropic integration unless the task explicitly asks for it.
- Keep secrets out of git. Use `.env` files locally and update `.env.example` only with placeholder names.
- For backend changes, prefer existing FastAPI, pydantic-settings, SQLAlchemy, and Alembic patterns.
- For frontend changes, follow the Next.js version warning in `apps/web/AGENTS.md` and check local docs before relying on older framework assumptions.
