FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.4 /uv /usr/local/bin/uv

# Cache layer: deps only
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# App code
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
# Operational scripts (seed_company_prestige etc) — invoked via
# `uv run python -m scripts.<name>` from inside the container.
COPY scripts ./scripts

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
