# Proshli — top-level Makefile.
#
# A single front door for the common dev commands. Each target prints its
# action so log scrollback stays readable. Targets are idempotent unless
# otherwise noted.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Avoid mistaking targets for files with the same name.
.PHONY: help dev up down logs ps migrate seed test test-api test-workers test-web \
        lint lint-api lint-web format gen-types clean install ci

help:  ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install JS + Python deps across the workspace.
	pnpm install
	cd apps/api && uv sync --all-groups
	cd apps/workers && uv sync --all-groups

dev:  ## Run the full stack with hot reload (api + web; pg/redis via docker).
	docker compose up -d pg redis
	(cd apps/api && uv run uvicorn app.main:app --reload --port 8000) & \
	(cd apps/web && pnpm dev) ; \
	wait

up:  ## Start the full stack via docker-compose.
	docker compose up -d --build
	@echo "Web:  http://localhost:3000"
	@echo "API:  http://localhost:8000/docs"
	@echo "Health: http://localhost:8000/health/ready"

down:  ## Stop and remove the docker-compose stack (keeps volumes).
	docker compose down

logs:  ## Tail logs from the docker-compose stack.
	docker compose logs -f --tail=100

ps:  ## Show docker-compose service status.
	docker compose ps

migrate:  ## Apply Alembic migrations against the running pg container.
	cd apps/api && uv run alembic upgrade head

seed:  ## Re-create the dev database from scratch (drops + migrates).
	docker compose exec pg psql -U proshli -d proshli -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(MAKE) migrate

test: test-api test-workers test-web  ## Run every test suite.

test-api:  ## Run backend tests.
	cd apps/api && uv run pytest -q

test-workers:  ## Run Celery workers smoke tests.
	cd apps/workers && uv run pytest -q

test-web:  ## Run the frontend Playwright tests.
	pnpm --filter @proshli/web test

lint: lint-api lint-web  ## Run all linters.

lint-api:  ## Backend lint + type-check.
	cd apps/api && uv run ruff check . && uv run mypy app
	cd apps/workers && uv run ruff check . && uv run mypy workers

lint-web:  ## Frontend lint + type-check.
	pnpm -r --parallel run lint || true
	pnpm -r --parallel run type-check

format:  ## Apply autoformatters across the repo.
	cd apps/api && uv run ruff format .
	cd apps/workers && uv run ruff format .
	pnpm prettier --write "**/*.{ts,tsx,md,json,yml}"

gen-types:  ## Regenerate the TS SDK from the live OpenAPI document.
	pnpm -F @proshli/shared-types gen

clean:  ## Remove build artifacts.
	rm -rf node_modules apps/*/node_modules apps/*/.next apps/*/dist packages/*/dist .turbo
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +

ci:  ## Lightweight pre-push check (mirrors CI).
	$(MAKE) lint
	$(MAKE) test
