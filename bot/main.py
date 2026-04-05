import asyncio
import os
from dataclasses import dataclass, field

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_URL = os.getenv("JOBSKOUT_API_URL", "http://127.0.0.1:8000")
BOT_SERVICE_KEY = os.getenv("BOT_SERVICE_KEY", "change-me-bot-service-key")
REQUIRE_CHANNEL_SUBSCRIPTION = os.getenv("REQUIRE_CHANNEL_SUBSCRIPTION", "true").lower() == "true"
REQUIRED_CHANNEL_USERNAME = os.getenv("REQUIRED_CHANNEL_USERNAME", "@iischnaya").strip()
EMPLOYER_PROMO_URL = os.getenv("EMPLOYER_PROMO_URL", "https://t.me/your_channel")

dp = Dispatcher()

@dataclass
class ChatState:
    filters: dict[str, str] = field(default_factory=dict)
    waiting_ai_input: bool = False


CHAT_STATE: dict[int, ChatState] = {}


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


async def login_user_via_telegram(message: Message) -> str | None:
    telegram_user_id = str(message.from_user.id if message.from_user else "")
    telegram_chat_id = str(message.chat.id)
    payload = {
        "telegram_user_id": telegram_user_id,
        "telegram_chat_id": telegram_chat_id,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{API_URL}/auth/telegram/login",
            json=payload,
            headers=bot_service_headers(),
        )
    if resp.status_code >= 400:
        return None
    data = resp.json()
    return data.get("access_token")


async def api_request_for_user(
    message: Message,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
) -> tuple[int, dict | list | str | None]:
    user_token = await login_user_via_telegram(message)
    if not user_token:
        await message.answer(
            "Аккаунт не привязан.\n"
            "1) На сайте нажми 'Сгенерировать код привязки Telegram'\n"
            "2) Отправь в боте: /link ТВОЙ_КОД",
            reply_markup=main_menu_keyboard(),
        )
        return 401, None
    headers = {"Authorization": f"Bearer {user_token}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.request(
            method=method,
            url=f"{API_URL}{path}",
            params=params,
            json=json,
            headers=headers,
        )
    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        return resp.status_code, resp.json()
    return resp.status_code, resp.text


def is_subscription_guard_enabled() -> bool:
    return REQUIRE_CHANNEL_SUBSCRIPTION and bool(REQUIRED_CHANNEL_USERNAME)


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    if not is_subscription_guard_enabled():
        return True
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL_USERNAME, user_id)
        return member.status in {"member", "administrator", "creator"}
    except TelegramBadRequest:
        return False
    except Exception:  # noqa: BLE001
        return False


async def ensure_subscription_message(message: Message) -> bool:
    if not is_subscription_guard_enabled():
        return True
    bot = message.bot
    user_id = message.from_user.id if message.from_user else 0
    ok = await is_subscribed(bot, user_id)
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
    bot = query.bot
    user_id = query.from_user.id
    ok = await is_subscribed(bot, user_id)
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


@dp.message(Command("link"))
async def link_account(message: Message) -> None:
    parts = (message.text or "").strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Используй формат: /link ABCD1234")
        return
    code = parts[1].strip().upper()
    if not await ensure_subscription_message(message):
        return
    payload = {
        "code": code,
        "telegram_user_id": str(message.from_user.id if message.from_user else ""),
        "telegram_chat_id": str(message.chat.id),
        "telegram_username": message.from_user.username if message.from_user else None,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{API_URL}/auth/telegram/consume-link",
            json=payload,
            headers=bot_service_headers(),
        )
    if resp.status_code >= 400:
        await message.answer("Код невалидный или истек. Сгенерируй новый код на сайте и попробуй снова.")
        return
    await message.answer("Готово! Аккаунт привязан. Теперь можно искать вакансии и включать дайджест.")


@dp.message(CommandStart())
async def start(message: Message) -> None:
    subscription_hint = ""
    if is_subscription_guard_enabled():
        subscription_hint = f"\nДоступ к функциям открыт после подписки на {REQUIRED_CHANNEL_USERNAME}."
    await message.answer(
        "Привет! Я JobSkout-бот.\n"
        "Я ищу вакансии, сохраняю фильтры, помогаю AI и настраиваю дайджест.\n"
        "Чтобы привязать аккаунт: сгенерируй код на сайте и отправь /link КОД.\n"
        f"Используй кнопки ниже.{subscription_hint}",
        reply_markup=main_menu_keyboard(),
    )


