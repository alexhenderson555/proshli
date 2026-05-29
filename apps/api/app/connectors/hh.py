"""HH.ru connector — real ingestion across categories with pagination.

Replaces the toy ``DemoHhConnector`` with a sweep that:

* Iterates a configured list of professional roles / search queries (so we are
  not stuck on a single ``"python developer"`` query).
* Iterates a configured list of HH area ids (Russia = ``113`` plus selected
  metros — overridable per env so we can run a smaller search in CI/dev).
* Paginates each (query, area) tuple via ``page`` / ``per_page`` with a hard
  global cap so a misconfigured sweep cannot DoS the public API.
* Deduplicates by HH vacancy id across the sweep (rows that show up under
  multiple queries — common for cross-stack roles).
* Retries on HTTP 429 with exponential backoff (HH 429s aggressively when a
  cron tick stacks pages too fast). Failure on a single (query, area) is
  isolated — we skip and continue rather than abort the whole sweep.
* Falls back to a deterministic two-record sample if the live API call raises
  (network blocked, every query 429'd, etc.) so ingestion runs in offline CI
  keep exercising the rest of the pipeline.

The HH search endpoint is public (no API key); we set a descriptive
``User-Agent`` per HH's TOS.

Cadence
=======

``apps/workers/workers/celery_app.py`` runs two separate HH tasks:

* ``run_hh_light`` every 10 min — narrow (Moscow + Russia-wide, low page
  cap) for freshness on top-of-funnel demand. Default constructor args.
* ``run_hh_wide`` every 6 h — full 50-city × 60-query sweep with deep
  pagination. Pass ``areas=WIDE_AREAS``, ``queries=WIDE_QUERIES``,
  ``max_pages=10``, ``global_limit=2000`` to the constructor.
"""

from __future__ import annotations

import logging
import time
from datetime import timedelta

import httpx
import structlog

from app.config import settings
from app.connectors.base import SourceConnector
from app.services.ingestion import VacancyPayload
from app.time_utils import now_utc

log = structlog.get_logger(__name__)
_stdlog = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Search-query rosters
# ---------------------------------------------------------------------------
# Light sweep — keep this list lean so the every-10-min tick finishes well
# under the worker soft timeout. Splits the most-trafficked roles into
# their narrower variants ("backend" vs "data" Python) so HH's relevance
# ranking surfaces results for both intents.
DEFAULT_HH_QUERIES: tuple[str, ...] = (
    "python developer",
    "go developer",
    "rust developer",
    "java developer",
    "kotlin developer",
    "node.js developer",
    "php developer",
    "ruby developer",
    "scala developer",
    ".net developer",
    "c++ developer",
    "frontend developer",
    "react developer",
    "vue developer",
    "typescript developer",
    "fullstack developer",
    "ios developer",
    "android developer",
    "flutter developer",
    "react native developer",
    "data engineer",
    "data scientist",
    "machine learning engineer",
    "ml engineer",
    "data analyst",
    "product analyst",
    "business analyst",
    "bi analyst",
    "devops engineer",
    "sre",
    "platform engineer",
    "cloud engineer",
    "qa engineer",
    "qa automation",
    "ux designer",
    "ui designer",
    "product designer",
    "product manager",
    "project manager",
    "engineering manager",
    "security engineer",
    "infosec analyst",
    "game developer",
    "unity developer",
    "unreal developer",
    "blockchain developer",
    "solidity developer",
    "1с разработчик",
)

# Wide sweep — additional queries that are too long-tail for the 10-min
# tick but worth catching in the 6h sweep. Splits stack queries into
# domain-specific variants (Python backend / data / ML) and adds emerging
# / niche roles (Web3, AI engineer, robotics) plus PM/marketing/sales
# adjacent IT roles that pay well enough to be worth aggregating.
WIDE_HH_QUERIES: tuple[str, ...] = DEFAULT_HH_QUERIES + (
    "python backend",
    "python data",
    "java backend",
    "java spring",
    "kotlin backend",
    "fullstack engineer",
    "site reliability engineer",
    "ml ops",
    "mlops engineer",
    "computer vision",
    "nlp engineer",
    "llm engineer",
    "ai engineer",
    "prompt engineer",
    "database administrator",
    "postgres dba",
    "android kotlin",
    "swift developer",
    "ios swift",
    "embedded developer",
    "firmware engineer",
    "robotics engineer",
    "hardware engineer",
    "smart contract developer",
    "web3 developer",
    "linux engineer",
    "kubernetes engineer",
    "tech lead",
    "team lead",
    "scrum master",
    "agile coach",
    "1с программист",
    "1с франчайзи",
    "технический писатель",
    "разработчик c#",
    "frontend архитектор",
    "тимлид разработки",
    "руководитель разработки",
)

