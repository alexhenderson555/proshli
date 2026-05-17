from datetime import timedelta

from app.connectors.base import SourceConnector
from app.services.ingestion import VacancyPayload
from app.time_utils import now_utc


class DemoCompanySitesConnector(SourceConnector):
    source_name = "company_sites"

    def fetch(self) -> list[VacancyPayload]:
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
