"""Unit tests for :mod:`app.services.vacancy_summary`.

Exercises the LLM path with a fake Anthropic client so the suite stays
hermetic; also covers the cache-hit, no-key, and exception paths.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from app.models import Vacancy
from app.services.vacancy_summary import (
    SummaryResult,
    VacancySummaryGenerator,
    summarise_and_cache,
)


def _make_vacancy(*, ai_summary: str | None = None, description: str = "") -> Vacancy:
    """Build a Vacancy stub without touching the DB.

    ``Vacancy`` is a SQLAlchemy declarative model — instantiating it
    detached is supported, and the fields we touch (title, description,
    ai_summary, summary_generated_at) are plain Python attributes.
    """
    v = Vacancy(
        source="test",
        external_id="x",
        title="Backend Engineer",
        company="Acme",
        location="Moscow",
        description=description or "Python service serving 1M req/day.",
    )
    v.ai_summary = ai_summary
    return v


@pytest.mark.asyncio
async def test_generate_no_api_key_returns_not_ok() -> None:
    """Empty api_key → no LLM call, returns ok=False."""
    gen = VacancySummaryGenerator(api_key="")
    v = _make_vacancy()
    result = await gen.generate(vacancy=v)
    assert isinstance(result, SummaryResult)
    assert result.ok is False
    assert result.text == ""


@pytest.mark.asyncio
async def test_generate_with_fake_client_returns_summary() -> None:
    """Fake Anthropic client returns a tool_use block; we extract the summary."""
    gen = VacancySummaryGenerator(api_key="sk-test", model="claude-opus-4-6")

    class _Block:
        type = "tool_use"
        input = {"summary": "Команда платформы, FastAPI + ClickHouse."}

    class _Response:
        content = [_Block()]

    fake_messages = MagicMock()

    async def _create(**_: Any) -> _Response:
        return _Response()

    fake_messages.create = _create

    class _FakeClient:
        messages = fake_messages

    gen._client = _FakeClient()  # type: ignore[assignment]
    gen._ensure_client = lambda: _FakeClient()  # type: ignore[assignment]

    v = _make_vacancy()
    result = await gen.generate(vacancy=v)
    assert result.ok is True
    assert "FastAPI" in result.text


@pytest.mark.asyncio
async def test_generate_swallows_exception() -> None:
    """LLM exception → returns ok=False, never raises."""
    gen = VacancySummaryGenerator(api_key="sk-test", model="claude-opus-4-6")

    class _Messages:
        async def create(self, **_: Any) -> Any:
            raise RuntimeError("boom")

    class _FakeClient:
        messages = _Messages()

    gen._client = _FakeClient()  # type: ignore[assignment]
    gen._ensure_client = lambda: _FakeClient()  # type: ignore[assignment]

    v = _make_vacancy()
    result = await gen.generate(vacancy=v)
    assert result.ok is False
    assert result.text == ""


@pytest.mark.asyncio
async def test_generate_empty_summary_returns_not_ok() -> None:
    """Tool returned an empty string → ok=False (caller falls through)."""
    gen = VacancySummaryGenerator(api_key="sk-test", model="claude-opus-4-6")

    class _Block:
        type = "tool_use"
        input = {"summary": "   "}

    class _Response:
        content = [_Block()]

    class _Messages:
        async def create(self, **_: Any) -> _Response:
            return _Response()

    class _FakeClient:
        messages = _Messages()

    gen._client = _FakeClient()  # type: ignore[assignment]
    gen._ensure_client = lambda: _FakeClient()  # type: ignore[assignment]

    v = _make_vacancy()
    result = await gen.generate(vacancy=v)
    assert result.ok is False


@pytest.mark.asyncio
async def test_summarise_and_cache_returns_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """If ``ai_summary`` is already set, no LLM call happens."""
    from app.services import vacancy_summary

    called = {"n": 0}

    class _NeverCalled(VacancySummaryGenerator):
        async def generate(self, *, vacancy: Vacancy) -> SummaryResult:  # type: ignore[override]
            called["n"] += 1
            return SummaryResult(text="should-not-be-used", ok=True)

    monkeypatch.setattr(vacancy_summary, "get_summary_generator", lambda: _NeverCalled(api_key=""))

    v = _make_vacancy(ai_summary="Уже сгенерировано.")
    out = await summarise_and_cache(v)
    assert out == "Уже сгенерировано."
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_summarise_and_cache_writes_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful generation populates ``ai_summary`` and the timestamp."""
    from app.services import vacancy_summary

    class _Stub(VacancySummaryGenerator):
        async def generate(self, *, vacancy: Vacancy) -> SummaryResult:  # type: ignore[override]
            return SummaryResult(text="Готовый summary.", ok=True)

    monkeypatch.setattr(vacancy_summary, "get_summary_generator", lambda: _Stub(api_key=""))

    v = _make_vacancy(ai_summary=None)
    assert v.ai_summary is None
    assert v.summary_generated_at is None

    out = await summarise_and_cache(v)
    assert out == "Готовый summary."
    assert v.ai_summary == "Готовый summary."
    assert v.summary_generated_at is not None


@pytest.mark.asyncio
async def test_summarise_and_cache_returns_empty_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No LLM available → returns empty, leaves Vacancy untouched."""
    from app.services import vacancy_summary

    class _Stub(VacancySummaryGenerator):
        async def generate(self, *, vacancy: Vacancy) -> SummaryResult:  # type: ignore[override]
            return SummaryResult(text="", ok=False)

    monkeypatch.setattr(vacancy_summary, "get_summary_generator", lambda: _Stub(api_key=""))

    v = _make_vacancy(ai_summary=None)
    out = await summarise_and_cache(v)
    assert out == ""
    assert v.ai_summary is None
    assert v.summary_generated_at is None
