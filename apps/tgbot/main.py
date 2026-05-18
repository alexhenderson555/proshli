"""Entrypoint for the Proshli Telegram bot.

Wires the dispatcher (defined in :mod:`apps.tgbot.handlers`) to a single
shared :class:`httpx.AsyncClient` and starts long-polling. Everything
else lives in dedicated modules — this file should stay roughly this
size as the bot grows.
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.types import BotCommand

from apps.tgbot.config import BOT_TOKEN, logger
from apps.tgbot.handlers import dp

# Slash-command suggestions surfaced by Telegram's "/" picker. The list
# must mirror the @dp.message(Command(...)) handlers in apps.tgbot.handlers;
# adding a new command without updating this tuple means users won't get
# autocomplete for it. Descriptions are capped to 256 chars by the Bot API
# — keep them short.
_BOT_COMMANDS: tuple[BotCommand, ...] = (
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="help", description="Список команд"),
    BotCommand(command="help_job", description="Что умею по теме работы"),
    BotCommand(command="link", description="Привязать аккаунт по коду с сайта"),
    BotCommand(command="search", description="Поиск с текущими фильтрами"),
    BotCommand(command="digest_daily", description="Ежедневный дайджест"),
    BotCommand(command="digest_weekly", description="Еженедельный дайджест"),
    BotCommand(command="digest_off", description="Отключить дайджест"),
    BotCommand(command="unlink", description="Отвязать Telegram-аккаунт"),
    BotCommand(command="improve_resume", description="AI-советы по резюме"),
)


async def _register_bot_commands(bot: Bot) -> None:
    """Push the slash-command catalogue to Telegram on startup.

    ``set_my_commands`` is idempotent server-side, so running this every
    boot is cheap and keeps the catalogue in sync if we add/remove a
    handler. Failures are logged but non-fatal — we'd rather a bot with
    no autocomplete than no bot at all.
    """
    try:
        await bot.set_my_commands(list(_BOT_COMMANDS))
    except (TelegramBadRequest, TelegramNetworkError) as exc:
        logger.warning("set_my_commands failed: %s", exc)


async def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if not BOT_TOKEN:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN before running bot.")

    # Single httpx client shared across all handlers — reuses TCP /
    # keepalive connections and saves ~50 ms per call vs. a per-request
    # ``async with httpx.AsyncClient()``. Injected into handlers via
    # aiogram's ``workflow_data`` dependency mechanism.
    async with httpx.AsyncClient(timeout=10.0) as http:
        bot = Bot(token=BOT_TOKEN)
        try:
            await _register_bot_commands(bot)
            await dp.start_polling(bot, http=http)
        finally:
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
