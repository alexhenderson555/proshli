import asyncio
import logging
import os
import time
from dataclasses import dataclass, field

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# `OTKLIK_API_URL` is the canonical name post-rebrand; `JOBSKOUT_API_URL`
# is still honoured as a fallback so older deployments don't break.
API_URL = os.getenv("OTKLIK_API_URL") or os.getenv("JOBSKOUT_API_URL", "http://127.0.0.1:8000")
BOT_SERVICE_KEY = os.getenv("BOT_SERVICE_KEY", "change-me-bot-service-key")
REQUIRE_CHANNEL_SUBSCRIPTION = os.getenv("REQUIRE_CHANNEL_SUBSCRIPTION", "true").lower() == "true"
REQUIRED_CHANNEL_USERNAME = os.getenv("REQUIRED_CHANNEL_USERNAME", "@iischnaya").strip()
EMPLOYER_PROMO_URL = os.getenv("EMPLOYER_PROMO_URL", "https://t.me/your_channel")

# How long we trust a Telegram-issued user JWT before we re-mint one.
# Backend default is 60 min — we keep a safe margin so a click landing
# right at the boundary doesn't 401.
TOKEN_CACHE_TTL_SECONDS = 30 * 60

logger = logging.getLogger("otklik.tgbot")

dp = Dispatcher()


