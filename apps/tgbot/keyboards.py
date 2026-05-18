"""Inline keyboard factories.

Pure functions — no state, no I/O. Kept in one module so we don't have
to scroll through 100 lines of ``InlineKeyboardButton`` arrays mixed in
with the handler logic.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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


def vacancy_card_keyboard(item: dict) -> InlineKeyboardMarkup | None:
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
