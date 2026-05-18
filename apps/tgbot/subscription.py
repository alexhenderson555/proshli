"""Channel-subscription gate.

The bot can be configured to require subscription to a specific
Telegram channel before any feature is usable (the launch promo for
the Proshli channel is a recurring growth lever). When the flag is
off, the gate is a no-op and every call short-circuits to ``True``.
"""

from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.types import CallbackQuery, Message

from apps.tgbot.api_client import telegram_user_id
from apps.tgbot.config import (
    REQUIRE_CHANNEL_SUBSCRIPTION,
    REQUIRED_CHANNEL_USERNAME,
    logger,
)
from apps.tgbot.keyboards import main_menu_keyboard


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
    user_id = telegram_user_id(message) or 0
    ok = await is_subscribed(message.bot, user_id)
    if ok:
        return True
    await message.answer(
        f"Для доступа к функциям подпишись на канал {REQUIRED_CHANNEL_USERNAME} "
        "и нажми 'Проверить подписку'.",
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
            f"Нужна подписка на {REQUIRED_CHANNEL_USERNAME}. "
            "После подписки нажми 'Проверить подписку'.",
            reply_markup=main_menu_keyboard(),
        )
    return False
