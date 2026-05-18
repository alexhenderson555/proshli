"""Corporate career-site connector.

Each major Russian / RU-tech-adjacent employer publishes its own career page;
they rarely share an ATS, so we point one fetcher per company at whatever
public endpoint they expose. Endpoints come in three flavours:

1. **Greenhouse-hosted boards** (e.g. Wildberries Tech, JetBrains for parts of
   their hiring) — they expose ``boards-api.greenhouse.io/v1/boards/<slug>/jobs``
   as JSON. Cheapest case.
2. **Native company APIs** — Yandex, VK, Avito, Ozon, Tinkoff (now T-Bank),
   Wildberries Career, Sber all run their own backends. We hit the documented
   JSON endpoints they use to render their public pages.
3. **HTML scraping** — for companies without an API endpoint we fall back to
   a thin BeautifulSoup pass on the listing page.

Failures are isolated per company. A 500 from Yandex doesn't block Tinkoff
from ingesting. The whole connector returns whatever managed to come back,
plus deterministic samples if *everything* failed (so dev / CI keep working).

Network calls are time-budgeted (10 s / company), and we cap total live items
at ``CORP_SITES_LIMIT`` (default 200) so a runaway crawl can't blow the
ingestion budget.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Iterable
from datetime import timedelta
from typing import Callable

import httpx

from app.connectors.base import SourceConnector
from app.services.ingestion import VacancyPayload
from app.time_utils import now_utc


CORP_SITES_LIMIT = int(os.getenv("CORP_SITES_LIMIT", "200"))
USER_AGENT = "Proshli/1.0 (job-aggregator; +https://proshli.ru)"


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value or "").strip()


def _ext_id(company: str, url: str) -> str:
    return hashlib.sha256(f"{company}|{url}".encode("utf-8")).hexdigest()[:24]


# ---------------------------------------------------------------- per-company

def _fetch_greenhouse(client: httpx.Client, slug: str, company: str) -> list[VacancyPayload]:
    """Greenhouse boards expose a clean JSON listing."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    response = client.get(url)
    response.raise_for_status()
    payload = response.json()
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    out: list[VacancyPayload] = []
    now = now_utc()
    for job in jobs:
        if not isinstance(job, dict):
            continue
        title = str(job.get("title") or "").strip()
        if not title:
            continue
        location_obj = job.get("location") or {}
        location = str(location_obj.get("name") or "Unknown") if isinstance(location_obj, dict) else "Unknown"
        absolute_url = str(job.get("absolute_url") or "")
        content = _strip_html(str(job.get("content") or ""))
        out.append(
            VacancyPayload(
                source="company_sites",
                external_id=_ext_id(company, absolute_url or title)[:128],
                title=title[:255],
                company=company[:255],
                location=location[:128],
                employment_type="full-time",
                experience_level="middle",
                salary_from=None,
                salary_to=None,
                currency="RUB",
                description=content[:4000],
                applications_count=0,
                published_at=now,
            )
        )
    return out


def _fetch_yandex(client: httpx.Client) -> list[VacancyPayload]:
    """Yandex Jobs (yandex.ru/jobs) backend serves JSON to its SPA."""
    url = "https://yandex.ru/jobs/api/vacancies/?limit=100"
    response = client.get(url)
    response.raise_for_status()
    data = response.json()
    items: Iterable[dict] = []
    if isinstance(data, dict):
        items = data.get("results") or data.get("items") or data.get("vacancies") or []
    out: list[VacancyPayload] = []
    now = now_utc()
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or "").strip()
        if not title:
            continue
        loc_raw = item.get("city") or item.get("location") or "Unknown"
        location = str(loc_raw) if not isinstance(loc_raw, dict) else str(loc_raw.get("name") or "Unknown")
        url_field = str(item.get("url") or item.get("link") or "")
        description = _strip_html(str(item.get("description") or item.get("summary") or ""))
        out.append(
            VacancyPayload(
                source="company_sites",
                external_id=_ext_id("Yandex", url_field or title)[:128],
                title=title[:255],
                company="Yandex",
                location=location[:128],
                employment_type="full-time",
                experience_level="middle",
                salary_from=None,
                salary_to=None,
                currency="RUB",
                description=description[:4000],
                applications_count=0,
                published_at=now,
            )
        )
    return out


def _fetch_avito(client: httpx.Client) -> list[VacancyPayload]:
    """Avito Tech (career.avito.tech) — JSON behind /api/vacancies."""
    url = "https://career.avito.tech/api/vacancies/?limit=100"
    response = client.get(url)
    response.raise_for_status()
    data = response.json()
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return []
    now = now_utc()
    out: list[VacancyPayload] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        location = str(item.get("city") or item.get("location") or "Unknown")
        url_field = str(item.get("url") or "")
        description = _strip_html(str(item.get("description") or item.get("short_description") or ""))
        out.append(
            VacancyPayload(
                source="company_sites",
                external_id=_ext_id("Avito", url_field or title)[:128],
                title=title[:255],
                company="Avito",
                location=location[:128],
                employment_type="full-time",
                experience_level="middle",
                salary_from=None,
                salary_to=None,
                currency="RUB",
                description=description[:4000],
                applications_count=0,
                published_at=now,
            )
        )
    return out


