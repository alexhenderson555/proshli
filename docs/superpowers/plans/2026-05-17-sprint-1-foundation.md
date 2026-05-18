# Sprint 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Поднять Proshli на Yandex Cloud staging — Next.js 16 web + FastAPI async api + Celery workers + TG-бот в Turborepo-монорепо. CI green, Postgres+pgvector готов, Redis готов, дизайн-токены и Storybook живые, обсервабилити подключена. Готовый стартовый каркас для разработки Sprint 2-7.

**Architecture:** Turborepo monorepo с `apps/{web,api,workers,tgbot}` и `packages/{ui,shared-types,config}`. FastAPI на SQLAlchemy 2 async + asyncpg + pgvector. Next.js 16 (App Router) + Tailwind 4 + shadcn/ui + next-themes (4 темы) + next-intl (RU/EN) + Framer Motion. Деплой через Docker + GitHub Actions в Yandex Cloud Serverless Containers. Observability: Sentry + self-hosted Plausible.

**Tech Stack:** TypeScript 5, Python 3.12, Next.js 16, React 19, FastAPI, SQLAlchemy 2 async, asyncpg, Postgres 16 + pgvector, Redis 7, Celery, Tailwind 4, shadcn/ui, next-themes, next-intl, Framer Motion, Storybook 8, Sentry, Plausible, pnpm 11, uv 0.4, GitHub Actions, Yandex Cloud, Turborepo 2.

**Working directory:** `C:/Users/Alex/Cursor/jobskout/` (будет переименован в Sprint 1 Task 0)

---

## Pre-flight: домен и Yandex Cloud (вне основного потока разработки)

### Pre-1: Регистрация домена proshli.ru

- [ ] **Step 1: Проверить доступность домена**

В браузере открыть https://www.namecheap.com или https://reg.ru, поиск `proshli.ru`. Если занят — fallback на `proshli.io`, потом `proshli.app`.

- [ ] **Step 2: Зарегистрировать домен на 2 года**

Через namecheap или reg.ru. Сохранить креды регистратора в bitwarden/1password.

- [ ] **Step 3: Дополнительно: занять proshli.ru, proshli.io для брендозащиты**

Подождать решения о торговой марке (Task 0 ниже) — после может быть проще регистрировать.

### Pre-2: Yandex Cloud setup

- [ ] **Step 1: Создать организацию и folder**

В консоли https://console.yandex.cloud/: организация `proshli`, дефолтный folder `proshli-staging`. Привязать платёжный аккаунт.

- [ ] **Step 2: Установить yc CLI**

Windows PowerShell как админ:

```powershell
iex (New-Object System.Net.WebClient).DownloadString('https://storage.yandexcloud.net/yandexcloud-yc/install.ps1')
yc init
```

- [ ] **Step 3: Создать VPC и подсеть**

```bash
yc vpc network create --name proshli-staging
yc vpc subnet create --name proshli-staging-default \
  --zone ru-central1-a --network-name proshli-staging --range 10.0.1.0/24
```

- [ ] **Step 4: Создать Managed Postgres 16 с pgvector**

```bash
yc managed-postgresql cluster create \
  --name proshli-staging-pg --environment production \
  --network-name proshli-staging \
  --host zone-id=ru-central1-a,subnet-name=proshli-staging-default \
  --resource-preset s2.micro --disk-size 20 --disk-type network-ssd \
  --postgresql-version 16 \
  --user name=proshli,password=<STRONG_PWD> \
  --database name=proshli,owner=proshli,extensions=vector
```

Сохранить connection string в bitwarden как `YC_PG_DSN`.

- [ ] **Step 5: Создать Managed Redis**

```bash
yc managed-redis cluster create \
  --name proshli-staging-redis --environment production \
  --network-name proshli-staging \
  --host zone=ru-central1-a,subnet-name=proshli-staging-default \
  --resource-preset hm1.nano --disk-size 16 --redis-version 7.2
```

Сохранить host:port в bitwarden как `YC_REDIS_URL`.

- [ ] **Step 6: Создать Object Storage bucket**

```bash
yc storage bucket create --name proshli-staging-uploads --max-size 10737418240
yc iam access-key create --service-account-name <SA_NAME>
```

Сохранить S3 access-key + secret как `YC_S3_KEY` / `YC_S3_SECRET`.

- [ ] **Step 7: Создать Container Registry**

```bash
yc container registry create --name proshli
```

Сохранить registry ID как `YC_REGISTRY_ID`.

- [ ] **Step 8: Создать service account для деплоя**

```bash
yc iam service-account create --name proshli-deployer
yc resource-manager folder add-access-binding <FOLDER_ID> \
  --role container-registry.admin \
  --subject serviceAccount:<SA_ID>
yc resource-manager folder add-access-binding <FOLDER_ID> \
  --role serverless.containers.editor \
  --subject serviceAccount:<SA_ID>
yc iam key create --service-account-name proshli-deployer -o yc-sa-key.json
```

`yc-sa-key.json` сохранить как GitHub Actions secret `YC_SA_JSON_KEY`.

---

## Task 0: Решение по переименованию репо jobskout → proshli

**Files:** изменения в Git-настройках, не в коде.

- [ ] **Step 1: Принять решение о моменте rename**

Варианты:
- (A) Переименовать GitHub-репо jobskout → proshli-ai сейчас, продолжить разработку в той же папке.
- (B) Оставить локальную папку `jobskout/` до конца Sprint 1, переименовать в Sprint 2.

Рекомендация: **(B)** — локальная папка остаётся `jobskout/`, GitHub-репо тоже остаётся `jobskout` до Sprint 2. В Sprint 2 делается одновременный rename: github remote, local folder, all bookmarks. Это снижает риск ошибок в Sprint 1, когда монорепо ещё нестабильно.

- [ ] **Step 2: Обновить README заголовок (намерение)**

Поправить `README.md`, заменить заголовок на `# Proshli (codename: jobskout)` и добавить блок:

```markdown
> **Бренд:** продукт ребрендируется в **Proshli**. Кодовое имя репо `jobskout` сохраняется до Sprint 2 ради стабильности Sprint 1 разработки.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: signal upcoming rebrand to Proshli"
```

---

## Task 1: Инициализировать Turborepo в корне

**Files:**
- Create: `package.json` (корень)
- Create: `turbo.json`
- Create: `pnpm-workspace.yaml`
- Create: `.npmrc`
- Modify: `.gitignore`

- [ ] **Step 1: Установить pnpm и turbo глобально**

```bash
npm install -g pnpm@11 turbo@latest
pnpm --version  # ожидается 11.x
turbo --version  # ожидается 2.x
```

- [ ] **Step 2: Создать корневой package.json**

```json
{
  "name": "proshli-monorepo",
  "version": "0.0.0",
  "private": true,
  "packageManager": "pnpm@11.1.2",
  "scripts": {
    "build": "turbo build",
    "dev": "turbo dev",
    "lint": "turbo lint",
    "test": "turbo test",
    "type-check": "turbo type-check",
    "format": "prettier --write \"**/*.{ts,tsx,md,json,yml}\"",
    "clean": "turbo clean && rm -rf node_modules"
  },
  "devDependencies": {
    "turbo": "^2.5.0",
    "prettier": "^3.3.3",
    "prettier-plugin-tailwindcss": "^0.6.8"
  }
}
```

- [ ] **Step 3: Создать pnpm-workspace.yaml**

```yaml
packages:
  - "apps/*"
  - "packages/*"
```

- [ ] **Step 4: Создать turbo.json**

```json
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": [".env", ".env.local"],
  "globalEnv": ["NODE_ENV", "SENTRY_DSN"],
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "!.next/cache/**", "dist/**", "storybook-static/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true,
      "dependsOn": ["^build"]
    },
    "lint": { "outputs": [] },
    "type-check": { "outputs": [], "dependsOn": ["^build"] },
    "test": { "outputs": ["coverage/**"], "dependsOn": ["^build"] },
    "clean": { "cache": false }
  }
}
```

- [ ] **Step 5: Создать .npmrc**

```
auto-install-peers=true
shamefully-hoist=false
strict-peer-dependencies=false
node-linker=isolated
```

- [ ] **Step 6: Обновить .gitignore**

Дописать в `.gitignore`:

```
# Turborepo
.turbo

# pnpm
node_modules/
.pnpm-store/

# Python venvs / uv
.venv/
__pycache__/
*.pyc
.python-version

# Coverage
coverage/
htmlcov/
.coverage

# IDE
.vscode/
.idea/

# Env files
.env
.env.local
.env.*.local
!.env.example

# Storybook
storybook-static/

# Yandex Cloud
yc-sa-key.json
```

- [ ] **Step 7: pnpm install + проверка**

