import json
import re
from dataclasses import dataclass
from datetime import datetime

from app.models import IngestRun, RawVacancy, Vacancy
from app.time_utils import now_utc
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass
class VacancyPayload:
    source: str
    external_id: str
    title: str
    company: str
    location: str
    employment_type: str
    experience_level: str
    salary_from: int | None
    salary_to: int | None
    currency: str
    description: str
    applications_count: int
    published_at: datetime


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().strip())


def build_fingerprint(item: VacancyPayload) -> str:
    return " | ".join(
        [
            normalize_text(item.title),
            normalize_text(item.company),
            normalize_text(item.location),
        ]
    )


def vacancy_exists(db: Session, item: VacancyPayload) -> bool:
    by_source = db.scalar(
        select(Vacancy).where(Vacancy.source == item.source).where(Vacancy.external_id == item.external_id)
    )
    if by_source:
        return True

    # Soft dedupe across sources.
    all_recent = db.scalars(
        select(Vacancy).where(Vacancy.published_at >= now_utc().replace(hour=0, minute=0, second=0))
    ).all()
    candidate_fp = build_fingerprint(item)
    for existing in all_recent:
        existing_fp = " | ".join(
            [
                normalize_text(existing.title),
                normalize_text(existing.company),
                normalize_text(existing.location),
            ]
        )
        if existing_fp == candidate_fp:
            return True
    return False


def store_raw(db: Session, item: VacancyPayload) -> None:
    raw = RawVacancy(
        source=item.source,
        external_id=item.external_id,
        payload_json=json.dumps(item.__dict__, default=str, ensure_ascii=False),
        ingested_at=now_utc(),
    )
    db.add(raw)


def persist_vacancy(db: Session, item: VacancyPayload) -> None:
    vacancy = Vacancy(
        source=item.source,
        external_id=item.external_id,
        title=item.title,
        company=item.company,
        location=item.location,
        employment_type=item.employment_type,
        experience_level=item.experience_level,
        salary_from=item.salary_from,
        salary_to=item.salary_to,
        currency=item.currency,
        description=item.description,
        applications_count=item.applications_count,
        published_at=item.published_at,
    )
    db.add(vacancy)


def run_ingestion(db: Session, source_name: str, payloads: list[VacancyPayload]) -> IngestRun:
    run = IngestRun(source=source_name, fetched_count=len(payloads), started_at=now_utc())
    db.add(run)
    db.commit()
    db.refresh(run)

    inserted = 0
    deduped = 0
    for item in payloads:
        store_raw(db, item)
        if vacancy_exists(db, item):
            deduped += 1
            continue
        persist_vacancy(db, item)
        inserted += 1

    run.inserted_count = inserted
    run.deduped_count = deduped
    run.finished_at = now_utc()
    db.commit()
    db.refresh(run)
    return run