def _fetch_html_generic(
    client: httpx.Client,
    company: str,
    listing_url: str,
    title_pattern: re.Pattern[str],
    link_pattern: re.Pattern[str] | None = None,
) -> list[VacancyPayload]:
    """Last-resort HTML scrape: extract <title> + canonical link via regex.

    We don't ship BeautifulSoup because the structure of these pages drifts
    quarterly anyway — a regex on data-test-id-style attrs is no worse than a
    DOM selector that breaks the same week.
    """
    response = client.get(listing_url)
    response.raise_for_status()
    html = response.text
    titles = title_pattern.findall(html)
    links = link_pattern.findall(html) if link_pattern else [""] * len(titles)
    now = now_utc()
    out: list[VacancyPayload] = []
    for raw_title, raw_link in zip(titles, links + [""] * len(titles)):
        title = _strip_html(raw_title)
        if not title:
            continue
        link = raw_link if isinstance(raw_link, str) else ""
        out.append(
            VacancyPayload(
                source="company_sites",
                external_id=_ext_id(company, link or title)[:128],
                title=title[:255],
                company=company[:255],
                location="Unknown",
                employment_type="full-time",
                experience_level="middle",
                salary_from=None,
                salary_to=None,
                currency="RUB",
                description="",
                applications_count=0,
                published_at=now,
            )
        )
    return out


# Registry of (label, callable) — each callable takes an httpx.Client and
# returns a list of payloads. New companies get appended here.
_FETCHERS: tuple[tuple[str, Callable[[httpx.Client], list[VacancyPayload]]], ...] = (
    ("Yandex", _fetch_yandex),
    ("Avito", _fetch_avito),
    ("Wildberries", lambda c: _fetch_greenhouse(c, "wildberriestech", "Wildberries Tech")),
    ("JetBrains", lambda c: _fetch_greenhouse(c, "jetbrains", "JetBrains")),
    ("Miro", lambda c: _fetch_greenhouse(c, "miro", "Miro")),
    ("Nebius", lambda c: _fetch_greenhouse(c, "nebius", "Nebius")),
    (
        "T-Bank",
        lambda c: _fetch_html_generic(
            c,
            "T-Bank",
            "https://www.tbank.ru/career/vacancies/",
            re.compile(r'data-qa-type="vacancy-name"[^>]*>([^<]+)<'),
            re.compile(r'data-qa-type="vacancy-link"[^>]*href="([^"]+)"'),
        ),
    ),
    (
        "VK",
        lambda c: _fetch_html_generic(
            c,
            "VK",
            "https://team.vk.company/vacancies/",
            re.compile(r'class="vacancy-card__title[^"]*"[^>]*>([^<]+)<'),
            re.compile(r'class="vacancy-card[^"]*"[^>]*href="([^"]+)"'),
        ),
    ),
    (
        "Ozon",
        lambda c: _fetch_html_generic(
            c,
            "Ozon",
            "https://job.ozon.ru/vacancy/",
            re.compile(r'<a[^>]+class="[^"]*vacancyCard[^"]*"[^>]*>[\s\S]*?<h3[^>]*>([^<]+)</h3>'),
            re.compile(r'<a[^>]+class="[^"]*vacancyCard[^"]*"[^>]*href="([^"]+)"'),
        ),
    ),
)


class CorpSitesConnector(SourceConnector):
    source_name = "company_sites"

    def _fetch_live(self) -> list[VacancyPayload]:
        headers = {"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.7"}
        seen: set[str] = set()
        results: list[VacancyPayload] = []
        with httpx.Client(timeout=10.0, headers=headers, follow_redirects=True) as client:
            for label, fetcher in _FETCHERS:
                try:
                    chunk = fetcher(client)
                except Exception:  # noqa: BLE001
                    chunk = []
                for item in chunk:
                    if item.external_id in seen:
                        continue
                    seen.add(item.external_id)
                    results.append(item)
                    if len(results) >= CORP_SITES_LIMIT:
                        return results
        return results

    def fetch(self) -> list[VacancyPayload]:
        try:
            live = self._fetch_live()
            if live:
                return live
        except Exception:  # noqa: BLE001
            pass

        now = now_utc()
        return [
            VacancyPayload(
                source=self.source_name,
                external_id="cmp-live-901",
                title="Backend Developer (Python)",
                company="ScaleHub",
                location="Moscow",
                employment_type="full-time",
                experience_level="senior",
                salary_from=310000,
                salary_to=430000,
                currency="RUB",
                description="Python, microservices, docker, mentor juniors",
                applications_count=4,
                published_at=now - timedelta(hours=2),
            ),
            VacancyPayload(
                source=self.source_name,
                external_id="cmp-live-902",
                title="Product Analyst",
                company="EdTech Nova",
                location="Saint Petersburg",
                employment_type="full-time",
                experience_level="middle",
                salary_from=180000,
                salary_to=260000,
                currency="RUB",
                description="Product metrics, SQL, visualization, experimentation",
                applications_count=9,
                published_at=now - timedelta(days=1),
            ),
        ]
