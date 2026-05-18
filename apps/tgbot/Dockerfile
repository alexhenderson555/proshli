# Proshli Telegram bot — minimal aiogram polling container.
#
# The bot is an aiogram polling app with two runtime deps (aiogram +
# httpx). No build step, no compiled assets — just install the pinned
# deps and run the package.
#
# Build context: repo root (so the `apps/` prefix is visible). We copy
# the whole `apps/tgbot/` package because the bot was split from a
# single-file script into focused modules (config, state, keyboards,
# api_client, subscription, handlers, main).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Pin to majors that match what the bot was developed against. aiogram
# 3.x is the current line; httpx 0.27 is the latest minor that works
# with stdlib certifi on python:3.12-slim.
RUN pip install --no-cache-dir \
    "aiogram>=3.13,<4" \
    "httpx>=0.27,<0.29"

COPY apps/tgbot/ ./apps/tgbot/

# Use `-m` so absolute imports (`from apps.tgbot.handlers import dp`)
# resolve. WORKDIR=/app is on sys.path implicitly under `python -m`.
CMD ["python", "-m", "apps.tgbot.main"]