# ---------------------------------------------------------------------------
# Area rosters — HH area_id integer mapping
# ---------------------------------------------------------------------------
# 113 = Russia (covers the whole country at HH's ranking; small regional
# postings sometimes don't surface here so the wide sweep adds metros).
# Light = Moscow + Russia-wide, the freshness pair.
DEFAULT_HH_AREAS: tuple[str, ...] = ("1", "113")

# 50-city wide roster: Russian Mn-pop cities + CIS hubs. IDs from HH's
# /areas tree (https://api.hh.ru/areas). Comment beside each shows the
# city for grep-friendliness.
WIDE_HH_AREAS: tuple[str, ...] = (
    "113",   # Russia (national)
    "1",     # Москва
    "2",     # Санкт-Петербург
    "3",     # Екатеринбург
    "4",     # Новосибирск
    "1438",  # Иннополис
    "76",    # Ростов-на-Дону
    "78",    # Самара
    "88",    # Казань
    "66",    # Нижний Новгород
    "104",   # Челябинск
    "54",    # Краснодар
    "1202",  # Уфа
    "1146",  # Пермь
    "1217",  # Воронеж
    "39",    # Волгоград
    "98",    # Тюмень
    "1473",  # Тольятти
    "1124",  # Омск
    "68",    # Красноярск
    "95",    # Сочи
    "53",    # Калининград
    "22",    # Владивосток
    "1261",  # Хабаровск
    "1093",  # Иркутск
    "1078",  # Барнаул
    "1041",  # Ярославль
    "1106",  # Саратов
    "1338",  # Архангельск
    "1359",  # Брянск
    "1366",  # Владимир
    "1395",  # Вологда
    "1431",  # Ижевск
    "1454",  # Калуга
    "1490",  # Кемерово
    "1517",  # Киров
    "1543",  # Кострома
    "1577",  # Курск
    "1620",  # Липецк
    "1646",  # Магнитогорск
    "1679",  # Мурманск
    "1716",  # Набережные Челны
    "1827",  # Оренбург
    "1846",  # Пенза
    "1929",  # Рязань
    "1965",  # Смоленск
    "1985",  # Ставрополь
    "2030",  # Тверь
    "2049",  # Томск
    "2114",  # Ульяновск
    # CIS hubs — Belarus / Kazakhstan / Armenia / Georgia (relocation-friendly)
    "16",    # Минск
    "40",    # Алматы
    "159",   # Астана
    "120",   # Ереван
    "1051",  # Тбилиси
)