```bash
cd C:/Users/Alex/Cursor/jobskout
pnpm install
pnpm turbo --version
```

Expected: `node_modules/` создан, turbo доступен.

- [ ] **Step 8: Commit**

```bash
git add package.json pnpm-workspace.yaml turbo.json .npmrc .gitignore pnpm-lock.yaml
git commit -m "feat(repo): initialize Turborepo monorepo with pnpm 11"
```

---

## Task 2: Переместить web → apps/web

**Files:**
- Move: `web/` → `apps/web/`
- Modify: `apps/web/package.json` (name, scripts)
- Create: `apps/web/.env.example`

- [ ] **Step 1: Создать apps/ и переместить web**

```bash
mkdir -p apps packages
git mv web apps/web
```

- [ ] **Step 2: Обновить apps/web/package.json**

```json
{
  "name": "@proshli/web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start --port 3000",
    "lint": "eslint",
    "type-check": "tsc --noEmit",
    "test": "playwright test",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "next": "16.2.1",
    "react": "19.2.4",
    "react-dom": "19.2.4"
  },
  "devDependencies": {
    "@playwright/test": "^1.58.2",
    "@tailwindcss/postcss": "^4",
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "eslint": "^9",
    "eslint-config-next": "16.2.1",
    "tailwindcss": "^4",
    "typescript": "^5"
  }
}
```

- [ ] **Step 3: Создать apps/web/.env.example**

```
# Public (NEXT_PUBLIC_*) — экспонируются в браузер
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SITE_URL=http://127.0.0.1:3000
NEXT_PUBLIC_SENTRY_DSN=
NEXT_PUBLIC_PLAUSIBLE_DOMAIN=staging.proshli.ru

# Server-only
SENTRY_AUTH_TOKEN=
```

- [ ] **Step 4: Прочитать AGENTS.md в apps/web**

```bash
cat apps/web/AGENTS.md
```

Если файл указывает на breaking changes Next.js 16, прочитать `apps/web/node_modules/next/dist/docs/` перед написанием Next-кода.

- [ ] **Step 5: Verify dev сервер работает**

```bash
pnpm install
pnpm --filter @proshli/web dev
```

Открыть http://127.0.0.1:3000 — должна отдаваться текущая стартовая страница без ошибок.

- [ ] **Step 6: Commit**

```bash
git add apps/web pnpm-lock.yaml
git commit -m "refactor(web): move into apps/web with @proshli/web scope"
```

---

## Task 3: Переместить backend → apps/api, мигрировать на uv

**Files:**
- Move: `backend/` → `apps/api/`
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/uv.lock` (генерируется)
- Delete: `apps/api/requirements.txt`
- Create: `apps/api/.env.example`

- [ ] **Step 1: Установить uv**

```bash
pip install uv
uv --version
```

Ожидается uv >= 0.4.

- [ ] **Step 2: Переместить backend в apps/api**

```bash
git mv backend apps/api
```

- [ ] **Step 3: Создать apps/api/pyproject.toml**

```toml
[project]
name = "proshli-api"
version = "0.1.0"
description = "Proshli backend API"
requires-python = ">=3.12,<3.13"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.35",
    "asyncpg>=0.29.0",
    "pgvector>=0.3.6",
    "alembic>=1.13.3",
    "pydantic[email]>=2.9.2",
    "pydantic-settings>=2.6.0",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "python-multipart>=0.0.12",
    "pypdf>=5.1.0",
    "httpx>=0.27.2",
    "sentry-sdk[fastapi]>=2.18.0",
    "structlog>=24.4.0",
    "redis>=5.2.0",
    "celery>=5.4.0",
    "feedparser>=6.0.11",
]

[dependency-groups]
dev = [
    "pytest>=8.3.3",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.7.0",
    "bandit>=1.8.0",
    "mypy>=1.13.0",
    "types-passlib",
    "types-python-jose",
]

[tool.uv]
package = false

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["app"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "C4", "UP", "ASYNC", "SIM"]
ignore = ["E501"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
```

- [ ] **Step 4: Создать apps/api/.env.example**

```
# Application
APP_ENV=development
APP_LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://proshli:proshli@localhost:5432/proshli

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Auth
JWT_SECRET=change-me-in-prod-please
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_TTL_MINUTES=60

# Bot
BOT_SERVICE_KEY=change-me-too

# Observability
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.1

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

- [ ] **Step 5: Сгенерировать lock и установить**

```bash
cd apps/api
uv sync --all-groups
cd ../..
```

Ожидается: `.venv` создан внутри `apps/api/`, все deps подтянуты, `uv.lock` сгенерирован.

- [ ] **Step 6: Удалить requirements.txt**

```bash
git rm apps/api/requirements.txt
```

- [ ] **Step 7: Commit**

```bash
git add apps/api/pyproject.toml apps/api/uv.lock apps/api/.env.example
git rm apps/api/requirements.txt
git commit -m "refactor(api): migrate to apps/api with uv + async stack"
```

---

## Task 4: Конвертировать backend на async SQLAlchemy

Существующий код использует sync SQLAlchemy + `psycopg2`. Конвертируем на async + asyncpg.

**Files:**
- Modify: `apps/api/app/db.py` (или эквивалент)
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/models.py` (только декларации — DeclarativeBase меняется минимально)
- Modify: все роуты, использующие Session → AsyncSession

- [ ] **Step 1: Прочитать текущую структуру**

```bash
ls apps/api/app/
```

Записать список модулей. Идентифицировать файл с DB engine/sessionmaker.

- [ ] **Step 2: Написать тест на async подключение**

Создать `apps/api/tests/test_db_connection.py`:

```python
import pytest
from sqlalchemy import text
from app.db import async_session_factory


@pytest.mark.asyncio
async def test_async_session_can_query():
    async with async_session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_pgvector_extension_available():
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        )
        assert result.scalar() == 1
```

- [ ] **Step 3: Запустить тест — должен упасть**

```bash
cd apps/api
uv run pytest tests/test_db_connection.py -v
```

Expected: FAIL — `async_session_factory` не существует.

- [ ] **Step 4: Создать новый async db.py**

`apps/api/app/db.py`:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 5: Создать config.py с pydantic-settings**

`apps/api/app/config.py`:

```python
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = Field(default="development")
    app_log_level: str = Field(default="INFO")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_ttl_minutes: int = 60

    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.1

    cors_allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

- [ ] **Step 6: Поднять локальный Postgres + pgvector для тестов**

```bash
docker run -d --name proshli-pg -p 5432:5432 \
  -e POSTGRES_USER=proshli -e POSTGRES_PASSWORD=proshli \
  -e POSTGRES_DB=proshli pgvector/pgvector:pg16
docker exec -it proshli-pg psql -U proshli -d proshli -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

- [ ] **Step 7: Запустить тесты — должны пройти**

```bash
cd apps/api
cp .env.example .env
uv run pytest tests/test_db_connection.py -v
```

Expected: PASS оба теста.

- [ ] **Step 8: Конвертировать существующие routes на AsyncSession**

Для каждого файла в `apps/api/app/routes/` (или `routers/`):
- Изменить импорт `Session` → `AsyncSession`
- Заменить `Depends(get_db)` на новую async-зависимость
- Заменить sync вызовы (`db.query(...)`) на async (`(await db.execute(select(...))).scalars()`)

Шаблон новой зависимости (добавить в `app/deps.py`):

```python
from collections.abc import AsyncIterator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import async_session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


DbSession = Depends(get_db)
```

Конвертация — отдельная подзадача для каждого роута. На этом шаге зафиксировать список роутов и пройтись по ним один за одним, проверяя `pytest` после каждого.

- [ ] **Step 9: Commit после конвертации каждого роута**

```bash
git add apps/api/app/routes/<file>.py apps/api/tests/<test>.py
git commit -m "refactor(api): convert <route> to async SQLAlchemy"
```

---

## Task 5: Alembic — baseline + pgvector + начальные таблицы

**Files:**
- Modify: `apps/api/alembic/env.py` (async engine)
- Create: `apps/api/alembic/versions/<hash>_pgvector_baseline.py`

- [ ] **Step 1: Конвертировать alembic env.py на async**

`apps/api/alembic/env.py` (целиком заменить):

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.db import Base
from app import models  # noqa: F401 — регистрирует модели

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


run_migrations_online()
```

- [ ] **Step 2: Создать миграцию pgvector**

```bash
cd apps/api
uv run alembic revision -m "enable pgvector extension"
```

В сгенерированный файл вписать:

```python
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector;")
```

- [ ] **Step 3: Прогнать миграцию**

```bash
uv run alembic upgrade head
```

Expected: `vector` extension установлен.

- [ ] **Step 4: Smoke-тест pgvector**

