"""Telegram-channels connector.

Scrapes recent posts from public Telegram job channels (see
``docs/2026-05-17-tg-channels-curated-list.md``) using Telethon's user-account
API. The bot token in ``.env.prod`` is *not* usable here — bots cannot read
arbitrary public channels they're not admin of. The user-account session below
needs ``TELEGRAM_API_ID`` / ``TELEGRAM_API_HASH`` (from https://my.telegram.org)
and a one-off interactive login to create the ``.session`` file we mount into
the worker.

Operational shape
-----------------

* Channels list comes from ``settings.tg_channels`` (comma-separated @handles)
  with a sensible default roster baked in.
* For each channel we read up to ``TG_FETCH_PER_CHANNEL`` (default 30) most
  recent messages, filter to the last ``TG_LOOKBACK_HOURS`` (default 24), and
  apply a heuristic vacancy detector.
* The heuristic is intentionally generous: any post with > 80 chars *and* one
  of the common job keywords (вакансия/ищем/требуется/hiring/looking/salary)
  is forwarded to ingestion. The downstream AI prefilter does the real
  pruning — false positives are cheap, false negatives are not.
* External id is ``f"tg:{channel}:{msg_id}"`` — stable and unique.

The connector returns an empty list when ``TELEGRAM_API_ID``/``HASH`` are not
set (dev default) so test/CI runs are unaffected.
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import timedelta

from app.config import settings
from app.connectors.base import SourceConnector
from app.services.ingestion import VacancyPayload
from app.time_utils import now_utc


# Default roster matching docs/2026-05-17-tg-channels-curated-list.md. Override
# via the ``TG_CHANNELS`` env var (comma-separated bare @handles). Without an
# api_id/hash this list is irrelevant — the connector short-circuits to [].
DEFAULT_TG_CHANNELS: tuple[str, ...] = (
    "python_jobs_feed", "djangojobs", "python_jobs", "async_python_jobs", "ru_python_jobs",
    "golang_jobs", "golang_jobs_ru", "rust_jobs_feed", "java_jobs_feed", "kotlinjobs",
    "dotnet_jobs", "node_js_jobs", "php_jobs_feed",
    "frontend_jobs", "frontend_jobs_ru", "react_jobs", "vuejs_jobs", "typescript_jobs",
    "web_jobs_ru",
    "ios_jobs_feed", "android_jobs_feed", "flutter_jobs_ru", "react_native_jobs",
    "ml_jobs_feed", "data_science_jobs", "data_engineer_jobs", "ai_ml_jobs_ru",
    "analyst_jobs",
    "devops_jobs_feed", "sre_jobs_ru", "k8s_jobs", "cloud_jobs_ru", "platform_jobs",
    "qa_jobs_feed", "automation_qa_jobs", "qa_ru",
    "uxui_jobs", "design_jobs_ru", "product_designer_jobs",
    "product_jobs_ru", "pm_jobs_feed", "project_jobs_ru",
    "analytics_jobs_ru", "bi_jobs_feed", "business_analyst_jobs",
    "web3_jobs_feed", "crypto_jobs_ru", "blockchain_jobs_feed", "solidity_jobs",
    "gamedev_jobs_ru", "unity_jobs", "unreal_jobs",
    "infosec_jobs_ru", "security_jobs_feed", "pentest_jobs",
    "marketing_jobs_ru", "smm_jobs_ru", "content_jobs_ru", "copywriter_jobs_ru",
    "sales_jobs_ru", "support_jobs_ru", "cs_jobs_ru",
    "hr_jobs_ru", "recruiter_jobs",
    "relocation_jobs", "remote_jobs_ru", "work_abroad_it",
    "it_jobs_ru", "ru_it_jobs", "jobs_in_it", "it_remote_jobs", "it_jobs_feed",
    "ru_jobs_remote", "startup_jobs_ru",
    "c_plus_plus_jobs", "embedded_jobs", "scala_jobs", "ruby_jobs_feed", "1c_jobs_ru",
    "data_jobs_ru", "ml_engineers_jobs", "llm_engineer_jobs", "prompt_jobs",
    "ai_research_jobs",
)


# Keywords that gate a message into the "looks like a vacancy" bucket. Casefold
# everything before testing — Telegram posts mix Cyrillic & Latin freely.
_VACANCY_KEYWORDS: tuple[str, ...] = (
    "вакансия", "вакансии", "ищем", "ищу команду", "требуется", "набираем",
    "нужен", "нужна", "разыскивается", "open position", "we are hiring",
    "hiring", "looking for", "join us", "join our team", "we're hiring",
    "позиция", "зарплата", "salary", "от 100", "от 150", "от 200", "от 250",
    "от 300", "от 400", "от 500", "rub", "руб", "₽", "$", "€", "remote",
    "удаленно", "удалёнка", "офис", "гибрид", "оформление",
)


# Crude salary extractor — picks up "от 200 000 до 350 000 ₽" / "150-250k RUB"
# patterns. Returns ``(from, to, currency)``; any field can be None.
_SALARY_RE = re.compile(
    r"(?P<from>\d{2,3}(?:[\s\u00a0\u202f]?\d{3})*)\s*(?:[-—–]|до)\s*(?P<to>\d{2,3}(?:[\s\u00a0\u202f]?\d{3})*)\s*(?P<cur>₽|руб|rub|usd|\$|eur|€)?",
    re.IGNORECASE,
)


def _looks_like_vacancy(text: str) -> bool:
    if not text or len(text) < 80:
        return False
    lowered = text.casefold()
    return any(keyword in lowered for keyword in _VACANCY_KEYWORDS)


def _parse_salary(text: str) -> tuple[int | None, int | None, str]:
    match = _SALARY_RE.search(text)
    if not match:
        return None, None, "RUB"
    def _to_int(raw: str) -> int | None:
        try:
            return int(re.sub(r"\D", "", raw))
        except ValueError:
            return None

    salary_from = _to_int(match.group("from"))
    salary_to = _to_int(match.group("to"))
    currency = (match.group("cur") or "RUB").upper()
    currency = {"₽": "RUB", "РУБ": "RUB", "$": "USD", "€": "EUR"}.get(currency, currency)
    return salary_from, salary_to, currency


def _guess_title(text: str) -> str:
    # First non-empty line, stripped of leading hash/bullets/emoji noise.
    for line in text.splitlines():
        cleaned = re.sub(r"^[#\-\*\>\u2022\s]+", "", line).strip()
        if cleaned:
            return cleaned[:255]
    return "Telegram vacancy"


class TelegramChannelsConnector(SourceConnector):
    """Telethon-based scraper. Returns [] when not configured."""

    source_name = "telegram"

    def __init__(self) -> None:
        self._api_id_raw = (
            getattr(settings, "telegram_api_id", "") or os.getenv("TELEGRAM_API_ID", "")
        )
        self._api_hash = (
            getattr(settings, "telegram_api_hash", "") or os.getenv("TELEGRAM_API_HASH", "")
        )
        self._session_path = (
            getattr(settings, "telegram_session_path", "")
            or os.getenv("TELEGRAM_SESSION_PATH", "/data/proshli-tg")
        )
        raw_channels = getattr(settings, "tg_channels", "") or os.getenv("TG_CHANNELS", "")
        if raw_channels.strip():
            self._channels = tuple(
                part.strip().lstrip("@")
                for part in raw_channels.split(",")
                if part.strip()
            )
        else:
            self._channels = DEFAULT_TG_CHANNELS
        self._per_channel = int(os.getenv("TG_FETCH_PER_CHANNEL", "30"))
        self._lookback_hours = int(os.getenv("TG_LOOKBACK_HOURS", "24"))

    def _is_configured(self) -> bool:
        return bool(self._api_id_raw and self._api_hash)

    async def _fetch_async(self) -> list[VacancyPayload]:
        try:
            from telethon import TelegramClient  # type: ignore[import-not-found]
            from telethon.errors import ChannelPrivateError, UsernameNotOccupiedError  # type: ignore[import-not-found]
        except Exception:  # noqa: BLE001
            return []

        try:
            api_id = int(self._api_id_raw)
        except (TypeError, ValueError):
            return []

        cutoff = now_utc() - timedelta(hours=self._lookback_hours)
        results: list[VacancyPayload] = []

        client = TelegramClient(self._session_path, api_id, self._api_hash)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                # Session file not provisioned. The first run on a fresh VPS
                # needs an interactive `python -m scripts.tg_login` to log in
                # and create the .session file. Skip silently otherwise.
                return []

            for channel in self._channels:
                try:
                    async for message in client.iter_messages(channel, limit=self._per_channel):
                        msg_date = getattr(message, "date", None)
                        if msg_date is not None:
                            msg_naive = msg_date.replace(tzinfo=None)
                            if msg_naive < cutoff:
                                break
                        text = getattr(message, "message", None) or getattr(message, "raw_text", "") or ""
                        if not _looks_like_vacancy(text):
                            continue

                        salary_from, salary_to, currency = _parse_salary(text)
                        title = _guess_title(text)
                        external_id = f"tg:{channel}:{message.id}"

                        results.append(
                            VacancyPayload(
                                source=self.source_name,
                                external_id=external_id,
                                title=title[:255],
                                company=f"@{channel}"[:255],
                                location="Unknown",
                                employment_type="full-time",
                                experience_level="middle",
                                salary_from=salary_from,
                                salary_to=salary_to,
                                currency=currency,
                                description=text[:4000],
                                applications_count=0,
                                published_at=(msg_date.replace(tzinfo=None) if msg_date else now_utc()),
                            )
                        )
                except (ChannelPrivateError, UsernameNotOccupiedError):
                    continue
                except Exception:  # noqa: BLE001
                    # Per-channel failure shouldn't kill the whole sweep —
                    # channel got renamed/banned, network blip, whatever.
                    continue
        finally:
            try:
                await client.disconnect()
            except Exception:  # noqa: BLE001
                pass

        return results

    def fetch(self) -> list[VacancyPayload]:
        if not self._is_configured():
            return []
        try:
            # Telethon is async-native; spin a private loop because we are
            # called from a sync Celery task.
            return asyncio.run(self._fetch_async())
        except RuntimeError:
            # Already inside a running loop (rare in our worker setup but
            # possible under pytest-asyncio fixtures).
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._fetch_async())
            finally:
                loop.close()
        except Exception:  # noqa: BLE001
            return []
