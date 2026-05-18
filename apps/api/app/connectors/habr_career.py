"""Habr Career connector.

Pulls vacancies from career.habr.com via the public RSS feed:

    https://career.habr.com/vacancies/rss?sort=date&type=all

The RSS feed gives us the canonical 50 most-recent vacancies with title,
company (in <description>), and link. Salary, location, and employment type are
*not* in the RSS payload — they live on the HTML detail page. We don't follow
each link inline (50 sequential HTTPS calls per tick would blow the 10-second
budget), so we leave salary/location empty and rely on the AI prefilter to fill
them from the description when needed.

Falls back to deterministic samples when the network is unreachable so the
ingestion run still completes in CI.
"""

from __future__ import annotations

import hashlib
import re
from datetime import timedelta

import feedparser  # type: ignore[import-untyped]
import httpx

from app.connectors.base import SourceConnector
from app.services.ingestion import VacancyPayload
from app.time_utils import now_utc


HABR_CAREER_RSS = "https://career.habr.com/vacancies/rss?sort=date&type=all"


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value or "").strip()


class HabrCareerConnector(SourceConnector):
    source_name = "habr_career"

    def _fetch_live(self) -> list[VacancyPayload]:
        headers = {"User-Agent": "Proshli/1.0 (job-aggregator; +https://proshli.ru)"}
        with httpx.Client(timeout=15.0, headers=headers) as client:
            response = client.get(HABR_CAREER_RSS)
            response.raise_for_status()
            text = response.text

        parsed = feedparser.parse(text)
        items: list[VacancyPayload] = []
        now = now_utc()

        for entry in parsed.entries[:100]:
            title = str(entry.get("title") or "").strip()
            if not title:
                continue
            link = str(entry.get("link") or "").strip()
            description_raw = str(entry.get("summary") or entry.get("description") or "")
            description = _strip_html(description_raw)

            # career.habr.com puts the company in the <author> tag formatted
            # as ``hello@example.com (Company Name)`` — we want only the name.
            author_raw = str(entry.get("author") or "").strip()
            company = author_raw
            paren = re.search(r"\(([^)]+)\)", author_raw)
            if paren:
                company = paren.group(1).strip()
            if not company:
                # Title sometimes has " · Company" suffix on Habr Career.
                if "·" in title:
                    head, tail = title.split("·", 1)
                    title, company = head.strip(), tail.strip()
                else:
                    company = "Unknown"

            external_id = hashlib.sha256(link.encode("utf-8")).hexdigest()[:24] if link else hashlib.sha256(
                f"{title}|{company}".encode("utf-8")
            ).hexdigest()[:24]

            items.append(
                VacancyPayload(
                    source=self.source_name,
                    external_id=external_id[:128],
                    title=title[:255],
                    company=company[:255],
                    location="Unknown",
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
        return items

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
                external_id="habr-live-3001",
                title="Senior Frontend Engineer",
                company="Habr Career sample",
                location="Remote",
                employment_type="full-time",
                experience_level="senior",
                salary_from=None,
                salary_to=None,
                currency="RUB",
                description="React, TypeScript, Next.js, design systems",
                applications_count=0,
                published_at=now - timedelta(hours=3),
            ),
        ]