```bash
docker exec -it proshli-pg psql -U proshli -d proshli \
  -c "SELECT '[1,2,3]'::vector <-> '[3,2,1]'::vector;"
```

Expected: число (косинусная дистанция).

- [ ] **Step 5: Commit**

```bash
git add apps/api/alembic
git commit -m "feat(api): async alembic + enable pgvector extension"
```

---

## Task 6: Переместить bot → apps/tgbot

**Files:**
- Move: `bot/` → `apps/tgbot/`
- Create: `apps/tgbot/pyproject.toml`

- [ ] **Step 1: Переместить**

```bash
git mv bot apps/tgbot
```

- [ ] **Step 2: Создать pyproject.toml**

`apps/tgbot/pyproject.toml`:

```toml
[project]
name = "proshli-tgbot"
version = "0.1.0"
description = "Proshli Telegram bot"
requires-python = ">=3.12,<3.13"
dependencies = [
    "aiogram>=3.14.0",
    "httpx>=0.27.2",
    "pydantic-settings>=2.6.0",
    "structlog>=24.4.0",
    "telethon>=1.37.0",
    "sentry-sdk>=2.18.0",
]

[dependency-groups]
dev = ["pytest>=8.3.3", "ruff>=0.7.0", "mypy>=1.13.0"]

[tool.uv]
package = false
```

- [ ] **Step 3: Установить**

```bash
cd apps/tgbot && uv sync --all-groups && cd ../..
```

- [ ] **Step 4: Commit**

```bash
git add apps/tgbot
git commit -m "refactor(tgbot): move into apps/tgbot"
```

---

## Task 7: Создать apps/workers (Celery stub)

**Files:**
- Create: `apps/workers/pyproject.toml`
- Create: `apps/workers/workers/__init__.py`
- Create: `apps/workers/workers/celery_app.py`
- Create: `apps/workers/workers/tasks/parse_hh.py`
- Create: `apps/workers/tests/test_celery_smoke.py`

- [ ] **Step 1: Создать структуру**

```bash
mkdir -p apps/workers/workers/tasks apps/workers/tests
touch apps/workers/workers/__init__.py apps/workers/workers/tasks/__init__.py
```

- [ ] **Step 2: pyproject.toml**

`apps/workers/pyproject.toml`:

```toml
[project]
name = "proshli-workers"
version = "0.1.0"
description = "Proshli background workers (Celery)"
requires-python = ">=3.12,<3.13"
dependencies = [
    "celery[redis]>=5.4.0",
    "redis>=5.2.0",
    "sqlalchemy[asyncio]>=2.0.35",
    "asyncpg>=0.29.0",
    "pgvector>=0.3.6",
    "httpx>=0.27.2",
    "pydantic-settings>=2.6.0",
    "structlog>=24.4.0",
    "sentry-sdk[celery]>=2.18.0",
]

[dependency-groups]
dev = ["pytest>=8.3.3", "ruff>=0.7.0", "mypy>=1.13.0"]

[tool.uv]
package = false
```

- [ ] **Step 3: Celery app**

`apps/workers/workers/celery_app.py`:

```python
import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery_app = Celery(
    "proshli",
    broker=REDIS_URL,
    backend=RESULT_BACKEND,
    include=[
        "workers.tasks.parse_hh",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "parse-hh-every-15-min": {
        "task": "workers.tasks.parse_hh.parse_hh_recent",
        "schedule": crontab(minute="*/15"),
    },
}
```

- [ ] **Step 4: Stub task**

`apps/workers/workers/tasks/parse_hh.py`:

```python
import structlog

from workers.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def parse_hh_recent(self) -> int:
    """Parse recent HH vacancies. Returns number of inserted rows."""
    log.info("parse_hh_recent.start")
    # Реальная реализация — Sprint 2.
    return 0
```

- [ ] **Step 5: Smoke-тест**

`apps/workers/tests/test_celery_smoke.py`:

```python
from workers.celery_app import celery_app
from workers.tasks.parse_hh import parse_hh_recent


def test_celery_app_exists():
    assert celery_app is not None
    assert celery_app.main == "proshli"


def test_parse_hh_task_registered():
    assert "workers.tasks.parse_hh.parse_hh_recent" in celery_app.tasks


def test_parse_hh_runs_locally():
    result = parse_hh_recent.apply().get()
    assert result == 0
```

- [ ] **Step 6: Прогнать тесты**

```bash
cd apps/workers
uv sync --all-groups
uv run pytest tests/test_celery_smoke.py -v
```

Expected: 3 теста PASS.

- [ ] **Step 7: Commit**

```bash
cd ../..
git add apps/workers
git commit -m "feat(workers): scaffold Celery app with parse_hh stub task"
```

---

## Task 8: packages/config — общие eslint, prettier, tsconfig

**Files:**
- Create: `packages/config/package.json`
- Create: `packages/config/eslint/base.mjs`
- Create: `packages/config/eslint/next.mjs`
- Create: `packages/config/tsconfig/base.json`
- Create: `packages/config/tsconfig/nextjs.json`
- Create: `packages/config/prettier/index.mjs`

- [ ] **Step 1: Создать package.json**

`packages/config/package.json`:

```json
{
  "name": "@proshli/config",
  "version": "0.0.0",
  "private": true,
  "exports": {
    "./eslint/base": "./eslint/base.mjs",
    "./eslint/next": "./eslint/next.mjs",
    "./tsconfig/base": "./tsconfig/base.json",
    "./tsconfig/nextjs": "./tsconfig/nextjs.json",
    "./prettier": "./prettier/index.mjs"
  },
  "devDependencies": {
    "eslint": "^9",
    "eslint-config-next": "16.2.1",
    "typescript": "^5"
  }
}
```

- [ ] **Step 2: ESLint base config**

`packages/config/eslint/base.mjs`:

```javascript
import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    rules: {
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    },
  },
];
```

- [ ] **Step 3: ESLint next config**

`packages/config/eslint/next.mjs`:

```javascript
import baseConfig from "./base.mjs";
import nextPlugin from "eslint-config-next";

export default [
  ...baseConfig,
  ...nextPlugin,
];
```

- [ ] **Step 4: TSConfig base**

`packages/config/tsconfig/base.json`:

```json
{
  "$schema": "https://json.schemastore.org/tsconfig",
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "isolatedModules": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true
  }
}
```

- [ ] **Step 5: TSConfig nextjs**

`packages/config/tsconfig/nextjs.json`:

```json
{
  "extends": "./base.json",
  "compilerOptions": {
    "lib": ["DOM", "DOM.Iterable", "ES2022"],
    "module": "ESNext",
    "jsx": "preserve",
    "allowJs": true,
    "noEmit": true,
    "incremental": true,
    "plugins": [{ "name": "next" }]
  }
}
```

- [ ] **Step 6: Prettier config**

`packages/config/prettier/index.mjs`:

```javascript
/** @type {import("prettier").Config} */
export default {
  semi: true,
  singleQuote: false,
  trailingComma: "all",
  printWidth: 100,
  plugins: ["prettier-plugin-tailwindcss"],
};
```

- [ ] **Step 7: Применить в apps/web**

В `apps/web/tsconfig.json` — extends на пакет (заменить блок compilerOptions):

