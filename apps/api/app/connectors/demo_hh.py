from datetime import timedelta

import httpx

from app.config import settings
from app.connectors.base import SourceConnector
from app.services.ingestion import VacancyPayload
from app.time_utils import now_utc


class DemoHhConnector(SourceConnector):
    source_name = "hh"

    def _fetch_live(self) -> list[VacancyPayload]:
        # httpx wants ``Mapping[str, str | int | ...]``; stringify the
        # int-valued params up front so mypy sees a homogeneous type.
        params: dict[str, str] = {
            "text": settings.hh_search_text,
            "area": settings.hh_region,
            "per_page": str(settings.hh_per_page),
            "only_with_salary": "false",
            "order_by": "publication_time",
            "search_field": "name",
        }
        headers = {"User-Agent": "Otklik.ai/1.0 (job-aggregator)"}

        with httpx.Client(timeout=20.0, headers=headers) as client:
            response = client.get(f"{settings.hh_base_url}/vacancies", params=params)
            response.raise_for_status()
            payload = response.json()

        items = payload.get("items", [])
        mapped: list[VacancyPayload] = []
        for item in items:
            salary = item.get("salary") or {}
            employer = item.get("employer") or {}
            area = item.get("area") or {}
            snippet = item.get("snippet") or {}
            schedule = item.get("schedule") or {}
            experience = item.get("experience") or {}
            published_raw = item.get("published_at")
            published_at = now_utc()
            if isinstance(published_raw, str):
                try:
                    published_at = published_at.fromisoformat(published_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                except ValueError:
                    published_at = now_utc()

            mapped.append(
                VacancyPayload(
                    source=self.source_name,
                    external_id=str(item.get("id") or ""),
                    title=item.get("name") or "Unknown title",
                    company=employer.get("name") or "Unknown company",
                    location=area.get("name") or "Unknown",
                    employment_type=schedule.get("id") or "full-time",
                    experience_level=experience.get("id") or "middle",
                    salary_from=salary.get("from"),
                    salary_to=salary.get("to"),
                    currency=salary.get("currency") or "RUB",
                    description=((snippet.get("requirement") or "") + "\n" + (snippet.get("responsibility") or "")).strip(),
                    applications_count=0,
                    published_at=published_at,
                )
            )
        return mapped

    def fetch(self) -> list[VacancyPayload]:
        try:
            live = self._fetch_live()
            if live:
                return live
        except Exception:
            # Fallback to deterministic sample so ingestion/tests keep working offline.
            pass

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
