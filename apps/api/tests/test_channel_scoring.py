"""Unit tests for :mod:`app.services.channel_scoring`.

The pure-function half (``score_vacancy``, ``normalise_company``,
``_salary_score`` etc.) doesn't need a DB so the tests run hermetic.
The async helpers are exercised in a future integration test against
a seeded fixture.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import Vacancy
from app.services.channel_scoring import (
    WEIGHTS,
    ScoreBreakdown,
    _freshness_score,
    _salary_score,
    _topic_demand_score,
    normalise_company,
    score_vacancy,
)


def _make_vacancy(
    *,
    salary_from: int | None = None,
    salary_to: int | None = None,
    published_at: datetime | None = None,
    topic_id: int | None = None,
    company: str = "Acme",
) -> Vacancy:
    """Build a detached Vacancy stub for pure-function tests."""
    v = Vacancy(
        source="test",
        external_id="x",
        title="Backend Engineer",
        company=company,
        location="Moscow",
        description="…",
    )
    v.salary_from = salary_from
    v.salary_to = salary_to
    v.published_at = published_at
    v.topic_id = topic_id
    v.id = 1
    return v


def test_weights_sum_to_one() -> None:
    """The composite score is a convex combination — weights must sum to 1."""
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_normalise_company_lowercases_and_strips() -> None:
    assert normalise_company("  Yandex  ") == "yandex"
    assert normalise_company("ЯНДЕКС") == "яндекс"
    assert normalise_company(None) == ""
    assert normalise_company("") == ""


def test_salary_score_zero_when_unset() -> None:
    assert _salary_score(None, None) == 0.0
    assert _salary_score(0, 0) == 0.0


def test_salary_score_monotonic() -> None:
    """Higher salary → higher score, capped at 1.0."""
    assert _salary_score(None, 100_000) < _salary_score(None, 300_000)
    assert _salary_score(None, 300_000) < _salary_score(None, 600_000)
    # Saturates near 1.0 at the ceiling.
    assert _salary_score(None, 700_000) >= 0.99
    # Anything above the ceiling stays at 1.0.
    assert _salary_score(None, 2_000_000) == _salary_score(None, 700_000)


def test_salary_score_uses_to_then_from() -> None:
    """``salary_to`` takes precedence; falls back to ``salary_from``."""
    assert _salary_score(100_000, 500_000) == _salary_score(None, 500_000)
    assert _salary_score(300_000, None) == _salary_score(None, 300_000)


def test_freshness_score_today_is_one() -> None:
    now = datetime(2026, 5, 18, tzinfo=UTC)
    assert _freshness_score(now, now=now) == 1.0


def test_freshness_score_old_is_zero() -> None:
    now = datetime(2026, 5, 18, tzinfo=UTC)
    old = now - timedelta(days=30)
    assert _freshness_score(old, now=now) == 0.0


def test_freshness_score_midwindow() -> None:
    now = datetime(2026, 5, 18, tzinfo=UTC)
    half = now - timedelta(days=7)
    assert abs(_freshness_score(half, now=now) - 0.5) < 0.01


def test_freshness_score_none_is_zero() -> None:
    assert _freshness_score(None) == 0.0


def test_topic_demand_known_topic() -> None:
    # Python backend gets the boost.
    assert _topic_demand_score(1) > 0.5
    # Unmapped topic defaults to neutral 0.5.
    assert _topic_demand_score(999) == 0.5
    # None → neutral too.
    assert _topic_demand_score(None) == 0.5


def test_score_vacancy_combines_components() -> None:
    """Composite score is the weighted sum of components, in [0, 1]."""
    now = datetime(2026, 5, 18, tzinfo=UTC)
    v = _make_vacancy(
        salary_to=600_000,
        published_at=now,
        topic_id=1,
    )
    sc = score_vacancy(vacancy=v, prestige=0.8, now=now)

    assert isinstance(sc.breakdown, ScoreBreakdown)
    assert 0.0 <= sc.total <= 1.0
    # Recompute from components to verify the linear combination.
    expected = (
        WEIGHTS["salary"] * sc.breakdown.salary
        + WEIGHTS["prestige"] * sc.breakdown.prestige
        + WEIGHTS["freshness"] * sc.breakdown.freshness
        + WEIGHTS["topic_demand"] * sc.breakdown.topic_demand
    )
    assert abs(sc.total - expected) < 1e-9


def test_score_vacancy_prestige_clamped() -> None:
    """Prestige > 1 saturates at 1; negative clamps to 0."""
    now = datetime(2026, 5, 18, tzinfo=UTC)
    v = _make_vacancy(salary_to=500_000, published_at=now, topic_id=1)
    high = score_vacancy(vacancy=v, prestige=5.0, now=now)
    low = score_vacancy(vacancy=v, prestige=-1.0, now=now)
    assert high.breakdown.prestige == 1.0
    assert low.breakdown.prestige == 0.0


def test_score_vacancy_handles_missing_salary() -> None:
    """No salary → salary component is 0; total still well-defined."""
    now = datetime(2026, 5, 18, tzinfo=UTC)
    v = _make_vacancy(published_at=now, topic_id=1)
    sc = score_vacancy(vacancy=v, prestige=0.5, now=now)
    assert sc.breakdown.salary == 0.0
    assert 0.0 <= sc.total <= 1.0


def test_score_breakdown_json_roundtrip() -> None:
    """JSON serialisation round-trips."""
    import json as _json

    sb = ScoreBreakdown(salary=0.5, prestige=0.7, freshness=0.3, topic_demand=0.9)
    payload = sb.to_json()
    parsed = _json.loads(payload)
    assert parsed == {
        "salary": 0.5,
        "prestige": 0.7,
        "freshness": 0.3,
        "topic_demand": 0.9,
    }


def test_score_vacancy_ranking_makes_sense() -> None:
    """Higher salary + higher prestige + topic boost should outscore a basic row."""
    now = datetime(2026, 5, 18, tzinfo=UTC)

    strong = _make_vacancy(
        salary_to=600_000,
        published_at=now,
        topic_id=1,
        company="Yandex",
    )
    weak = _make_vacancy(
        salary_to=80_000,
        published_at=now - timedelta(days=10),
        topic_id=999,
        company="Unknown LLC",
    )
    strong.id = 100
    weak.id = 200

    strong_sc = score_vacancy(vacancy=strong, prestige=0.95, now=now)
    weak_sc = score_vacancy(vacancy=weak, prestige=0.0, now=now)
    assert strong_sc.total > weak_sc.total
