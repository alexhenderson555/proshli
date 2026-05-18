"""HTTP-layer wrappers around the Proshli backend API.

Centralises three things:

1. Service-to-service auth (``BOT_SERVICE_KEY`` header) on the bot's
   privileged endpoints (telegram login, link consume, etc.).
2. User-JWT minting + caching for handler-side calls. The TTL is short
   enough that a missed invalidation can't keep a stale identity
   indefinitely; a 401 from the API also evicts the cache.
3. A single ``api_request_for_user`` entry point that resolves the
   user JWT, attaches it, hits the backend, and returns
   ``(status_code, parsed_body | text | None)``. Handlers never call
   ``httpx`` directly — keeps the auth & error pattern uniform.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from aiogram.types import CallbackQuery, Message

from apps.tgbot.config import API_URL, BOT_SERVICE_KEY, logger
from apps.tgbot.keyboards import main_menu_keyboard
from apps.tgbot.state import TOKEN_CACHE, CachedToken


def bot_service_headers() -> dict[str, str]:
    return {"x-bot-service-key": BOT_SERVICE_KEY}


def telegram_user_id(message_or_query: Message | CallbackQuery) -> int | None:
    """Best-effort extraction of the Telegram user id from any event."""
    user = message_or_query.from_user
    return user.id if user else None


async def _login_user_via_telegram(
    http: httpx.AsyncClient,
    telegram_user_id_value: int,
    telegram_chat_id: int,
) -> str | None:
    """Mint a fresh user JWT from the API for this Telegram identity.

    Only call when the cache is stale — see ``get_user_token`` for the
    cached entry point.
    """
    payload = {
        "telegram_user_id": str(telegram_user_id_value),
        "telegram_chat_id": str(telegram_chat_id),
    }
    try:
        resp = await http.post(
            f"{API_URL}/auth/telegram/login",
            json=payload,
            headers=bot_service_headers(),
        )
    except httpx.HTTPError as exc:
        logger.warning("login_user_via_telegram network failure: %s", exc)
        return None
    if resp.status_code >= 400:
        logger.info(
            "login_user_via_telegram non-2xx: status=%s body=%s",
            resp.status_code,
            resp.text[:200],
        )
        return None
    data = resp.json()
    return data.get("access_token")


async def get_user_token(
    http: httpx.AsyncClient,
    telegram_user_id_value: int,
    telegram_chat_id: int,
) -> str | None:
    """Return a valid user JWT, hitting the API only when the cache is stale.

    Saves a full DB round-trip on every callback click (the previous
    behaviour). The cache is invalidated by:
      - TTL expiry (``TOKEN_CACHE_TTL_SECONDS``).
      - A 401 on a downstream call — the caller can ``pop`` the entry
        and retry with a fresh login.
    """
    cached = TOKEN_CACHE.get(telegram_user_id_value)
    if cached and cached.is_fresh:
        return cached.token
    token = await _login_user_via_telegram(http, telegram_user_id_value, telegram_chat_id)
    if token:
        TOKEN_CACHE[telegram_user_id_value] = CachedToken(
            token=token, issued_at=time.monotonic()
        )
    return token


async def api_request_for_user(
    http: httpx.AsyncClient,
    message: Message,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
) -> tuple[int, dict | list | str | None]:
    tg_user_id = telegram_user_id(message)
    if tg_user_id is None:
        await message.answer("Не вижу твой Telegram-аккаунт. Попробуй /start.")
        return 401, None

    user_token = await get_user_token(http, tg_user_id, message.chat.id)
    if not user_token:
        await message.answer(
            "Аккаунт не привязан.\n"
            "1) На сайте нажми 'Сгенерировать код привязки Telegram'\n"
            "2) Отправь в боте: /link ТВОЙ_КОД",
            reply_markup=main_menu_keyboard(),
        )
        return 401, None

    headers = {"Authorization": f"Bearer {user_token}"}
    try:
        resp = await http.request(
            method=method,
            url=f"{API_URL}{path}",
            params=params,
            json=json,
            headers=headers,
        )
    except httpx.HTTPError as exc:
        logger.warning("api_request_for_user network failure: %s", exc)
        await message.answer("Сеть недоступна, попробуй позже.")
        return 0, None

    # If the API rejected our cached token, drop it and let the next
    # interaction re-mint. We do not silently retry here — that hides
    # bugs in the link flow.
    if resp.status_code == 401:
        TOKEN_CACHE.pop(tg_user_id, None)

    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        return resp.status_code, resp.json()
    return resp.status_code, resp.text


async def post_channel_decision(
    http: httpx.AsyncClient, action: str, candidate_id: int, admin_message_id: int
) -> tuple[int, dict | None]:
    """POST to the bot-service channel-approval endpoint.

    Returns ``(status_code, parsed_json | None)``. Network failures
    surface as ``(0, None)`` so the caller can answer the callback
    with a generic error toast without crashing the dispatcher.
    """
    payload = {
        "candidate_id": candidate_id,
        "admin_message_id": admin_message_id,
    }
    try:
        resp = await http.post(
            f"{API_URL}/internal/channel-approval/{action}",
            json=payload,
            headers=bot_service_headers(),
        )
    except httpx.HTTPError as exc:
        logger.warning("channel_decision network failure: %s", exc)
        return 0, None
    body: dict[Any, Any] | None = None
    if "application/json" in resp.headers.get("content-type", ""):
        try:
            body = resp.json()
        except ValueError:
            body = None
    return resp.status_code, body
