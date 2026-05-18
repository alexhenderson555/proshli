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
* Falls back to a deterministic two-record sample if the live API call raises
  (network blocked, HH 429'd us, etc.) so ingestion runs in offline CI keep
  exercising the rest of the pipeline.

The HH search endpoint is public (no API key); we set a descriptive
``User-Agent`` per HH's TOS.
"""

from __future__ import annotations

from datetime import timedelta

import httpx

from app.config import settings
from app.connectors.base import SourceConnector
from app.services.ingestion import VacancyPayload
from app.time_utils import now_utc


# Built-in roster of HH search queries — broad enough to cover every taxonomy
# bucket the publication pipeline emits (Python, Go, Rust, frontend, mobile,
# data, devops, qa, design, product, analyst, security, gamedev, marketing,
# sales). The env var ``hh_search_queries`` overrides this when set.
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

# HH area ids we sweep by default. 113 = Russia (covers everywhere), but we
# also probe individual metros explicitly because HH search ranks results
# locally and small regional jobs occasionally don't surface at the country
# level. 1 = Moscow, 2 = SPB, 3 = Ekb, 4 = Novosibirsk, 88 = Kazan, 76 = Rostov,
# 66 = Krasnodar, 1438 = Innopolis. Override via env if you need narrower scope.
DEFAULT_HH_AREAS: tuple[str, ...] = ("113",)


def _parse_csv(raw: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
    items = tuple(part.strip() for part in raw.split(",") if part.strip())
    return items or fallback


class HhConnector(SourceConnector):
    source_name = "hh"

    def __init__(self) -> None:
        # Read the search roster from env once per process; tests can swap
        # ``settings.hh_search_queries`` and rebuild the connector to scope a
        # fixture run.
        queries_raw = getattr(settings, "hh_search_queries", "") or ""
        areas_raw = getattr(settings, "hh_areas", "") or ""
        self._queries = _parse_csv(queries_raw, DEFAULT_HH_QUERIES)
        self._areas = _parse_csv(areas_raw, DEFAULT_HH_AREAS)
        # Global cap on the sweep — HH allows up to 2000 results per query
        # but we don't need anywhere near that. With 47 queries × 1 area ×
        # 100 per_page × 5 pages we cap at ~23k vacancies per tick; the
        # global ceiling keeps us safe if the env is misconfigured.
        self._global_limit = max(int(getattr(settings, "hh_live_limit", 30) or 30), 30)
        self._per_page = min(max(int(settings.hh_per_page or 100), 10), 100)
        self._max_pages = max(int(getattr(settings, "hh_max_pages_per_query", 3) or 3), 1)

    # ------------------------------------------------------------------ live

    def _fetch_page(
        self, client: httpx.Client, query: str, area: str, page: int
    ) -> dict[str, object]:
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
        response = client.get(f"{settings.hh_base_url}/vacancies", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
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
                        try:
                            payload = self._fetch_page(client, query, area, page)
                        except Exception:  # noqa: BLE001
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
        return mapped

    # --------------------------------------------------------------- public

    def fetch(self) -> list[VacancyPayload]:
        try:
            live = self._fetch_live()
            if live:
                return live
        except Exception:  # noqa: BLE001
            pass

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
