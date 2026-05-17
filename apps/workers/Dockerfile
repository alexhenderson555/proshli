FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /workers

# uv from the upstream image — pinned for reproducibility.
COPY --from=ghcr.io/astral-sh/uv:0.4 /uv /usr/local/bin/uv

# Cache deps before app code so source changes don't bust the layer.
COPY apps/workers/pyproject.toml apps/workers/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# The workers reach into ``app.*`` from the api project via a runtime
# sys.path insert, so we copy the api source alongside the workers code.
COPY apps/api/app /api/app
COPY apps/api/pyproject.toml /api/pyproject.toml
COPY apps/workers/workers ./workers

ENV PYTHONPATH="/api:/workers" \
    PATH="/workers/.venv/bin:$PATH"

# Default command runs a worker; docker-compose overrides this for the
# beat process. No EXPOSE — workers don't accept inbound connections.
CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=INFO"]