```json
{
  "extends": "@proshli/config/tsconfig/nextjs",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

В `apps/web/package.json` добавить в devDependencies: `"@proshli/config": "workspace:*"`.

- [ ] **Step 8: pnpm install + type-check**

```bash
pnpm install
pnpm --filter @proshli/web type-check
```

Expected: type-check PASS.

- [ ] **Step 9: Commit**

```bash
git add packages/config apps/web/tsconfig.json apps/web/package.json pnpm-lock.yaml
git commit -m "feat(config): share eslint/tsconfig/prettier via @proshli/config"
```

---

## Task 9: packages/shared-types — TypeScript типы общих доменных объектов

**Files:**
- Create: `packages/shared-types/package.json`
- Create: `packages/shared-types/src/index.ts`
- Create: `packages/shared-types/src/vacancy.ts`
- Create: `packages/shared-types/src/user.ts`
- Create: `packages/shared-types/src/application.ts`
- Create: `packages/shared-types/tsconfig.json`

- [ ] **Step 1: package.json**

`packages/shared-types/package.json`:

```json
{
  "name": "@proshli/shared-types",
  "version": "0.0.0",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  },
  "scripts": {
    "type-check": "tsc --noEmit",
    "lint": "echo 'no source to lint yet'"
  },
  "devDependencies": {
    "@proshli/config": "workspace:*",
    "typescript": "^5"
  }
}
```

- [ ] **Step 2: tsconfig.json**

```json
{
  "extends": "@proshli/config/tsconfig/base",
  "include": ["src/**/*"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Типы Vacancy**

`packages/shared-types/src/vacancy.ts`:

```typescript
export type VacancySource = "hh" | "habr_career" | "telegram" | "corp_site";

export type RemoteType = "remote" | "hybrid" | "office";

export interface SalaryRange {
  min: number | null;
  max: number | null;
  currency: "RUB" | "USD" | "EUR" | "KZT" | "AMD" | "GEL";
}

export interface Vacancy {
  id: string;
  fingerprint: string;
  title: string;
  companyId: string;
  companyName: string;
  salary: SalaryRange;
  location: string | null;
  remoteType: RemoteType;
  description: string;
  requirements: string[];
  publishedAt: string;
  responsesCount: number | null;
  sources: Array<{
    source: VacancySource;
    sourceId: string;
    url: string;
  }>;
  ghostScore: number;
  status: "active" | "archived" | "hidden";
}

export interface VacancyMatch {
  vacancyId: string;
  userId: string;
  matchPercent: number;
  hireChanceScore: number;
  scoreBreakdown: {
    match: number;
    ageFactor: number;
    responsesFactor: number;
    activityFactor: number;
  };
}
```

- [ ] **Step 4: Типы User**

`packages/shared-types/src/user.ts`:

```typescript
export type SubscriptionTier = "free" | "pro" | "premium";

export type Locale = "ru" | "en";

export interface User {
  id: string;
  email: string;
  telegramId: number | null;
  locale: Locale;
  subscriptionTier: SubscriptionTier;
  createdAt: string;
}

export interface UserProfile {
  userId: string;
  fullName: string;
  desiredSalary: { min: number; max: number; currency: "RUB" | "USD" } | null;
  preferredLocations: string[];
  skills: string[];
  stealthCompanies: string[];
}
```

- [ ] **Step 5: Типы Application**

`packages/shared-types/src/application.ts`:

```typescript
export type ApplicationStatus =
  | "draft"
  | "sent"
  | "screening"
  | "interview"
  | "offer"
  | "rejected";

export interface Application {
  id: string;
  userId: string;
  vacancyId: string;
  status: ApplicationStatus;
  createdAt: string;
  lastEventAt: string;
  resumeVersionId: string | null;
  coverLetterText: string | null;
}

export interface ApplicationEvent {
  id: string;
  applicationId: string;
  eventType: "status_changed" | "follow_up_sent" | "email_received";
  payload: Record<string, unknown>;
  createdAt: string;
}
```

- [ ] **Step 6: index.ts**

`packages/shared-types/src/index.ts`:

```typescript
export * from "./vacancy";
export * from "./user";
export * from "./application";
```

- [ ] **Step 7: Подключить в apps/web**

В `apps/web/package.json` добавить:

```json
"dependencies": {
  ...
  "@proshli/shared-types": "workspace:*"
}
```

- [ ] **Step 8: type-check**

```bash
pnpm install
pnpm --filter @proshli/shared-types type-check
pnpm --filter @proshli/web type-check
```

Expected: оба PASS.

- [ ] **Step 9: Commit**

```bash
git add packages/shared-types apps/web/package.json pnpm-lock.yaml
git commit -m "feat(shared-types): domain types for Vacancy, User, Application"
```

---

## Task 10: packages/ui — shadcn/ui компоненты + дизайн-токены

**Files:**
- Create: `packages/ui/package.json`
- Create: `packages/ui/tsconfig.json`
- Create: `packages/ui/src/index.ts`
- Create: `packages/ui/src/styles/globals.css` (дизайн-токены, темы)
- Create: `packages/ui/src/lib/utils.ts` (cn helper)
- Create: `packages/ui/src/components/button.tsx`
- Create: `packages/ui/src/components/card.tsx`
- Create: `packages/ui/src/components/badge.tsx`
- Create: `packages/ui/src/components/skeleton.tsx`
- Create: `packages/ui/src/components/theme-provider.tsx`

- [ ] **Step 1: package.json**

`packages/ui/package.json`:

```json
{
  "name": "@proshli/ui",
  "version": "0.0.0",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts",
    "./styles": "./src/styles/globals.css"
  },
  "scripts": {
    "type-check": "tsc --noEmit",
    "lint": "echo 'lint placeholder'"
  },
  "dependencies": {
    "@radix-ui/react-slot": "^1.1.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "framer-motion": "^11.11.0",
    "lucide-react": "^0.460.0",
    "next-themes": "^0.4.3",
    "tailwind-merge": "^2.5.4"
  },
  "peerDependencies": {
    "react": "^19",
    "react-dom": "^19"
  },
  "devDependencies": {
    "@proshli/config": "workspace:*",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "typescript": "^5"
  }
}
```

- [ ] **Step 2: tsconfig.json**

```json
{
  "extends": "@proshli/config/tsconfig/base",
  "compilerOptions": {
    "lib": ["DOM", "ES2022"],
    "jsx": "preserve",
    "noEmit": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Дизайн-токены и темы**

`packages/ui/src/styles/globals.css`:

```css
@import "tailwindcss";

@layer base {
  :root {
    /* Spacing scale (8pt grid) */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-6: 24px;
    --space-8: 32px;
    --space-12: 48px;
    --space-16: 64px;
    --space-24: 96px;

    /* Radius */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-xl: 16px;

    /* Light theme colors (OKLCH) */
    --color-bg: oklch(0.98 0.005 240);
    --color-bg-elevated: oklch(1 0 0);
    --color-fg: oklch(0.18 0.015 240);
    --color-fg-muted: oklch(0.45 0.015 240);
    --color-border: oklch(0.9 0.005 240);
    --color-primary: oklch(0.55 0.18 256);
    --color-primary-fg: oklch(1 0 0);
    --color-accent: oklch(0.7 0.15 200);
    --color-destructive: oklch(0.55 0.22 27);
    --color-warning: oklch(0.7 0.18 85);
    --color-success: oklch(0.55 0.15 145);
  }

  .dark,
  [data-theme="dark"] {
    --color-bg: oklch(0.16 0.01 240);
    --color-bg-elevated: oklch(0.21 0.015 240);
    --color-fg: oklch(0.95 0.005 240);
    --color-fg-muted: oklch(0.65 0.01 240);
    --color-border: oklch(0.28 0.015 240);
    --color-primary: oklch(0.72 0.18 256);
    --color-primary-fg: oklch(0.15 0 0);
    --color-accent: oklch(0.75 0.15 200);
    --color-destructive: oklch(0.65 0.22 27);
    --color-warning: oklch(0.78 0.18 85);
    --color-success: oklch(0.65 0.15 145);
  }

  [data-theme="oled"] {
    --color-bg: oklch(0 0 0);
    --color-bg-elevated: oklch(0.12 0.01 240);
    --color-fg: oklch(0.96 0.005 240);
    --color-fg-muted: oklch(0.65 0.01 240);
    --color-border: oklch(0.22 0.015 240);
    --color-primary: oklch(0.75 0.18 256);
    --color-primary-fg: oklch(0.05 0 0);
    --color-accent: oklch(0.78 0.15 200);
    --color-destructive: oklch(0.65 0.22 27);
    --color-warning: oklch(0.78 0.18 85);
    --color-success: oklch(0.65 0.15 145);
  }

  * {
    border-color: var(--color-border);
  }

  body {
    background: var(--color-bg);
    color: var(--color-fg);
    font-family: "Inter", system-ui, sans-serif;
    font-feature-settings: "cv02", "cv03", "cv04", "cv11";
  }

  h1, h2, h3, h4 {
    font-family: "Manrope", "Inter", sans-serif;
    letter-spacing: -0.02em;
  }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }
}
```

- [ ] **Step 4: utils.ts**

`packages/ui/src/lib/utils.ts`:

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 5: Button component**

`packages/ui/src/components/button.tsx`:

```tsx
"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-md)] text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--color-primary)] text-[var(--color-primary-fg)] hover:opacity-90",
        secondary:
          "bg-[var(--color-bg-elevated)] text-[var(--color-fg)] hover:opacity-90 border",
        ghost: "hover:bg-[var(--color-bg-elevated)]",
        destructive:
          "bg-[var(--color-destructive)] text-white hover:opacity-90",
        outline: "border bg-transparent hover:bg-[var(--color-bg-elevated)]",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 px-3 text-xs",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { buttonVariants };
```

- [ ] **Step 6: Card, Badge, Skeleton — минимальные**

`packages/ui/src/components/card.tsx`:

```tsx
import * as React from "react";
import { cn } from "../lib/utils";

export const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-[var(--radius-lg)] border bg-[var(--color-bg-elevated)] shadow-sm",
      className,
    )}
    {...props}
  />
));
Card.displayName = "Card";

