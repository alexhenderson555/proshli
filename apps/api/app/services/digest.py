from dataclasses import dataclass

from app.models import DigestPreference, Resume, User, Vacancy
from sqlalchemy import desc, select
from sqlalchemy.orm import Session


@dataclass
class RankedVacancy:
    vacancy: Vacancy
    reason: str


def user_skills(db: Session, user: User) -> set[str]:
    latest_resume = db.scalar(
        select(Resume).where(Resume.user_id == user.id).order_by(desc(Resume.created_at)).limit(1)
    )
    if not latest_resume or not latest_resume.parsed_skills:
        return set()
    return {s.strip().lower() for s in latest_resume.parsed_skills.split(",") if s.strip()}


def rank_for_user(db: Session, user: User, limit: int = 10) -> list[RankedVacancy]:
    skills = user_skills(db, user)
    vacancies = db.scalars(select(Vacancy).order_by(desc(Vacancy.published_at)).limit(60)).all()

    ranked: list[tuple[int, RankedVacancy]] = []
    for vacancy in vacancies:
        score = 0
        reasons: list[str] = []
        desc_text = (vacancy.description or "").lower()

        matched = [skill for skill in skills if skill in desc_text]
        if matched:
            score += len(matched) * 10
            reasons.append(f"Совпадение навыков: {', '.join(matched[:3])}")

        if vacancy.applications_count <= 10:
            score += 3
            reasons.append("Низкая конкуренция по числу откликов")

        if "remote" in vacancy.location.lower() or "remote" in desc_text or "удален" in desc_text:
            score += 2
            reasons.append("Есть признаки удаленного формата")

        if score > 0:
            ranked.append((score, RankedVacancy(vacancy=vacancy, reason="; ".join(reasons))))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [entry for _, entry in ranked[:limit]]


def digest_channels(pref: DigestPreference) -> list[str]:
    channels: list[str] = []
    if pref.via_telegram:
        channels.append("telegram")
    if pref.via_email:
        channels.append("email")
    return channels
