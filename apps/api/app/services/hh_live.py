"""Live hh.ru fetch helper.

Used by ``GET /vacancies`` to enrich locally-indexed results with the public
hh.ru search feed.  Failures fall back to an empty list — never block the
core listing — and synthetic negative ids keep FE routing stable when the
same job hasn't yet been ingested locally.
"""

from __future__ import annotations

import html
import re
from datetime import datetime

import httpx
from app.config import settings
from app.schemas import VacancyOut
from app.time_utils import now_utc


def _clean_hh_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = html.unescape(value)
    normalized = re.sub(r"</?highlighttext>", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"<[^>]+>", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


async def fetch_live_hh_vacancies(
    location: str | None,
    stack: str | None,
    level: str | None,
    min_salary: int | None,
    work_mode: str | None,
    max_age_days: int | None,
) -> list[VacancyOut]:
    if not settings.hh_live_enabled:
        return []

    text_parts: list[str] = [settings.hh_search_text]
    if stack:
        text_parts.append(stack)
    if level:
        text_parts.append(level)
    if work_mode == "remote":
        text_parts.append("удаленно")
    elif work_mode == "hybrid":
        text_parts.append("гибрид")
    elif work_mode == "office":
        text_parts.append("офис")

    params: dict[str, str | int] = {
        "text": " ".join(part for part in text_parts if part).strip(),
        "area": settings.hh_region,
        "per_page": min(settings.hh_live_limit, 100),
        "order_by": "publication_time",
    }
    if location:
        params["search_field"] = "name"
        params["text"] = f"{params['text']} {location}".strip()
    if min_salary is not None:
        params["salary"] = min_salary
    if max_age_days is not None:
        params["period"] = max(1, min(max_age_days, 30))

    headers = {"User-Agent": "Proshli/1.0 (job-aggregator)"}
    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        response = await client.get(f"{settings.hh_base_url}/vacancies", params=params)
        response.raise_for_status()
        payload = response.json()

    items = payload.get("items") or []
    now = now_utc()
    mapped: list[VacancyOut] = []
    for item in items:
        salary = item.get("salary") or {}
        employer = item.get("employer") or {}
        area = item.get("area") or {}
        snippet = item.get("snippet") or {}
        schedule = item.get("schedule") or {}
        experience = item.get("experience") or {}
        published_raw = item.get("published_at")
        published_at = now
        if isinstance(published_raw, str):
            try:
                published_at = datetime.fromisoformat(
                    published_raw.replace("Z", "+00:00")
                ).replace(tzinfo=None)
            except ValueError:
                published_at = now

        raw_id = str(item.get("id") or "0")
        synthetic_id = (
            -abs(int(raw_id))
            if raw_id.isdigit()
            else -(abs(hash(raw_id)) % 2_000_000_000)
        )
        description = (
            _clean_hh_text(snippet.get("requirement"))
            + "\n"
            + _clean_hh_text(snippet.get("responsibility"))
        ).strip()
        mapped.append(
            VacancyOut(
                id=synthetic_id,
                source="hh_live",
                title=_clean_hh_text(item.get("name")) or "Unknown title",
                company=_clean_hh_text(employer.get("name")) or "Unknown company",
                location=_clean_hh_text(area.get("name")) or "Unknown",
                employment_type=schedule.get("id") or "full-time",
                experience_level=experience.get("id") or "middle",
                salary_from=salary.get("from"),
                salary_to=salary.get("to"),
                currency=salary.get("currency") or "RUB",
                description=description,
                published_at=published_at,
                applications_count=0,
                is_active=True,
                archived_at=None,
                is_deleted=False,
                deleted_at=None,
                is_promoted=False,
                promotion_expires_at=None,
                external_url=item.get("alternate_url"),
            )
        )
    return mapped