export const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6", className)} {...props} />
));
CardContent.displayName = "CardContent";
```

`packages/ui/src/components/badge.tsx`:

```tsx
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-[var(--color-primary)] text-[var(--color-primary-fg)]",
        secondary: "bg-[var(--color-bg-elevated)] border",
        success: "bg-[var(--color-success)] text-white",
        warning: "bg-[var(--color-warning)] text-black",
        destructive: "bg-[var(--color-destructive)] text-white",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
```

`packages/ui/src/components/skeleton.tsx`:

```tsx
import { cn } from "../lib/utils";

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-[var(--radius-md)] bg-[var(--color-bg-elevated)]",
        className,
      )}
      {...props}
    />
  );
}
```

- [ ] **Step 7: ThemeProvider**

`packages/ui/src/components/theme-provider.tsx`:

```tsx
"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

type Props = ComponentProps<typeof NextThemesProvider>;

export function ThemeProvider({ children, ...props }: Props) {
  return (
    <NextThemesProvider
      attribute="data-theme"
      defaultTheme="system"
      enableSystem
      themes={["light", "dark", "oled", "system"]}
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}
```

- [ ] **Step 8: index.ts**

`packages/ui/src/index.ts`:

```typescript
export { Button, buttonVariants, type ButtonProps } from "./components/button";
export { Card, CardContent } from "./components/card";
export { Badge, type BadgeProps } from "./components/badge";
export { Skeleton } from "./components/skeleton";
export { ThemeProvider } from "./components/theme-provider";
export { cn } from "./lib/utils";
```

- [ ] **Step 9: pnpm install + type-check**

```bash
pnpm install
pnpm --filter @proshli/ui type-check
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add packages/ui pnpm-lock.yaml
git commit -m "feat(ui): scaffold @proshli/ui with tokens, themes, base components"
```

---

## Task 11: Подключить @proshli/ui в apps/web + добавить next-themes + next-intl

**Files:**
- Modify: `apps/web/package.json`
- Modify: `apps/web/app/layout.tsx`
- Modify: `apps/web/app/globals.css` (импорт из @proshli/ui)
- Create: `apps/web/messages/ru.json`
- Create: `apps/web/messages/en.json`
- Create: `apps/web/i18n.ts`
- Modify: `apps/web/next.config.ts`
- Create: `apps/web/middleware.ts`
- Modify: `apps/web/app/[locale]/layout.tsx` (если App Router требует)

- [ ] **Step 1: Установить зависимости**

В `apps/web/package.json` добавить:

```json
"dependencies": {
  ...
  "@proshli/ui": "workspace:*",
  "@proshli/shared-types": "workspace:*",
  "next-intl": "^3.25.0"
}
```

```bash
pnpm install
```

- [ ] **Step 2: i18n config**

`apps/web/i18n.ts`:

```typescript
import { getRequestConfig } from "next-intl/server";
import { notFound } from "next/navigation";

export const locales = ["ru", "en"] as const;
export const defaultLocale = "ru" as const;
export type Locale = (typeof locales)[number];

export default getRequestConfig(async ({ requestLocale }) => {
  const locale = (await requestLocale) ?? defaultLocale;
  if (!locales.includes(locale as Locale)) notFound();
  return {
    locale,
    messages: (await import(`./messages/${locale}.json`)).default,
  };
});
```

- [ ] **Step 3: Сообщения RU/EN**

`apps/web/messages/ru.json`:

```json
{
  "common": {
    "appName": "Proshli",
    "tagline": "Отклик, который услышат"
  },
  "nav": {
    "vacancies": "Вакансии",
    "applications": "Отклики",
    "profile": "Профиль",
    "settings": "Настройки"
  },
  "theme": {
    "light": "Светлая",
    "dark": "Тёмная",
    "oled": "OLED",
    "system": "Системная"
  }
}
```

`apps/web/messages/en.json`:

```json
{
  "common": {
    "appName": "Proshli",
    "tagline": "Applications that get a real response"
  },
  "nav": {
    "vacancies": "Vacancies",
    "applications": "Applications",
    "profile": "Profile",
    "settings": "Settings"
  },
  "theme": {
    "light": "Light",
    "dark": "Dark",
    "oled": "OLED",
    "system": "System"
  }
}
```

- [ ] **Step 4: next.config.ts с next-intl plugin**

`apps/web/next.config.ts` (заменить целиком):

```typescript
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n.ts");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@proshli/ui", "@proshli/shared-types"],
  experimental: {
    typedRoutes: true,
  },
};

export default withNextIntl(nextConfig);
```

- [ ] **Step 5: middleware.ts**

`apps/web/middleware.ts`:

```typescript
import createMiddleware from "next-intl/middleware";
import { locales, defaultLocale } from "./i18n";

export default createMiddleware({
  locales,
  defaultLocale,
  localePrefix: "always",
});

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
```

- [ ] **Step 6: Структура /[locale]/**

Перенести существующий root layout/page в `apps/web/app/[locale]/`:

```bash
mkdir -p apps/web/app/[locale]
git mv apps/web/app/layout.tsx apps/web/app/[locale]/layout.tsx
git mv apps/web/app/page.tsx apps/web/app/[locale]/page.tsx
```

- [ ] **Step 7: Обновить layout с ThemeProvider + NextIntl**

`apps/web/app/[locale]/layout.tsx`:

```tsx
import "@proshli/ui/styles";
import "../globals.css";
import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { ThemeProvider } from "@proshli/ui";
import { Inter, Manrope } from "next/font/google";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
});

const manrope = Manrope({
  subsets: ["latin", "cyrillic"],
  variable: "--font-manrope",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Proshli",
  description: "Proshli that gets a real response",
};

export default async function RootLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const messages = await getMessages();
  return (
    <html lang={locale} suppressHydrationWarning className={`${inter.variable} ${manrope.variable}`}>
      <body className="font-sans antialiased">
        <ThemeProvider>
          <NextIntlClientProvider locale={locale} messages={messages}>
            {children}
          </NextIntlClientProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 8: Обновить главную страницу**

`apps/web/app/[locale]/page.tsx`:

```tsx
import { useTranslations } from "next-intl";
import { Button, Card, CardContent, Badge } from "@proshli/ui";

export default function HomePage() {
  const t = useTranslations("common");
  return (
    <main className="min-h-dvh flex items-center justify-center p-8">
      <Card className="max-w-xl w-full">
        <CardContent className="flex flex-col gap-6 items-center text-center">
          <Badge variant="success">staging</Badge>
          <h1 className="text-5xl font-bold">{t("appName")}</h1>
          <p className="text-lg text-[var(--color-fg-muted)]">{t("tagline")}</p>
          <div className="flex gap-3">
            <Button>Get started</Button>
            <Button variant="secondary">Learn more</Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
```

- [ ] **Step 9: Тест в dev**

```bash
pnpm --filter @proshli/web dev
```

Открыть:
- http://127.0.0.1:3000 — редирект на /ru
- http://127.0.0.1:3000/ru — русская страница
- http://127.0.0.1:3000/en — английская страница

Проверить переключение тем через devtools: `document.documentElement.setAttribute('data-theme', 'dark')` — фон должен потемнеть.

- [ ] **Step 10: Commit**

```bash
git add apps/web pnpm-lock.yaml
git commit -m "feat(web): wire @proshli/ui, themes, next-intl (ru/en)"
```

---

## Task 12: Storybook в packages/ui

**Files:**
- Create: `packages/ui/.storybook/main.ts`
- Create: `packages/ui/.storybook/preview.ts`
- Create: `packages/ui/src/components/button.stories.tsx`
- Create: `packages/ui/src/components/card.stories.tsx`
- Create: `packages/ui/src/components/badge.stories.tsx`

- [ ] **Step 1: Установить storybook**

```bash
cd packages/ui
pnpm dlx storybook@latest init --type react_vite --no-dev
cd ../..
pnpm install
```

- [ ] **Step 2: Конфиг .storybook/main.ts**

`packages/ui/.storybook/main.ts`:

```typescript
import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../src/**/*.stories.@(ts|tsx)"],
  addons: [
    "@storybook/addon-essentials",
    "@storybook/addon-themes",
    "@storybook/addon-a11y",
  ],
  framework: { name: "@storybook/react-vite", options: {} },
  typescript: { check: false },
};

export default config;
```

- [ ] **Step 3: preview.ts**

`packages/ui/.storybook/preview.ts`:

```typescript
import type { Preview } from "@storybook/react";
import { withThemeByDataAttribute } from "@storybook/addon-themes";
import "../src/styles/globals.css";

const preview: Preview = {
  parameters: {
    backgrounds: { default: "app" },
    controls: { matchers: { color: /(background|color)$/i, date: /Date$/i } },
  },
  decorators: [
    withThemeByDataAttribute({
      themes: { light: "light", dark: "dark", oled: "oled" },
      defaultTheme: "light",
      attributeName: "data-theme",
    }),
  ],
};

export default preview;
```

- [ ] **Step 4: Button story**

`packages/ui/src/components/button.stories.tsx`:

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "./button";

const meta: Meta<typeof Button> = {
  title: "Primitives/Button",
  component: Button,
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "secondary", "ghost", "destructive", "outline"],
    },
    size: { control: "select", options: ["default", "sm", "lg", "icon"] },
  },
};
export default meta;

