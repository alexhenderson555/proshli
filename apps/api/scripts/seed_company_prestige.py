"""Seed the ``company_prestige`` table with curated RU tech companies.

The Phase 2 channel-approval scoring formula tilts 30% of the final
candidate score toward "prestige" — a hand-curated proxy for company
recognition. This script populates a sensible starting set; tweak the
values to taste.

Idempotent: ``ON CONFLICT (normalised_name) DO UPDATE`` so re-running
just refreshes the values.

Usage::

    uv run python -m scripts.seed_company_prestige

Expects ``DATABASE_URL`` in the environment (or in ``apps/api/.env``).
"""

from __future__ import annotations

import asyncio
import unicodedata

from app.config import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Score is 0.0–1.0. Tier 1 (≥0.90) = household-name RU tech;
# Tier 2 (0.70–0.89) = strong RU players + global brands with RU offices;
# Tier 3 (0.50–0.69) = solid mid-market.
_PRESTIGE: dict[str, float] = {
    # Tier 1 — big tech
    "Яндекс": 0.95,
    "Yandex": 0.95,
    "VK": 0.92,
    "Тинькофф": 0.93,
    "Tinkoff": 0.93,
    "T-Bank": 0.93,
    "Т-Банк": 0.93,
    "Сбер": 0.92,
    "Sber": 0.92,
    "СберТех": 0.90,
    "Avito": 0.91,
    "Авито": 0.91,
    "Ozon": 0.90,
    "Озон": 0.90,
    "Wildberries": 0.88,
    # Tier 2 — strong RU players
    "Альфа-Банк": 0.85,
    "Alfa-Bank": 0.85,
    "X5 Group": 0.82,
    "X5": 0.82,
    "МТС": 0.80,
    "MTS": 0.80,
    "Билайн": 0.75,
    "Beeline": 0.75,
    "Мегафон": 0.75,
    "Megafon": 0.75,
    "Rostelecom": 0.72,
    "Ростелеком": 0.72,
    "Лаборатория Касперского": 0.85,
    "Kaspersky": 0.85,
    "Mail.ru": 0.80,
    "JetBrains": 0.92,
    "Selectel": 0.78,
    "ВТБ": 0.78,
    "VTB": 0.78,
    # Tier 3 — solid mid-market / niche-strong
    "Самокат": 0.72,
    "Самолёт": 0.65,
    "Циан": 0.70,
    "Авиасейлс": 0.75,
    "Aviasales": 0.75,
    "СДЭК": 0.62,
    "Dodo": 0.68,
    "Додо": 0.68,
    "HeadHunter": 0.78,
    "HH.ru": 0.78,
    "Skyeng": 0.72,
    "Skypro": 0.65,
    "Нетология": 0.68,
    "Yandex Cloud": 0.85,
    "Cloud.ru": 0.72,
    "Cloud.RU": 0.72,
}


def _normalise(name: str) -> str:
    """Mirror ``app.services.channel_scoring.normalise_company``."""
    return unicodedata.normalize("NFKD", name).casefold().strip()


async def _run() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for raw, score in _PRESTIGE.items():
            await conn.execute(
                text(
                    """
                    INSERT INTO company_prestige (company_normalised, score, notes)
                    VALUES (:n, :s, :d)
                    ON CONFLICT (company_normalised) DO UPDATE
                        SET score = EXCLUDED.score,
                            notes = EXCLUDED.notes,
                            updated_at = now()
                    """
                ),
                {"n": _normalise(raw), "s": score, "d": raw},
            )
        result = await conn.execute(
            text("SELECT count(*) FROM company_prestige")
        )
        total = result.scalar_one()
    await engine.dispose()
    print(f"company_prestige now has {total} rows")


if __name__ == "__main__":
    asyncio.run(_run())