@dataclass
class CachedToken:
    """A user-JWT minted by the API for a Telegram identity.

    We keep the issued-at clock and refresh proactively rather than
    waiting for a 401. ``user_id`` is the Telegram user id (not the
    Otklik user id) — we don't need the latter on the bot side.
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


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Искать вакансии", callback_data="search_now"),
                InlineKeyboardButton(text="AI фильтр", callback_data="ai_filter"),
            ],
            [
                InlineKeyboardButton(text="Кнопочные фильтры", callback_data="filters_menu"),
                InlineKeyboardButton(text="Показать фильтры", callback_data="show_filters"),
            ],
            [
                InlineKeyboardButton(text="Дайджест daily", callback_data="digest_daily"),
                InlineKeyboardButton(text="Дайджест weekly", callback_data="digest_weekly"),
            ],
            [
                InlineKeyboardButton(text="Проверить подписку", callback_data="check_sub"),
                InlineKeyboardButton(text="Промо для работодателей", callback_data="promo_info"),
            ],
            [
                InlineKeyboardButton(text="Привязать аккаунт", callback_data="link_help"),
            ],
            [
                InlineKeyboardButton(text="Сбросить фильтры", callback_data="clear_filters"),
            ],
        ]
    )


def filters_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Level: junior", callback_data="f_level_junior"),
                InlineKeyboardButton(text="Level: middle", callback_data="f_level_middle"),
                InlineKeyboardButton(text="Level: senior", callback_data="f_level_senior"),
            ],
            [
                InlineKeyboardButton(text="Mode: remote", callback_data="f_mode_remote"),
                InlineKeyboardButton(text="Mode: hybrid", callback_data="f_mode_hybrid"),
                InlineKeyboardButton(text="Mode: office", callback_data="f_mode_office"),
            ],
            [
                InlineKeyboardButton(text="Stack: python", callback_data="f_stack_python"),
                InlineKeyboardButton(text="Stack: frontend", callback_data="f_stack_frontend"),
                InlineKeyboardButton(text="Stack: data", callback_data="f_stack_data"),
            ],
            [InlineKeyboardButton(text="Назад в меню", callback_data="go_main")],
        ]
    )


def chat_state(chat_id: int) -> ChatState:
    if chat_id not in CHAT_STATE:
        CHAT_STATE[chat_id] = ChatState()
    return CHAT_STATE[chat_id]


def bot_service_headers() -> dict[str, str]:
    return {"x-bot-service-key": BOT_SERVICE_KEY}


async def _login_user_via_telegram(
    http: httpx.AsyncClient,
    telegram_user_id: int,
    telegram_chat_id: int,
) -> str | None:
    """Mint a fresh user JWT from the API for this Telegram identity.

    Only call when the cache is stale — see ``get_user_token`` for the
    cached entry point.
    """
    payload = {
        "telegram_user_id": str(telegram_user_id),
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
    telegram_user_id: int,
    telegram_chat_id: int,
) -> str | None:
    """Return a valid user JWT, hitting the API only when the cache is stale.

    Saves a full DB round-trip on every callback click (the previous
    behaviour). The cache is invalidated by:
      - TTL expiry (``TOKEN_CACHE_TTL_SECONDS``).
      - A 401 on a downstream call — the caller can ``pop`` the entry
        and retry with a fresh login.
    """
    cached = TOKEN_CACHE.get(telegram_user_id)
    if cached and cached.is_fresh:
        return cached.token
    token = await _login_user_via_telegram(http, telegram_user_id, telegram_chat_id)
    if token:
        TOKEN_CACHE[telegram_user_id] = CachedToken(token=token, issued_at=time.monotonic())
    return token


def _telegram_user_id(message_or_query: Message | CallbackQuery) -> int | None:
    """Best-effort extraction of the Telegram user id from any event."""
    user = message_or_query.from_user
    return user.id if user else None


async def api_request_for_user(
    http: httpx.AsyncClient,
    message: Message,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
) -> tuple[int, dict | list | str | None]:
    tg_user_id = _telegram_user_id(message)
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


def is_subscription_guard_enabled() -> bool:
    return REQUIRE_CHANNEL_SUBSCRIPTION and bool(REQUIRED_CHANNEL_USERNAME)


async def is_subscribed(bot: Bot | None, user_id: int) -> bool:
    if not is_subscription_guard_enabled():
        return True
    if bot is None:
        # ``message.bot`` is typed as Optional by aiogram; in practice
        # it's always set on real updates, but be defensive — refuse
        # rather than crash.
        return False
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL_USERNAME, user_id)
    except TelegramBadRequest:
        # User has never been a member, or the bot can't see the channel.
        return False
    except TelegramNetworkError as exc:
        logger.warning("is_subscribed network failure: %s", exc)
        return False
    return member.status in {"member", "administrator", "creator"}


async def ensure_subscription_message(message: Message) -> bool:
    if not is_subscription_guard_enabled():
        return True
    user_id = _telegram_user_id(message) or 0
    ok = await is_subscribed(message.bot, user_id)
    if ok:
        return True
    await message.answer(
        f"Для доступа к функциям подпишись на канал {REQUIRED_CHANNEL_USERNAME} и нажми 'Проверить подписку'.",
        reply_markup=main_menu_keyboard(),
    )
    return False


async def ensure_subscription_callback(query: CallbackQuery) -> bool:
    if not is_subscription_guard_enabled():
        return True
    ok = await is_subscribed(query.bot, query.from_user.id)
    if ok:
        return True
    await query.answer("Сначала подпишись на канал.", show_alert=True)
    if query.message:
        await query.message.answer(
            f"Нужна подписка на {REQUIRED_CHANNEL_USERNAME}. После подписки нажми 'Проверить подписку'.",
            reply_markup=main_menu_keyboard(),
        )
    return False


@dp.message(Command("help_job"))
async def help_job(message: Message) -> None:
    await message.answer(
        "Могу помочь только по теме работы: вакансии, резюме, отклики и подготовка к интервью."
    )


@dp.message(Command("help"))
async def help_cmd(message: Message) -> None:
    """Bot-level help (commands), distinct from `/help_job` (topic scope)."""
    await message.answer(
        "Доступные команды:\n"
        "/start — главное меню\n"
        "/help — эта подсказка\n"
        "/help_job — что я умею по теме работы\n"
        "/link КОД — привязать аккаунт по коду с сайта\n"
        "/search — выполнить поиск с текущими фильтрами\n"
        "/digest_daily — включить ежедневный дайджест\n"
        "/digest_weekly — включить еженедельный дайджест\n"
        "/digest_off — отключить дайджест\n"
        "/unlink — отвязать аккаунт от Telegram\n"
        "/improve_resume — AI-советы по последнему резюме",
        reply_markup=main_menu_keyboard(),
    )


@dp.message(Command("link"))
async def link_account(message: Message, http: httpx.AsyncClient) -> None:
    parts = (message.text or "").strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Используй формат: /link ABCD1234")
        return
    code = parts[1].strip().upper()
    if not await ensure_subscription_message(message):
        return
    tg_user_id = _telegram_user_id(message)
    if tg_user_id is None:
        await message.answer("Не вижу твой Telegram-аккаунт. Попробуй /start.")
        return
    payload = {
        "code": code,
        "telegram_user_id": str(tg_user_id),
        "telegram_chat_id": str(message.chat.id),
        "telegram_username": message.from_user.username if message.from_user else None,
    }
    try:
        resp = await http.post(
            f"{API_URL}/auth/telegram/consume-link",
            json=payload,
            headers=bot_service_headers(),
        )
    except httpx.HTTPError as exc:
        logger.warning("link_account network failure: %s", exc)
        await message.answer("Сеть недоступна, попробуй позже.")
        return
    if resp.status_code >= 400:
        await message.answer("Код невалидный или истек. Сгенерируй новый код на сайте и попробуй снова.")
        return
    # Fresh link → drop any stale cached token so the next API call
    # re-mints under the new identity.
    TOKEN_CACHE.pop(tg_user_id, None)
    await message.answer("Готово! Аккаунт привязан. Теперь можно искать вакансии и включать дайджест.")


@dp.message(CommandStart())
async def start(message: Message) -> None:
    subscription_hint = ""
    if is_subscription_guard_enabled():
        subscription_hint = f"\nДоступ к функциям открыт после подписки на {REQUIRED_CHANNEL_USERNAME}."
    await message.answer(
        "Привет! Я Otklik.ai-бот.\n"
        "Я ищу вакансии, сохраняю фильтры, помогаю AI и настраиваю дайджест.\n"
        "Чтобы привязать аккаунт: сгенерируй код на сайте и отправь /link КОД.\n"
        "Команды: /help. Используй кнопки ниже."
        f"{subscription_hint}",
        reply_markup=main_menu_keyboard(),
    )


async def set_digest(http: httpx.AsyncClient, message: Message, frequency: str) -> None:
    payload = {
        "frequency": frequency,
        "via_telegram": True,
        "via_email": False,
        "telegram_chat_id": str(message.chat.id),
    }

    status_code, _ = await api_request_for_user(
        http,
        message,
        "PUT",
        "/digest/preferences",
        json=payload,
    )
    if status_code >= 400:
        await message.answer(f"Не удалось сохранить настройки ({status_code}).")
        return

    await message.answer(
        f"Готово. Подборка установлена: {frequency}. Буду присылать сюда в чат."
    )


def _vacancy_card_keyboard(item: dict) -> InlineKeyboardMarkup | None:
    """Per-vacancy inline keyboard with an 'Откликнуться' deep-link.

    The button is omitted when ``external_url`` is missing (e.g. a hand-
    posted vacancy without a public landing page) so users don't see a
    dead button. Returns ``None`` in that case so aiogram skips the
    ``reply_markup`` field entirely.
    """
    url = item.get("external_url")
    if not url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Откликнуться", url=url)]]
    )


async def perform_search(http: httpx.AsyncClient, message: Message) -> None:
    state = chat_state(message.chat.id)
    params: dict[str, str] = {}
    if "level" in state.filters:
        params["level"] = state.filters["level"]
    if "stack" in state.filters:
        params["stack"] = state.filters["stack"]
    if "work_mode" in state.filters:
        params["work_mode"] = state.filters["work_mode"]

    status_code, data = await api_request_for_user(http, message, "GET", "/vacancies", params=params)
    if status_code >= 400:
        await message.answer(f"Не удалось выполнить поиск ({status_code}).")
        return

    items = (data or [])[:8] if isinstance(data, list) else []
    if not items:
        await message.answer("По текущим фильтрам вакансий не найдено.")
        return
    # One message per vacancy so each gets its own inline "Откликнуться"
    # button bound to that vacancy's ``external_url``. Telegram caps the
    # message rate at ~30/sec per chat — 8 results stays well clear.
    for idx, item in enumerate(items, start=1):
        promo = " [PROMO]" if item.get("is_promoted") else ""
        salary_from = item.get("salary_from") or "—"
        salary_to = item.get("salary_to") or "—"
        currency = item.get("currency") or ""
        text = (
            f"{idx}. {item['title']} @ {item['company']}{promo}\n"
            f"{item['location']} | {salary_from}–{salary_to} {currency}".rstrip()
        )
        await message.answer(text, reply_markup=_vacancy_card_keyboard(item))


@dp.message(Command("search"))
async def search_command(message: Message, http: httpx.AsyncClient) -> None:
    if not await ensure_subscription_message(message):
        return
    await perform_search(http, message)


@dp.message(Command("digest_daily"))
async def digest_daily(message: Message, http: httpx.AsyncClient) -> None:
    if not await ensure_subscription_message(message):
        return
    await set_digest(http, message, "daily")


@dp.message(Command("digest_weekly"))
async def digest_weekly(message: Message, http: httpx.AsyncClient) -> None:
    if not await ensure_subscription_message(message):
        return
    await set_digest(http, message, "weekly")


@dp.message(Command("digest_off"))
async def digest_off(message: Message, http: httpx.AsyncClient) -> None:
    """Turn off the digest entirely (both transports) for the linked user.

    Sends ``DELETE /digest/preferences``; the API zeros ``via_telegram``
    and ``via_email`` but keeps the row, so re-enabling later doesn't
    require re-typing the chat id.
    """
    if not await ensure_subscription_message(message):
        return
    status_code, _ = await api_request_for_user(
        http, message, "DELETE", "/digest/preferences"
    )
    if status_code >= 400:
        await message.answer(f"Не удалось отключить дайджест ({status_code}).")
        return
    await message.answer("Дайджест отключён. Включить обратно: /digest_daily или /digest_weekly.")


@dp.message(Command("unlink"))
async def unlink_account(message: Message, http: httpx.AsyncClient) -> None:
    """Revoke the Telegram link from the bot side.

    Calls the bot-service-key-protected ``DELETE /auth/telegram/link``
    endpoint and drops the locally cached JWT so subsequent commands
    immediately fall back to the "not linked" branch.
    """
    tg_user_id = _telegram_user_id(message)
    if tg_user_id is None:
        await message.answer("Не вижу твой Telegram-аккаунт. Попробуй /start.")
        return
    payload = {
        "telegram_user_id": str(tg_user_id),
        "telegram_chat_id": str(message.chat.id),
    }
    try:
        resp = await http.request(
            "DELETE",
            f"{API_URL}/auth/telegram/link",
            json=payload,
            headers=bot_service_headers(),
        )
    except httpx.HTTPError as exc:
        logger.warning("unlink_account network failure: %s", exc)
        await message.answer("Сеть недоступна, попробуй позже.")
        return
    # 204 = success, 404 was historic — current handler is idempotent.
    if resp.status_code >= 400 and resp.status_code != 404:
        await message.answer(f"Не удалось отвязать аккаунт ({resp.status_code}).")
        return
    TOKEN_CACHE.pop(tg_user_id, None)
    await message.answer(
        "Аккаунт отвязан. Чтобы пользоваться ботом снова — сгенерируй новый код на сайте и отправь /link КОД."
    )


@dp.message(Command("improve_resume"))
async def improve_resume(message: Message, http: httpx.AsyncClient) -> None:
    """Ask the API to AI-improve the seeker's latest resume version.

    Picks the most recent ``ResumeVersion`` from ``GET /resumes/versions``
    (already sorted newest-first by the API) and feeds its id into
    ``POST /resumes/versions/{id}/improve``. The free-form text after the
    command becomes the ``focus`` hint, e.g. ``/improve_resume сделай акцент на ML``.
    Counts against the per-day AI budget — the response carries
    ``used_today``/``limit`` so we can warn the user when the cap is near.
    """
    if not await ensure_subscription_message(message):
        return

    parts = (message.text or "").strip().split(maxsplit=1)
    focus = parts[1].strip() if len(parts) > 1 else ""

    status_code, listing = await api_request_for_user(
        http, message, "GET", "/resumes/versions"
    )
    if status_code == 401:
        # api_request_for_user already nudged the user about linking.
        return
    if status_code >= 400 or not isinstance(listing, list):
        await message.answer(
            f"Не удалось получить список резюме ({status_code}). Попробуй позже."
        )
        return
    if not listing:
        await message.answer(
            "У тебя пока нет сохранённых резюме. Создай версию резюме на сайте, "
            "а потом возвращайся — я подскажу, как её улучшить."
        )
        return

    latest = listing[0]
    version_id = latest.get("id")
    target_role = latest.get("target_role") or ""
    if not isinstance(version_id, int):
        await message.answer("Резюме найдено, но в неожиданном формате. Сообщи команде.")
        return

    payload = {"target_role": target_role, "focus": focus}
    status_code, data = await api_request_for_user(
        http,
        message,
        "POST",
        f"/resumes/versions/{version_id}/improve",
        json=payload,
    )
    if status_code == 429:
        await message.answer(
            "Дневной лимит AI-запросов исчерпан. Попробуй завтра или оформи подписку."
        )
        return
    if status_code >= 400 or not isinstance(data, dict):
        await message.answer(
            f"AI-сервис недоступен ({status_code}). Попробуй позже."
        )
        return

    summary = str(data.get("summary", "")).strip()
    suggestions = [
        str(item).strip()
        for item in (data.get("suggestions") or [])
        if isinstance(item, str) and str(item).strip()
    ]
    used_today = data.get("used_today")
    limit = data.get("limit")

    lines: list[str] = []
    name = str(latest.get("name", "резюме"))
    lines.append(f"AI-разбор резюме «{name}»:")
    if summary:
        lines.append("")
        lines.append(f"Summary: {summary}")
    if suggestions:
        lines.append("")
        lines.append("Что улучшить:")
        for idx, item in enumerate(suggestions, 1):
            lines.append(f"{idx}. {item}")
    if isinstance(used_today, int) and isinstance(limit, int):
        lines.append("")
        lines.append(f"Использовано AI-запросов сегодня: {used_today}/{limit}")
    await message.answer("\n".join(lines))


@dp.callback_query(F.data == "check_sub")
async def check_sub(query: CallbackQuery) -> None:
    ok = await is_subscribed(query.bot, query.from_user.id)
    if ok:
        await query.answer("Подписка подтверждена", show_alert=True)
        if query.message:
            await query.message.answer("Отлично, доступ открыт.", reply_markup=main_menu_keyboard())
    else:
        await query.answer("Подписка не найдена", show_alert=True)


@dp.callback_query(F.data == "link_help")
async def link_help(query: CallbackQuery) -> None:
    if query.message:
        await query.message.answer(
            "Как привязать аккаунт:\n"
            "1) Войди на сайт Otklik.ai под своим аккаунтом соискателя\n"
            "2) Нажми кнопку генерации кода Telegram\n"
            "3) Отправь в боте: /link КОД",
            reply_markup=main_menu_keyboard(),
        )
    await query.answer()


@dp.callback_query(F.data == "search_now")
async def search_now(query: CallbackQuery, http: httpx.AsyncClient) -> None:
    if not await ensure_subscription_callback(query):
        return
    if query.message:
        await perform_search(http, query.message)
    await query.answer()


@dp.callback_query(F.data == "digest_daily")
async def digest_daily_cb(query: CallbackQuery, http: httpx.AsyncClient) -> None:
    if not await ensure_subscription_callback(query):
        return
    if query.message:
        await set_digest(http, query.message, "daily")
    await query.answer()


@dp.callback_query(F.data == "digest_weekly")
async def digest_weekly_cb(query: CallbackQuery, http: httpx.AsyncClient) -> None:
    if not await ensure_subscription_callback(query):
        return
    if query.message:
        await set_digest(http, query.message, "weekly")
    await query.answer()


@dp.callback_query(F.data == "filters_menu")
async def filters_menu(query: CallbackQuery) -> None:
    if not await ensure_subscription_callback(query):
        return
    if query.message:
        await query.message.answer("Выбери быстрые фильтры:", reply_markup=filters_keyboard())
    await query.answer()


@dp.callback_query(F.data == "go_main")
async def go_main(query: CallbackQuery) -> None:
    if query.message:
        await query.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await query.answer()


@dp.callback_query(F.data == "show_filters")
async def show_filters(query: CallbackQuery) -> None:
    if not await ensure_subscription_callback(query):
        return
    state = chat_state(query.message.chat.id) if query.message else ChatState()
    if query.message:
        await query.message.answer(f"Текущие фильтры: {state.filters or 'не заданы'}")
    await query.answer()


@dp.callback_query(F.data == "clear_filters")
async def clear_filters(query: CallbackQuery) -> None:
    if query.message:
        state = chat_state(query.message.chat.id)
        state.filters = {}
        state.waiting_ai_input = False
        await query.message.answer("Фильтры сброшены.", reply_markup=main_menu_keyboard())
    await query.answer()


@dp.callback_query(F.data == "ai_filter")
async def ai_filter_start(query: CallbackQuery) -> None:
    if not await ensure_subscription_callback(query):
        return
    if query.message:
        state = chat_state(query.message.chat.id)
        state.waiting_ai_input = True
        await query.message.answer(
            "Напиши запрос текстом (например: 'ищу middle python удаленно'). Я извлеку фильтры через AI."
        )
    await query.answer()


@dp.callback_query(F.data == "promo_info")
async def promo_info(query: CallbackQuery) -> None:
    text = (
        "Для работодателей есть PRO-пуш вакансий.\n"
        "Через API можно включить продвижение (promote), чтобы вакансия показывалась выше.\n"
        f"Связаться/подробнее: {EMPLOYER_PROMO_URL}"
    )
    if query.message:
        await query.message.answer(text, reply_markup=main_menu_keyboard())
    await query.answer()


@dp.callback_query(F.data.startswith("f_"))
async def set_quick_filter(query: CallbackQuery) -> None:
    if not await ensure_subscription_callback(query):
        return
    if not query.message or not query.data:
        await query.answer()
        return
    state = chat_state(query.message.chat.id)
    code = query.data
    mapping = {
        "f_level_junior": ("level", "junior"),
        "f_level_middle": ("level", "middle"),
        "f_level_senior": ("level", "senior"),
        "f_mode_remote": ("work_mode", "remote"),
        "f_mode_hybrid": ("work_mode", "hybrid"),
        "f_mode_office": ("work_mode", "office"),
        "f_stack_python": ("stack", "python"),
        "f_stack_frontend": ("stack", "frontend"),
        "f_stack_data": ("stack", "data"),
    }
    if code in mapping:
        key, value = mapping[code]
        state.filters[key] = value
        await query.message.answer(f"Установлен фильтр: {key}={value}")
    await query.answer()


@dp.message(F.text)
async def fallback(message: Message, http: httpx.AsyncClient) -> None:
    state = chat_state(message.chat.id)
    text = message.text or ""
    if state.waiting_ai_input:
        if not await ensure_subscription_message(message):
            return
        payload = {"message": text}
        status_code, data = await api_request_for_user(http, message, "POST", "/ai/chat", json=payload)
        if status_code >= 400 or not isinstance(data, dict):
            await message.answer(f"AI не ответил корректно ({status_code}).")
            return
        if data.get("accepted") and data.get("extracted_filters"):
            for key, value in data["extracted_filters"].items():
                state.filters[key] = value
            await message.answer(f"AI применил фильтры: {state.filters}")
            await perform_search(http, message)
        else:
            await message.answer(data.get("message", "AI не смог извлечь фильтры."))
        state.waiting_ai_input = False
        return

    if text.startswith("/"):
        await message.answer("Неизвестная команда. Нажми /start или /help.")
        return

    await message.answer(
        "Выбери действие кнопками (/start).\n"
        "Я работаю только по теме карьеры и вакансий.",
        reply_markup=main_menu_keyboard(),
    )


async def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if not BOT_TOKEN:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN before running bot.")

    # Single httpx client shared across all handlers — reuses TCP /
    # keepalive connections and saves ~50 ms per call vs. the previous
    # per-request ``async with httpx.AsyncClient()``. Injected into
    # handlers via aiogram's ``workflow_data`` dependency mechanism.
    async with httpx.AsyncClient(timeout=10.0) as http:
        bot = Bot(token=BOT_TOKEN)
        try:
            await dp.start_polling(bot, http=http)
        finally:
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