type Story = StoryObj<typeof Button>;

export const Default: Story = { args: { children: "Button" } };
export const Secondary: Story = {
  args: { variant: "secondary", children: "Secondary" },
};
export const Destructive: Story = {
  args: { variant: "destructive", children: "Delete" },
};
export const AllSizes: Story = {
  render: () => (
    <div className="flex items-center gap-3">
      <Button size="sm">Small</Button>
      <Button>Default</Button>
      <Button size="lg">Large</Button>
    </div>
  ),
};
```

- [ ] **Step 5: Card + Badge stories** (по аналогии — короткие)

`packages/ui/src/components/card.stories.tsx`:

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Card, CardContent } from "./card";

const meta: Meta<typeof Card> = { title: "Primitives/Card", component: Card };
export default meta;

export const Default: StoryObj<typeof Card> = {
  render: () => (
    <Card className="max-w-md">
      <CardContent>
        <h2 className="text-xl font-semibold mb-2">Card title</h2>
        <p>This is card content.</p>
      </CardContent>
    </Card>
  ),
};
```

`packages/ui/src/components/badge.stories.tsx`:

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "./badge";

const meta: Meta<typeof Badge> = { title: "Primitives/Badge", component: Badge };
export default meta;

export const AllVariants: StoryObj<typeof Badge> = {
  render: () => (
    <div className="flex gap-2">
      <Badge>Default</Badge>
      <Badge variant="secondary">Secondary</Badge>
      <Badge variant="success">Success</Badge>
      <Badge variant="warning">Warning</Badge>
      <Badge variant="destructive">Error</Badge>
    </div>
  ),
};
```

- [ ] **Step 6: Запустить Storybook**

```bash
pnpm --filter @proshli/ui storybook
```

Открыть http://localhost:6006 — увидеть Button / Card / Badge stories в трёх темах.

- [ ] **Step 7: Добавить scripts в packages/ui/package.json**

```json
"scripts": {
  "type-check": "tsc --noEmit",
  "storybook": "storybook dev -p 6006",
  "build-storybook": "storybook build"
}
```

- [ ] **Step 8: Commit**

```bash
git add packages/ui pnpm-lock.yaml
git commit -m "feat(ui): Storybook with theme switcher + stories for primitives"
```

---

## Task 13: API skeleton — health, structured logging, sentry

**Files:**
- Create: `apps/api/app/observability.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/app/routes/health.py`
- Create: `apps/api/tests/test_health.py`

- [ ] **Step 1: Написать тест health**

`apps/api/tests/test_health.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_liveness():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_checks_db():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
```

- [ ] **Step 2: Запустить — FAIL**

```bash
cd apps/api
uv run pytest tests/test_health.py -v
```

Expected: FAIL.

- [ ] **Step 3: observability.py — structlog + sentry**

`apps/api/app/observability.py`:

```python
import logging
import sys

import sentry_sdk
import structlog
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.config import settings


