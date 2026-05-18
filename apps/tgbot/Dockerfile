# Proshli Telegram bot — minimal aiogram polling container.
#
# The bot is a single-file aiogram polling app with two runtime deps
# (aiogram + httpx). No build step, no compiled assets — just install
# the pinned deps and run main.py.
#
# Build context: repo root (so the `apps/` prefix is visible). The
# image only needs `apps/tgbot/main.py`, but copying the whole
# `apps/tgbot/` directory keeps things forward-compatible if the bot
# later grows into a package.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /tgbot

# Pin to majors that match what the bot was developed against. aiogram
# 3.x is the current line; httpx 0.27 is the latest minor that works
# with stdlib certifi on python:3.12-slim.
RUN pip install --no-cache-dir \
    "aiogram>=3.13,<4" \
    "httpx>=0.27,<0.29"

COPY apps/tgbot/main.py ./main.py

CMD ["python", "main.py"]