async def set_digest(message: Message, frequency: str) -> None:
    payload = {
        "frequency": frequency,
        "via_telegram": True,
        "via_email": False,
        "telegram_chat_id": str(message.chat.id),
    }

    status_code, _ = await api_request_for_user(
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


async def perform_search(message: Message) -> None:
    state = chat_state(message.chat.id)
    params = {}
    if "level" in state.filters:
        params["level"] = state.filters["level"]
    if "stack" in state.filters:
        params["stack"] = state.filters["stack"]
    if "work_mode" in state.filters:
        params["work_mode"] = state.filters["work_mode"]

    status_code, data = await api_request_for_user(message, "GET", "/vacancies", params=params)
    if status_code >= 400:
        await message.answer(f"Не удалось выполнить поиск ({status_code}).")
        return

    data = (data or [])[:8]
    if not data:
        await message.answer("По текущим фильтрам вакансий не найдено.")
        return
    lines = []
    for idx, item in enumerate(data, start=1):
        promo = " [PROMO]" if item.get("is_promoted") else ""
        lines.append(
            f"{idx}. {item['title']} @ {item['company']}{promo}\n"
            f"   {item['location']} | {item.get('salary_from') or '-'}-{item.get('salary_to') or '-'} {item.get('currency')}"
        )
    await message.answer("\n\n".join(lines))


@dp.message(Command("search"))
async def search_command(message: Message) -> None:
    if not await ensure_subscription_message(message):
        return
    await perform_search(message)


@dp.message(Command("digest_daily"))
async def digest_daily(message: Message) -> None:
    if not await ensure_subscription_message(message):
        return
    await set_digest(message, "daily")


@dp.message(Command("digest_weekly"))
async def digest_weekly(message: Message) -> None:
    if not await ensure_subscription_message(message):
        return
    await set_digest(message, "weekly")


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
            "1) Войди на сайт JobSkout под своим аккаунтом соискателя\n"
            "2) Нажми кнопку генерации кода Telegram\n"
            "3) Отправь в боте: /link КОД",
            reply_markup=main_menu_keyboard(),
        )
    await query.answer()


@dp.callback_query(F.data == "search_now")
async def search_now(query: CallbackQuery) -> None:
    if not await ensure_subscription_callback(query):
        return
    if query.message:
        await perform_search(query.message)
    await query.answer()


@dp.callback_query(F.data == "digest_daily")
async def digest_daily_cb(query: CallbackQuery) -> None:
    if not await ensure_subscription_callback(query):
        return
    if query.message:
        await set_digest(query.message, "daily")
    await query.answer()


@dp.callback_query(F.data == "digest_weekly")
async def digest_weekly_cb(query: CallbackQuery) -> None:
    if not await ensure_subscription_callback(query):
        return
    if query.message:
        await set_digest(query.message, "weekly")
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
    if not query.message:
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
async def fallback(message: Message) -> None:
    state = chat_state(message.chat.id)
    if state.waiting_ai_input:
        if not await ensure_subscription_message(message):
            return
        payload = {"message": message.text}
        status_code, data = await api_request_for_user(message, "POST", "/ai/chat", json=payload)
        if status_code >= 400 or not isinstance(data, dict):
            await message.answer(f"AI не ответил корректно ({status_code}).")
            return
        if data.get("accepted") and data.get("extracted_filters"):
            for key, value in data["extracted_filters"].items():
                state.filters[key] = value
            await message.answer(f"AI применил фильтры: {state.filters}")
            await perform_search(message)
        else:
            await message.answer(data.get("message", "AI не смог извлечь фильтры."))
        state.waiting_ai_input = False
        return

    if message.text.startswith("/"):
        await message.answer("Неизвестная команда. Нажми /start.")
        return

    await message.answer(
        "Выбери действие кнопками (/start).\n"
        "Я работаю только по теме карьеры и вакансий.",
        reply_markup=main_menu_keyboard(),
    )


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN before running bot.")
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
