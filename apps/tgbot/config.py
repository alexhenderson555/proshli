"""Environment-derived runtime configuration for the Telegram bot.

Read once at import. Module-level constants make the rest of the bot
testable: a unit test can monkey-patch ``API_URL`` without spinning up
the dispatcher or the real httpx client. Defaults match what's in the
README — anyone running ``python -m apps.tgbot.main`` against a local
API gets a working bot without touching the env file.
"""

from __future__ import annotations

import logging
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ``PROSHLI_API_URL`` is the canonical name post-rebrand; ``JOBSKOUT_API_URL``
# is still honoured as a fallback so older deployments don't break.
API_URL = os.getenv("PROSHLI_API_URL") or os.getenv("JOBSKOUT_API_URL", "http://127.0.0.1:8000")

BOT_SERVICE_KEY = os.getenv("BOT_SERVICE_KEY", "change-me-bot-service-key")

REQUIRE_CHANNEL_SUBSCRIPTION = (
    os.getenv("REQUIRE_CHANNEL_SUBSCRIPTION", "true").lower() == "true"
)
REQUIRED_CHANNEL_USERNAME = os.getenv("REQUIRED_CHANNEL_USERNAME", "@iischnaya").strip()
EMPLOYER_PROMO_URL = os.getenv("EMPLOYER_PROMO_URL", "https://t.me/your_channel")

# How long we trust a Telegram-issued user JWT before we re-mint one.
# Backend default is 60 min — we keep a safe margin so a click landing
# right at the boundary doesn't 401.
TOKEN_CACHE_TTL_SECONDS = 30 * 60

logger = logging.getLogger("proshli.tgbot")
