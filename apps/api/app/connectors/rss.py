import hashlib
from datetime import timedelta

import feedparser
import httpx

from app.config import settings
from app.connectors.base import SourceConnector
from app.services.ingestion import VacancyPayload
from app.time_utils import now_utc


class RssConnector(SourceConnector):
    source_name = "rss"

    def fetch(self) -> list[VacancyPayload]:
        if not settings.rss_source_urls:
            return []

        now = now_utc()
        items: list[VacancyPayload] = []
        for source_url in settings.rss_source_urls:
            parsed = None
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(source_url)
                if response.status_code >= 400:
                    response = None
                if response is not None:
                    parsed = feedparser.parse(response.text)
            except Exception:  # noqa: BLE001
                parsed = None

            if parsed is None:
                continue

            for entry in parsed.entries[:100]:
                title = (entry.get("title") or "Untitled vacancy").strip()
                summary = (entry.get("summary") or entry.get("description") or "").strip()
                link = (entry.get("link") or "").strip()
                company = (entry.get("author") or entry.get("source", {}).get("title") or "Unknown").strip()

                external_id = hashlib.sha256(f"{source_url}|{link}|{title}".encode("utf-8")).hexdigest()[:24]
                items.append(
                    VacancyPayload(
                        source=self.source_name,
                        external_id=external_id,
                        title=title[:255],
                        company=company[:255],
                        location="Unknown",
                        employment_type="full-time",
                        experience_level="middle",
                        salary_from=None,
                        salary_to=None,
                        currency="RUB",
                        description=summary[:4000],
                        applications_count=0,
                        published_at=now - timedelta(minutes=1),
                    )
                )
        return items