def _parse_csv(raw: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
    items = tuple(part.strip() for part in raw.split(",") if part.strip())
    return items or fallback


class HhConnector(SourceConnector):
    """HH.ru search connector.

    All sweep dimensions (queries, areas, per-page, max-pages, global cap)
    are constructor parameters. Defaults come from env vars and fall back
    to the ``DEFAULT_*`` rosters above so the light-sweep cron works with
    zero config. The wide-sweep task passes ``WIDE_*`` rosters explicitly
    — no env-var dance required to differentiate the two cadences.
    """

    source_name = "hh"

    # Inter-page delay. HH allows ~30 req/sec per IP but 429s aggressively
    # on bursts. Half a second is conservative; the wide sweep takes
    # ~10–15 min wall-clock at this rate, which is fine for a 6h cadence.
    _PAGE_SLEEP_S: float = 0.5
    # Exponential backoff cap for 429 retries. We retry the same page up
    # to ``_MAX_RETRIES`` times with ``2 ** attempt`` seconds between,
    # then skip the (query, area) pair entirely rather than blocking the
    # whole sweep on one stuck combination.
    _MAX_RETRIES: int = 3

    def __init__(
        self,
        *,
        queries: tuple[str, ...] | None = None,
        areas: tuple[str, ...] | None = None,
        per_page: int | None = None,
        max_pages: int | None = None,
        global_limit: int | None = None,
    ) -> None:
        # Caller (e.g. ``run_hh_wide`` Celery task) wins; env vars come
        # next; built-in defaults last. ``None`` from the caller means
        # "use whatever env/default decides".
        if queries is not None:
            self._queries = queries
        else:
            queries_raw = getattr(settings, "hh_search_queries", "") or ""
            self._queries = _parse_csv(queries_raw, DEFAULT_HH_QUERIES)

        if areas is not None:
            self._areas = areas
        else:
            areas_raw = getattr(settings, "hh_areas", "") or ""
            self._areas = _parse_csv(areas_raw, DEFAULT_HH_AREAS)

        # Global cap on the sweep — HH allows up to 2000 results per query
        # but the wide sweep at 60 queries × 50 areas would explode without
        # a ceiling. Light sweep keeps the 30-row default for speed.
        env_limit = int(getattr(settings, "hh_live_limit", 30) or 30)
        self._global_limit = global_limit if global_limit is not None else env_limit

        env_per_page = int(settings.hh_per_page or 100)
        chosen_per_page = per_page if per_page is not None else env_per_page
        self._per_page = min(max(chosen_per_page, 10), 100)

        env_max_pages = int(getattr(settings, "hh_max_pages_per_query", 3) or 3)
        chosen_max_pages = max_pages if max_pages is not None else env_max_pages
        self._max_pages = max(chosen_max_pages, 1)

    # ------------------------------------------------------------------ live

    def _fetch_page(
        self, client: httpx.Client, query: str, area: str, page: int
    ) -> dict[str, object]:
        """One HH /vacancies search call with retry-on-429.

        Returns ``{}`` after exhausting retries; the outer loop treats an
        empty payload as a normal end-of-pages signal and moves to the
        next (query, area) pair.
        """
        params: dict[str, str] = {
            "text": query,
            "area": area,
            "per_page": str(self._per_page),
            "page": str(page),
            "only_with_salary": "false",
            "order_by": "publication_time",
            # HH groups duplicate postings under a single ``id`` when this is
            # set — saves us a little dedup work downstream.
            "clusters": "false",
            # Exclude archived (already-filled) rows.
            "archived": "false",
        }

        for attempt in range(self._MAX_RETRIES + 1):
            try:
                response = client.get(
                    f"{settings.hh_base_url}/vacancies", params=params
                )
            except httpx.HTTPError as exc:
                # Network-level failure (DNS / timeout / connection reset).
                # Same retry shape as 429 — the next attempt might succeed.
                log.warning(
                    "hh.fetch_network_error",
                    query=query,
                    area=area,
                    page=page,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt >= self._MAX_RETRIES:
                    return {}
                time.sleep(2 ** attempt)
                continue

            if response.status_code == 429:
                # HH's rate-limit headers don't always include
                # ``Retry-After``; exponential backoff is the safe default.
                log.warning(
                    "hh.fetch_429",
                    query=query,
                    area=area,
                    page=page,
                    attempt=attempt,
                )
                if attempt >= self._MAX_RETRIES:
                    return {}
                time.sleep(2 ** attempt)
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                _stdlog.warning(
                    "hh.fetch_http_error query=%r area=%r page=%d status=%d",
                    query,
                    area,
                    page,
                    response.status_code,
                )
                # Non-429 errors are usually permanent for this combo
                # (e.g. 400 on a malformed query). Bail without retry.
                _ = exc  # keep the local for the log message
                return {}

            data = response.json()
            if isinstance(data, dict):
                return data
            return {}
        return {}

    def _map_item(self, item: dict[str, object]) -> VacancyPayload:
        salary = (item.get("salary") if isinstance(item.get("salary"), dict) else {}) or {}
        employer = (item.get("employer") if isinstance(item.get("employer"), dict) else {}) or {}
        area = (item.get("area") if isinstance(item.get("area"), dict) else {}) or {}
        snippet = (item.get("snippet") if isinstance(item.get("snippet"), dict) else {}) or {}
        schedule = (item.get("schedule") if isinstance(item.get("schedule"), dict) else {}) or {}
        experience = (
            item.get("experience") if isinstance(item.get("experience"), dict) else {}
        ) or {}

        published_raw = item.get("published_at")
        published_at = now_utc()
        if isinstance(published_raw, str):
            try:
                published_at = published_at.fromisoformat(
                    published_raw.replace("Z", "+00:00")
                ).replace(tzinfo=None)
            except ValueError:
                published_at = now_utc()

        return VacancyPayload(
            source=self.source_name,
            external_id=str(item.get("id") or "")[:128],
            title=str(item.get("name") or "Unknown title")[:255],
            company=str(employer.get("name") or "Unknown company")[:255],
            location=str(area.get("name") or "Unknown")[:128],
            employment_type=str(schedule.get("id") or "full-time"),
            experience_level=str(experience.get("id") or "middle"),
            salary_from=salary.get("from") if isinstance(salary.get("from"), int) else None,
            salary_to=salary.get("to") if isinstance(salary.get("to"), int) else None,
            currency=str(salary.get("currency") or "RUB"),
            description=(
                (str(snippet.get("requirement") or "") + "\n" + str(snippet.get("responsibility") or ""))
                .strip()[:4000]
            ),
            applications_count=0,
            published_at=published_at,
        )

    def _fetch_live(self) -> list[VacancyPayload]:
        seen_ids: set[str] = set()
        mapped: list[VacancyPayload] = []
        # HH.ru requires a User-Agent with a contact, per their API TOS — bare
        # generic UAs are 403'd from RU cloud IP ranges.
        # https://api.hh.ru/openapi/redoc#section/Obshaya-informaciya/Trebovaniya-k-User-Agent
        headers = {
            "User-Agent": "Proshli/1.0 (proshli.ru; contact@proshli.ru)",
            "Accept": "application/json",
            "HH-User-Agent": "Proshli/1.0 (proshli.ru; contact@proshli.ru)",
        }

        with httpx.Client(timeout=20.0, headers=headers) as client:
            for query in self._queries:
                for area in self._areas:
                    for page in range(self._max_pages):
                        payload = self._fetch_page(client, query, area, page)
                        if not payload:
                            # Either retries exhausted (429/network) or a
                            # 4xx — skip the rest of this (query, area).
                            break
                        items = payload.get("items") or []
                        if not isinstance(items, list) or not items:
                            break
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            ext_id = str(item.get("id") or "")
                            if not ext_id or ext_id in seen_ids:
                                continue
                            seen_ids.add(ext_id)
                            mapped.append(self._map_item(item))
                            if len(mapped) >= self._global_limit:
                                return mapped
                        # HH returns ``pages`` (total pages available). Stop
                        # early to avoid empty extra round-trips.
                        total_pages = payload.get("pages")
                        if isinstance(total_pages, int) and page + 1 >= total_pages:
                            break
                        # Sleep between pages — see ``_PAGE_SLEEP_S``.
                        time.sleep(self._PAGE_SLEEP_S)
        return mapped

    # --------------------------------------------------------------- public

    def fetch(self) -> list[VacancyPayload]:
        try:
            live = self._fetch_live()
            if live:
                return live
        except Exception as exc:  # noqa: BLE001
            log.warning("hh.fetch_failed_top_level", error=str(exc))

        # Offline fallback — deterministic so CI/tests keep working.
        now = now_utc()
        return [
            VacancyPayload(
                source=self.source_name,
                external_id="hh-live-2001",
                title="Senior Python Engineer",
                company="ScaleHub",
                location="Moscow",
                employment_type="full-time",
                experience_level="senior",
                salary_from=300000,
                salary_to=450000,
                currency="RUB",
                description="Python, FastAPI, PostgreSQL, Kafka, leadership",
                applications_count=5,
                published_at=now - timedelta(hours=5),
            ),
            VacancyPayload(
                source=self.source_name,
                external_id="hh-live-2002",
                title="Middle Data Analyst",
                company="RetailMetrics",
                location="Remote",
                employment_type="full-time",
                experience_level="middle",
                salary_from=170000,
                salary_to=240000,
                currency="RUB",
                description="SQL, Python, BI, A/B testing",
                applications_count=12,
                published_at=now - timedelta(hours=16),
            ),
        ]
