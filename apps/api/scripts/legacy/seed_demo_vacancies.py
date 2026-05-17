import sys
from datetime import timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine
from app.models import Vacancy
from app.time_utils import now_utc


def main() -> None:
    Base.metadata.create_all(bind=engine)
    now = now_utc()
    db = SessionLocal()
    try:
        items = [
            Vacancy(
                source="hh",
                external_id="hh-1001",
                title="Python Backend Developer",
                company="FinTech Labs",
                location="Moscow",
                employment_type="full-time",
                experience_level="middle",
                salary_from=220000,
                salary_to=320000,
                currency="RUB",
                description="FastAPI, PostgreSQL, Docker, remote option",
                published_at=now - timedelta(hours=8),
                applications_count=17,
            ),
            Vacancy(
                source="company_site",
                external_id="cmp-410",
                title="Frontend React Engineer",
                company="RetailTech",
                location="Saint Petersburg",
                employment_type="full-time",
                experience_level="senior",
                salary_from=260000,
                salary_to=370000,
                currency="RUB",
                description="TypeScript, React, GraphQL, hybrid format",
                published_at=now - timedelta(days=1),
                applications_count=8,
            ),
            Vacancy(
                source="telegram_channel",
                external_id="tg-778",
                title="Data Analyst",
                company="Growth Analytics",
                location="Remote",
                employment_type="full-time",
                experience_level="junior",
                salary_from=120000,
                salary_to=180000,
                currency="RUB",
                description="SQL, Python, BI dashboards",
                published_at=now - timedelta(days=2),
                applications_count=24,
            ),
        ]
        db.add_all(items)
        db.commit()
        print(f"Seeded {len(items)} demo vacancies.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
