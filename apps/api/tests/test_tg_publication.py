"""Unit tests for the TG-publication prefilter + renderer.

The renderer is a pure function so we don't need a DB at all — these
tests assert the filter gates from the spec and check that the rendered
post is escape-safe + within the Telegram size cap.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest
from app.services.tg_publication import (
    _AI_SUMMARY_MAX_CHARS,
    _TG_MAX_CHARS,
    FilterDecision,
    passes_filter_rules,
    render_post,
)


@dataclass
class FakeVacancy:
    """Stand-in for ``app.models.Vacancy`` — only the renderer-relevant fields.

    Using a dataclass means we don't have to spin up SQLAlchemy or hit
    a database to test the formatter; the renderer reads attributes
    structurally and doesn't care about the runtime type.
    """

    id: int = 42
    source: str = "hh.ru"
    title: str = "Senior Python Engineer"
    company: str = "Yandex"
    location: str = "Москва"
    employment_type: str = "full-time"
    experience_level: str = "senior"
    salary_from: int | None = 300_000
    salary_to: int | None = 450_000
    currency: str = "RUB"
    description: str = (
        "Большая команда продуктового бэкенда. Python 3.12, FastAPI, "
        "PostgreSQL, k8s. От senior — 4+ года опыта, ML интеграции."
    )
    published_at: datetime = datetime(2026, 5, 18)
    topic_id: int | None = None
    classified_at: datetime | None = None


def test_filter_accepts_well_formed_vacancy() -> None:
    """Long description + non-recruiter company + salary present → accept."""
    decision = passes_filter_rules(
        description="a" * 120,
        company="Yandex",
        salary_from=200_000,
        salary_to=350_000,
    )
    assert decision == FilterDecision(ok=True)


def test_filter_rejects_short_description() -> None:
    decision = passes_filter_rules(
        description="Hire backend dev",
        company="Yandex",
        salary_from=200_000,
        salary_to=350_000,
    )
    assert decision.ok is False
    assert decision.reason == "description_too_short"


@pytest.mark.parametrize(
    "company",
    ["Кадровое агентство Дельта", "Best Recruit Agency", "HR Partner Group"],
)
def test_filter_rejects_recruiter_agency(company: str) -> None:
    """Recruiter / staffing companies are kept off the firehose."""
    decision = passes_filter_rules(
        description="x" * 200,
        company=company,
        salary_from=100_000,
        salary_to=200_000,
    )
    assert decision.ok is False
    assert decision.reason == "recruiter_agency"


def test_filter_rejects_no_salary_and_no_grade_keyword() -> None:
    """Without salary AND without grade keyword the post has no signal."""
    decision = passes_filter_rules(
        description="Хорошая команда " * 20,  # 320 chars, but no "senior" etc.
        company="Yandex",
        salary_from=None,
        salary_to=None,
    )
    assert decision.ok is False
    assert decision.reason == "no_signal"


def test_filter_accepts_no_salary_with_grade_keyword() -> None:
    """Grade keyword in the description is enough to clear the signal gate."""
    decision = passes_filter_rules(
        description="Ищем senior backend на FastAPI " * 5,
        company="Yandex",
        salary_from=None,
        salary_to=None,
    )
    assert decision.ok is True


def test_render_post_contains_expected_fields() -> None:
    """The rendered HTML carries title, company, salary, CTA, source."""
    vacancy = FakeVacancy()
    post = render_post(
        vacancy=vacancy,  # type: ignore[arg-type]
        ai_summary="Решаешь задачи продуктового масштаба.",
        top_skills=["Python", "FastAPI", "PostgreSQL"],
        base_url="https://proshli.ru",
        locale="ru",
    )
    assert "<b>Senior Python Engineer</b>" in post
    assert "Yandex" in post
    assert "300 000 – 450 000 ₽" in post
    assert "Москва" in post
    assert "Python · FastAPI · PostgreSQL" in post
    assert "https://proshli.ru/ru/vacancies/42" in post
    assert "Источник: hh.ru" in post


def test_render_post_escapes_html() -> None:
    """Adversarial inputs must not break the layout or inject markup."""
    vacancy = FakeVacancy(
        title="<script>alert(1)</script>",
        company="Foo & Bar",
        location="<b>Москва</b>",
    )
    post = render_post(
        vacancy=vacancy,  # type: ignore[arg-type]
        ai_summary="Plain summary",
        top_skills=["A<B"],
        base_url="https://proshli.ru",
    )
    # Raw HTML tags from user input must be escaped.
    assert "<script>" not in post
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in post
    assert "Foo &amp; Bar" in post
    assert "A&lt;B" in post


def test_render_post_truncates_summary() -> None:
    """An over-long AI summary gets cropped, not rejected."""
    vacancy = FakeVacancy()
    long_summary = "очень длинное описание " * 30  # ~660 chars
    post = render_post(
        vacancy=vacancy,  # type: ignore[arg-type]
        ai_summary=long_summary,
        top_skills=["Python"],
        base_url="https://proshli.ru",
    )
    # Summary is capped at _AI_SUMMARY_MAX_CHARS plus an ellipsis marker.
    # The full body still has to be under the TG hard cap.
    assert len(post) <= _TG_MAX_CHARS
    assert "…" in post
    assert len(long_summary) > _AI_SUMMARY_MAX_CHARS


def test_render_post_handles_missing_salary() -> None:
    """An em-dash is used when salary is unknown — matches RU TG convention."""
    vacancy = FakeVacancy(salary_from=None, salary_to=None)
    post = render_post(
        vacancy=vacancy,  # type: ignore[arg-type]
        ai_summary="Команда продукта.",
        top_skills=["Python"],
        base_url="https://proshli.ru",
    )
    assert "💰 — · 📍" in post
