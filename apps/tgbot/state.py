"""In-memory per-chat and per-user state for the bot.

Two dicts live here:

* ``TOKEN_CACHE`` — Telegram user id → freshly-minted API JWT. Lets us
  skip a full ``POST /auth/telegram/login`` on every click.
* ``CHAT_STATE`` — chat id → :class:`ChatState`. Holds the picked-up
  search filters and the "next text message is for AI" flag.

Both live in-process; if we ever scale beyond one bot instance these
move to Redis. For a single-instance polling bot they're fine.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from apps.tgbot.config import TOKEN_CACHE_TTL_SECONDS


@dataclass
class CachedToken:
    """A user-JWT minted by the API for a Telegram identity.

    We keep the issued-at clock and refresh proactively rather than
    waiting for a 401. ``user_id`` is the Telegram user id (not the
    Proshli user id) — we don't need the latter on the bot side.
    """

    token: str
    issued_at: float

    @property
    def is_fresh(self) -> bool:
        return (time.monotonic() - self.issued_at) < TOKEN_CACHE_TTL_SECONDS


@dataclass
class ChatState:
    filters: dict[str, str] = field(default_factory=dict)
    waiting_ai_input: bool = False


CHAT_STATE: dict[int, ChatState] = {}
# Telegram user id → cached user JWT. Keyed by user (not chat) so private
# + group chats for the same user share auth.
TOKEN_CACHE: dict[int, CachedToken] = {}


def chat_state(chat_id: int) -> ChatState:
    if chat_id not in CHAT_STATE:
        CHAT_STATE[chat_id] = ChatState()
    return CHAT_STATE[chat_id]