def configure_observability() -> None:
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            integrations=[FastApiIntegration()],
            send_default_pii=False,
        )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.app_log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            (
                structlog.dev.ConsoleRenderer()
                if settings.app_env == "development"
                else structlog.processors.JSONRenderer()
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.app_log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

- [ ] **Step 4: Health route**

`apps/api/app/routes/health.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict:
    checks: dict[str, str] = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"fail: {exc}"
    status = "ok" if all(v == "ok" for v in checks.values()) else "fail"
    return {"status": status, "checks": checks}
```

- [ ] **Step 5: main.py — собрать app**

`apps/api/app/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import settings
from app.observability import configure_observability
from app.routes import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_observability()
    log = structlog.get_logger()
    log.info("api.startup", env=settings.app_env)
    yield
    log.info("api.shutdown")


app = FastAPI(
    title="Proshli API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "proshli-api", "version": "0.1.0"}
```

- [ ] **Step 6: Запустить тесты — должны пройти**

```bash
cd apps/api
uv run pytest tests/test_health.py -v
```

Expected: 2 PASS.

- [ ] **Step 7: Запустить uvicorn локально**

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Открыть:
- http://127.0.0.1:8000/health/live → `{"status":"ok"}`
- http://127.0.0.1:8000/health/ready → проверяет БД
- http://127.0.0.1:8000/docs → Swagger UI

- [ ] **Step 8: Commit**

```bash
cd ../..
git add apps/api
git commit -m "feat(api): health endpoints + structlog + sentry integration"
```

---

## Task 14: docker-compose.dev.yml — локальная разработка одной командой

**Files:**
- Modify/Create: `docker-compose.yml` (заменить старый)
- Create: `apps/api/Dockerfile`
- Create: `apps/web/Dockerfile`
- Create: `apps/workers/Dockerfile`

- [ ] **Step 1: Удалить старый docker-compose.yml/.prod.yml**

```bash
git rm docker-compose.yml docker-compose.prod.yml
```

- [ ] **Step 2: Новый docker-compose.yml для dev**

`docker-compose.yml`:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: proshli
      POSTGRES_PASSWORD: proshli
      POSTGRES_DB: proshli
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U proshli"]
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  meilisearch:
    image: getmeili/meilisearch:v1.11
    environment:
      MEILI_ENV: development
      MEILI_MASTER_KEY: dev-master-key
    ports:
      - "7700:7700"
    volumes:
      - meili_data:/meili_data

volumes:
  pg_data:
  redis_data:
  meili_data:
```

- [ ] **Step 3: apps/api/Dockerfile**

`apps/api/Dockerfile`:

```dockerfile
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

RUN pip install --no-cache-dir uv==0.4.30

FROM base AS builder
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev

FROM base AS runtime
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY apps/api/app ./app
COPY apps/api/alembic ./alembic
COPY apps/api/alembic.ini ./

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health/live || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: apps/web/Dockerfile**

`apps/web/Dockerfile`:

```dockerfile
FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@11.1.2 --activate

WORKDIR /app

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/ui/package.json ./packages/ui/
COPY packages/shared-types/package.json ./packages/shared-types/
COPY packages/config/package.json ./packages/config/
RUN pnpm install --frozen-lockfile

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules
COPY . .
RUN pnpm --filter @proshli/web build

FROM base AS runtime
ENV NODE_ENV=production
COPY --from=builder /app/apps/web/.next ./.next
COPY --from=builder /app/apps/web/public ./public
COPY --from=builder /app/apps/web/package.json ./package.json
COPY --from=deps /app/apps/web/node_modules ./node_modules
EXPOSE 3000
CMD ["node_modules/.bin/next", "start", "-p", "3000"]
```

- [ ] **Step 5: apps/workers/Dockerfile**

Аналогично api, CMD: `celery -A workers.celery_app worker --loglevel=info`.

```dockerfile
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN pip install --no-cache-dir uv==0.4.30

COPY apps/workers/pyproject.toml apps/workers/uv.lock ./
RUN uv sync --frozen --no-dev

COPY apps/workers/workers ./workers

ENV PATH="/app/.venv/bin:$PATH"
CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
```

- [ ] **Step 6: Прогнать compose up**

```bash
docker compose up -d postgres redis meilisearch
docker compose ps
```

Expected: 3 контейнера healthy.

- [ ] **Step 7: Smoke-тест — api + web запускаются**

В двух разных терминалах:

```bash
# Terminal 1
cd apps/api && uv run uvicorn app.main:app --reload

# Terminal 2
pnpm --filter @proshli/web dev
```

Открыть http://127.0.0.1:3000/ru — рабочий веб. Открыть http://127.0.0.1:8000/health/ready — `database: ok`.

- [ ] **Step 8: Commit**

```bash
git add docker-compose.yml apps/*/Dockerfile
git rm docker-compose.prod.yml
git commit -m "feat(infra): docker-compose.dev + Dockerfiles for api/web/workers"
```

---

## Task 15: GitHub Actions — lint + type-check workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Workflow file**

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  lint-and-typecheck-web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "pnpm"
      - run: pnpm install --frozen-lockfile
      - run: pnpm turbo lint type-check

  lint-and-test-api:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: proshli
          POSTGRES_PASSWORD: proshli
          POSTGRES_DB: proshli
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv==0.4.30
      - working-directory: apps/api
        run: uv sync --all-groups
      - working-directory: apps/api
        env:
          DATABASE_URL: postgresql+asyncpg://proshli:proshli@localhost:5432/proshli
          JWT_SECRET: ci-only-secret
        run: |
          uv run alembic upgrade head
          uv run ruff check .
          uv run pytest -v --cov=app --cov-report=term-missing

  lint-and-test-workers:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv==0.4.30
      - working-directory: apps/workers
        run: |
          uv sync --all-groups
          uv run ruff check .
          uv run pytest -v
```

- [ ] **Step 2: Запушить ветку, открыть PR, дождаться CI**

```bash
git checkout -b feat/sprint-1-foundation
git add .github
git commit -m "ci: add lint/type-check/test workflow for web, api, workers"
git push -u origin feat/sprint-1-foundation
gh pr create --title "Sprint 1 Foundation" --body "Foundation work for Sprint 1"
```

Expected: все 3 джобы зелёные.

- [ ] **Step 3: Исправить любые красные джобы**

Запустить локально то, что упало, исправить, push.

- [ ] **Step 4: Commit & push**

После зелёного CI — merge готов.

---

## Task 16: GitHub Actions — Docker build & push в Yandex Container Registry

**Files:**
- Create: `.github/workflows/build-and-push.yml`

- [ ] **Step 1: Workflow**

`.github/workflows/build-and-push.yml`:

```yaml
name: Build & Push

on:
  push:
    branches: [main]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [web, api, workers]
    steps:
      - uses: actions/checkout@v4

      - name: Login to Yandex Container Registry
        uses: yc-actions/yc-cr-login@v3
        with:
          yc-sa-json-credentials: ${{ secrets.YC_SA_JSON_KEY }}

      - uses: docker/setup-buildx-action@v3

      - name: Build and push ${{ matrix.service }}
        uses: docker/build-push-action@v6
        with:
          context: .
          file: apps/${{ matrix.service }}/Dockerfile
          push: true
          tags: |
            cr.yandex/${{ secrets.YC_REGISTRY_ID }}/proshli-${{ matrix.service }}:${{ github.sha }}
            cr.yandex/${{ secrets.YC_REGISTRY_ID }}/proshli-${{ matrix.service }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

- [ ] **Step 2: Добавить GitHub Secrets**

В GitHub репо → Settings → Secrets:
- `YC_SA_JSON_KEY` — содержимое `yc-sa-key.json`
- `YC_REGISTRY_ID` — ID контейнер-реджистри из Pre-flight

- [ ] **Step 3: Push в main → проверить CI**

После merge PR в main → проверить, что `Build & Push` зелёный, 3 образа загружены в YCR.

```bash
yc container image list --registry-id <ID>
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/build-and-push.yml
git commit -m "ci: build & push Docker images to Yandex Container Registry"
```

---

## Task 17: Yandex Serverless Containers — deploy api + web

**Files:**
- Create: `.github/workflows/deploy-staging.yml`
- Create: `ops/deploy/api.yaml` (yc описание контейнера)
- Create: `ops/deploy/web.yaml`

- [ ] **Step 1: Деплой через yc CLI вручную (один раз)**

```bash
yc serverless container create --name proshli-api-staging
yc serverless container create --name proshli-web-staging

yc serverless container revision deploy \
  --container-name proshli-api-staging \
  --image cr.yandex/<ID>/proshli-api:latest \
  --cores 1 --memory 512MB \
  --service-account-id <SA_ID> \
  --environment DATABASE_URL=<PG_DSN> \
  --environment JWT_SECRET=<SECRET> \
  --environment SENTRY_DSN=<DSN>

yc serverless container revision deploy \
  --container-name proshli-web-staging \
  --image cr.yandex/<ID>/proshli-web:latest \
  --cores 1 --memory 512MB \
  --service-account-id <SA_ID> \
  --environment NEXT_PUBLIC_API_URL=https://api-staging.proshli.ru
```

Сохранить container IDs.

- [ ] **Step 2: deploy-staging.yml**

`.github/workflows/deploy-staging.yml`:

```yaml
name: Deploy staging

on:
  workflow_run:
    workflows: ["Build & Push"]
    types: [completed]
    branches: [main]

jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [api, web, workers]
    steps:
      - uses: actions/checkout@v4
      - uses: yc-actions/yc-sls-container-deploy@v3
        with:
          yc-sa-json-credentials: ${{ secrets.YC_SA_JSON_KEY }}
          container-name: proshli-${{ matrix.service }}-staging
          revision-service-account-id: ${{ secrets.YC_DEPLOY_SA_ID }}
          revision-image-url: cr.yandex/${{ secrets.YC_REGISTRY_ID }}/proshli-${{ matrix.service }}:${{ github.sha }}
          revision-cores: 1
          revision-memory: 512MB
```

- [ ] **Step 3: Привязать домены через Yandex Cloud → API Gateway или CDN**

В консоли Yandex Cloud → создать API Gateway:
- `/api/*` → proshli-api-staging container
- `/*` → proshli-web-staging container

Привязать домен `staging.proshli.ru` к gateway, выпустить SSL через managed certs.

- [ ] **Step 4: Smoke-тест**

```bash
curl https://staging.proshli.ru/api/health/live
curl https://staging.proshli.ru/  # должна вернуться Next.js страница
```

- [ ] **Step 5: Commit & push**

```bash
git add .github/workflows/deploy-staging.yml ops/
git commit -m "ci: deploy staging via Yandex Serverless Containers"
```

После merge — проверить деплой в Actions UI.

---

## Task 18: Sentry self-hosted для API + Web

**Files:**
- Modify: `apps/web/instrumentation.ts` (создать, если нет)
- Modify: `apps/web/sentry.client.config.ts`
- Modify: `apps/web/sentry.server.config.ts`

- [ ] **Step 1: Поднять GlitchTip (open-source Sentry-compatible) на Yandex Compute**

В консоли Yandex Cloud создать VM `glitchtip-staging`, поставить через docker-compose из glitchtip docs. Получить DSN.

(Альтернатива: cloud Sentry free tier — но он не self-hosted и данные уходят за рубеж.)

- [ ] **Step 2: Установить @sentry/nextjs**

```bash
pnpm --filter @proshli/web add @sentry/nextjs
```

- [ ] **Step 3: Wizard**

```bash
cd apps/web
pnpm dlx @sentry/wizard@latest -i nextjs
```

Внести DSN, ничего автоматического не отправлять (отказаться от source-maps на CI на этом этапе).

- [ ] **Step 4: Проверить, что ошибка ловится**

Создать `apps/web/app/[locale]/sentry-test/page.tsx`:

```tsx
"use client";

import { Button } from "@proshli/ui";

export default function SentryTestPage() {
  return (
    <Button onClick={() => { throw new Error("Test Sentry error"); }}>
      Throw error
    </Button>
  );
}
```

Нажать → проверить, что событие появилось в GlitchTip UI.

- [ ] **Step 5: Backend Sentry уже подключён в Task 13** — проверить, что в `.env` есть `SENTRY_DSN` и тест-эндпоинт работает.

Создать `apps/api/app/routes/dev.py`:

```python
from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/dev", tags=["dev"])

@router.get("/sentry-test")
async def sentry_test() -> dict:
    if settings.app_env != "development":
        return {"status": "disabled in prod"}
    raise RuntimeError("Test Sentry error")
```

Подключить только в dev в `main.py`:

```python
if settings.app_env == "development":
    from app.routes import dev
    app.include_router(dev.router)
```

- [ ] **Step 6: Commit**

```bash
git add apps/web apps/api
git commit -m "feat(observability): wire Sentry/GlitchTip on web and api"
```

---

## Task 19: Plausible self-hosted для аналитики

**Files:**
- Modify: `apps/web/app/[locale]/layout.tsx` (добавить script)
- Create: `ops/plausible/docker-compose.yml`

- [ ] **Step 1: Поднять Plausible**

На той же staging-VM рядом с GlitchTip:

```bash
mkdir ~/plausible && cd ~/plausible
curl -sSL https://github.com/plausible/community-edition/raw/master/docker-compose.yml -o docker-compose.yml
curl -sSL https://github.com/plausible/community-edition/raw/master/plausible-conf.env.example -o plausible-conf.env
# заполнить SECRET_KEY_BASE, BASE_URL=https://plausible.proshli.ru
docker compose up -d
```

- [ ] **Step 2: Создать site в Plausible UI**

`staging.proshli.ru` — получить script tag.

- [ ] **Step 3: Подключить в layout**

В `apps/web/app/[locale]/layout.tsx`:

```tsx
import Script from "next/script";

// внутри <head>
<Script
  src="https://plausible.proshli.ru/js/script.js"
  data-domain="staging.proshli.ru"
  strategy="afterInteractive"
/>
```

- [ ] **Step 4: Smoke-тест**

Открыть `https://staging.proshli.ru/ru`, проверить в Plausible Dashboard — visit зарегистрировался.

- [ ] **Step 5: Commit**

```bash
git add apps/web ops/plausible
git commit -m "feat(observability): Plausible self-hosted analytics"
```

---

## Task 20: README + контрибьютор-документ

**Files:**
- Modify: `README.md`
- Create: `CONTRIBUTING.md`

- [ ] **Step 1: Обновить README с новой структурой**

`README.md` (целиком переписать):

```markdown
# Proshli (codename: jobskout)

Премиум job-search SaaS для IT-аудитории РФ/СНГ. Парсит вакансии из HH, Habr Career, Telegram-каналов и корп. сайтов; сортирует по «шансу взятия»; генерит резюме под вакансию через AI; находит контакты компаний в открытых источниках; ведёт канбан откликов с автотрекингом через email.

## Структура

\`\`\`
apps/
  web/        — Next.js 16 фронт (RU+EN, темы, App Router)
  api/        — FastAPI async + Postgres+pgvector + Alembic
  workers/    — Celery воркеры (парсеры, AI, email)
  tgbot/      — Telegram-бот (aiogram)
packages/
  ui/         — shadcn-style дизайн-система + Storybook
  shared-types/ — общие TS-типы домена
  config/     — общие eslint/tsconfig/prettier
docs/
  superpowers/specs/  — design-спеки
  superpowers/plans/  — implementation планы
ops/
  deploy/     — Yandex Cloud деплой-конфиги
\`\`\`

## Быстрый старт (локально)

\`\`\`bash
# 1. Установить деps
pnpm install
cd apps/api && uv sync --all-groups && cd ../..
cd apps/workers && uv sync --all-groups && cd ../..

# 2. Поднять зависимости (Postgres, Redis, Meilisearch)
docker compose up -d postgres redis meilisearch

# 3. Запустить миграции
cd apps/api
cp .env.example .env
uv run alembic upgrade head

# 4. В двух терминалах
pnpm --filter @proshli/web dev      # http://127.0.0.1:3000
cd apps/api && uv run uvicorn app.main:app --reload   # http://127.0.0.1:8000
\`\`\`

## Storybook

\`\`\`bash
pnpm --filter @proshli/ui storybook   # http://localhost:6006
\`\`\`

## CI / Деплой

- Push в любую ветку → CI (lint + type-check + tests)
- Merge в main → Docker build + push в YCR → deploy в staging

## Документация

- [Design spec](docs/superpowers/specs/2026-05-17-jobskout-v2-platform-design.md)
- [Sprint 1 plan](docs/superpowers/plans/2026-05-17-sprint-1-foundation.md)
```

- [ ] **Step 2: CONTRIBUTING.md**

`CONTRIBUTING.md`:

```markdown
# Contributing

## Branches
- `main` — staging-ready, defended by CI
- `feat/<sprint>-<area>` — feature branches

## Commits — Conventional Commits

- `feat(scope): ...` — новая фича
- `fix(scope): ...` — багфикс
- `refactor(scope): ...` — рефакторинг без изменения поведения
- `chore(scope): ...` — инфра / зависимости
- `docs(scope): ...` — документация
- `ci(scope): ...` — CI/CD

Scopes: `web`, `api`, `workers`, `tgbot`, `ui`, `shared-types`, `config`, `repo`, `infra`.

## PR Checklist

- [ ] Все workflow зелёные
- [ ] Тесты добавлены для новой логики
- [ ] Если изменена БД — добавлена Alembic-миграция
- [ ] Если меняется UI — добавлена/обновлена Storybook story
- [ ] Без `console.log`, `print`, оставленных TODO
```

- [ ] **Step 3: Commit**

```bash
git add README.md CONTRIBUTING.md
git commit -m "docs: rewrite README + CONTRIBUTING for monorepo"
```

---

## Task 21: Финальная проверка Sprint 1

- [ ] **Step 1: Локально всё работает**

```bash
docker compose up -d
pnpm --filter @proshli/web dev &
cd apps/api && uv run uvicorn app.main:app --reload &
```

Проверить:
- http://127.0.0.1:3000/ru — главная RU
- http://127.0.0.1:3000/en — главная EN
- Переключатель темы (через devtools `[data-theme=dark]`)
- http://127.0.0.1:8000/health/ready — `database: ok`
- http://127.0.0.1:8000/docs — Swagger
- http://localhost:6006 — Storybook

- [ ] **Step 2: CI зелёный**

```bash
gh run list --limit 5
```

Expected: 5 успешных run-ов на main.

- [ ] **Step 3: Staging deploy работает**

```bash
curl -sSL https://staging.proshli.ru/api/health/live
curl -sSL https://staging.proshli.ru/ru | head -20
```

Expected: API возвращает `{"status":"ok"}`, web возвращает HTML с Next.js.

- [ ] **Step 4: Observability работает**

- Нажать «Throw error» на /ru/sentry-test → событие появилось в GlitchTip
- В Plausible — есть визиты

- [ ] **Step 5: Финальный smoke-checklist в репо**

Создать `docs/superpowers/plans/2026-05-17-sprint-1-completion.md`:

```markdown
# Sprint 1 Completion Checklist

- [x] Turborepo monorepo с pnpm
- [x] apps/web на Next.js 16 + Tailwind 4 + shadcn-style UI + i18n RU/EN + 4 темы
- [x] apps/api на FastAPI async + SQLAlchemy 2 + asyncpg + pgvector
- [x] Alembic миграции async
- [x] apps/workers — Celery stub
- [x] apps/tgbot — структура готова
- [x] packages/ui — компонентная база + Storybook
- [x] packages/shared-types — TS-типы домена
- [x] packages/config — общие eslint/tsconfig/prettier
- [x] docker-compose.dev.yml — Postgres+pgvector, Redis, Meilisearch
- [x] Dockerfile для web/api/workers
- [x] CI: lint + type-check + tests (3 job)
- [x] Build & Push в Yandex Container Registry
- [x] Деплой в Yandex Serverless Containers (staging)
- [x] Домен staging.proshli.ru + SSL
- [x] Sentry / GlitchTip self-hosted
- [x] Plausible self-hosted

## Готов к Sprint 2

Следующий план: парсеры (HH API, Habr Career, Telegram, корп. сайты) + дедупликация + embedding worker + Meilisearch индексация.
```

- [ ] **Step 6: Tag и merge**

```bash
git tag v0.1.0-sprint-1
git push origin v0.1.0-sprint-1
```

---

## Self-review (по правилам writing-plans)

**Spec coverage** (по разделам спеки):

- ✅ Sprint 1 раздел 10 — Sprint 1: «Sprint 1 — нед. 1-2: Фундамент» полностью покрыт Task 1-21
- ✅ Tech stack (раздел 5) — Next.js 16, FastAPI async, Postgres+pgvector, Redis, Celery, Meilisearch — все добавлены
- ✅ Frontend 10/10 (раздел 8) — design tokens, темы (light/dark/system/oled), i18n (RU/EN), shadcn/ui, Framer Motion, Storybook
- ✅ Архитектура (раздел 6) — monorepo с apps/packages, pgvector, ClickHouse — последний оставлен на Sprint 2 (когда нужен)
- ⚠️ Yandex Cloud setup — описано клик-опсом в Pre-flight; альтернативно можно описать через Terraform на Sprint 2
- ⚠️ AI router (раздел 5) — не входит в Sprint 1 фундамент, добавляется в Sprint 4
- ⚠️ Браузер-кластер Playwright — Sprint 2 (для корп. сайтов)

**Placeholder scan:** ✅ нет TODO/TBD/«fill in details» — каждый шаг имеет код или точную команду.

**Type consistency:** ✅ Vacancy / User / Application типы определены один раз в `@proshli/shared-types`, переиспользуются. Имена snake_case в Python и camelCase в TS — конверсия делается на API-границе (будет в Sprint 3).

**Известные риски Sprint 1:**

- Next.js 16 имеет breaking changes — Task 2 Step 4 явно требует прочитать AGENTS.md и breaking-доки
- Async SQLAlchemy конверсия (Task 4) может занять больше времени, если существующий код широко использовал sync API — буфер 1-2 дня
- Storybook 8 + Tailwind 4 — относительно свежие версии, могут быть мелкие интеграционные проблемы

---

## Execution

После approve плана — два варианта:

**1. Subagent-Driven** (рекомендуется) — для каждой Task диспатчится свежий subagent, я ревью между тасками, быстрая итерация.

**2. Inline Execution** — выполняем таски подряд в этой сессии с чекпоинтами на review.

Какой вариант?
