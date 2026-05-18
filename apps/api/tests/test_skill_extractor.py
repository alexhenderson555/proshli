"""Unit tests for :mod:`app.services.skill_extractor`.

Covers the pure dictionary path (no LLM dependency), word-boundary
protection against substring false positives, dedupe / ordering, the
empty-input branch, and ``_merge_dedup``. The LLM path is exercised
via a fake client so the test stays hermetic — no ``ANTHROPIC_API_KEY``
needed in CI.
"""

from __future__ import annotations

from typing import Any

import pytest
from app.services.skill_extractor import (
    ExtractionResult,
    SkillExtractor,
    _merge_dedup,
    extract_skills_dictionary,
)


def test_dictionary_finds_framework_language_db() -> None:
    """A standard backend description surfaces FastAPI/PostgreSQL/Python."""
    text = "Большая команда продуктового бэкенда. Python 3.12, FastAPI, PostgreSQL, k8s."
    out = extract_skills_dictionary(text, limit=8)
    assert "FastAPI" in out
    assert "PostgreSQL" in out
    assert "Python" in out
    assert "Kubernetes" in out
    # Frameworks come before languages per dictionary ordering.
    assert out.index("FastAPI") < out.index("Python")


def test_dictionary_word_boundary_excludes_django_for_go() -> None:
    """The "go" alias must NOT match "Django"."""
    out = extract_skills_dictionary("We use Django and Postgres", limit=8)
    assert "Django" in out
    assert "Go" not in out


def test_dictionary_word_boundary_matches_explicit_go() -> None:
    """The "go" alias DOES match an explicit "Go" mention."""
    out = extract_skills_dictionary("We write Go services with Redis", limit=8)
    assert "Go" in out
    assert "Redis" in out


def test_dictionary_dedup_per_skill() -> None:
    """Multiple aliases for one skill yield one entry."""
    out = extract_skills_dictionary("Postgres and postgresql together", limit=8)
    assert out.count("PostgreSQL") == 1


def test_dictionary_respects_limit() -> None:
    """``limit`` caps the result length."""
    text = (
        "Python FastAPI Django PostgreSQL Redis Kafka Docker Kubernetes AWS GCP React Vue Angular"
    )
    out = extract_skills_dictionary(text, limit=3)
    assert len(out) == 3


def test_dictionary_empty_input() -> None:
    """Empty / None text returns an empty list."""
    assert extract_skills_dictionary("", limit=8) == []
    assert extract_skills_dictionary(None, limit=8) == []  # type: ignore[arg-type]


def test_merge_dedup_preserves_primary_order() -> None:
    """Primary list order is preserved; secondary fills the rest."""
    merged = _merge_dedup(
        ["FastAPI", "Python"],
        ["Redis", "Python", "Docker"],
        limit=5,
    )
    assert merged == ["FastAPI", "Python", "Redis", "Docker"]


def test_merge_dedup_case_insensitive() -> None:
    """``Python`` and ``python`` collapse to one entry."""
    merged = _merge_dedup(["Python"], ["python", "Docker"], limit=5)
    assert merged == ["Python", "Docker"]


def test_merge_dedup_respects_limit() -> None:
    merged = _merge_dedup(["A", "B"], ["C", "D", "E"], limit=3)
    assert merged == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_extractor_dictionary_only_when_enough_hits() -> None:
    """If dictionary returns ≥ min_dictionary_hits, no LLM call happens."""
    extractor = SkillExtractor(api_key="", min_dictionary_hits=2)
    # Force any LLM path to throw if it were called.
    extractor._ensure_client = lambda: None  # type: ignore[assignment]

    result = await extractor.extract(
        title="Senior Python Engineer",
        description="Python, FastAPI, PostgreSQL stack.",
    )
    assert isinstance(result, ExtractionResult)
    assert result.source == "dictionary"
    assert "FastAPI" in result.skills


@pytest.mark.asyncio
async def test_extractor_fallback_when_no_api_key_and_low_hits() -> None:
    """No API key + few dictionary hits → ``fallback`` source."""
    extractor = SkillExtractor(api_key="", min_dictionary_hits=5)
    result = await extractor.extract(
        title="Manager",
        description="We need someone responsible and outgoing.",
    )
    assert result.source == "fallback"


@pytest.mark.asyncio
async def test_extractor_llm_merge_with_fake_client() -> None:
    """LLM enrichment merges with dictionary hits and dedupes."""
    extractor = SkillExtractor(api_key="sk-test", model="claude-opus-4-6", min_dictionary_hits=5)

    class _FakeBlock:
        type = "tool_use"
        input = {"skills": ["FastAPI", "Celery", "Redis"]}

    class _FakeResponse:
        content = [_FakeBlock()]

    class _FakeMessages:
        async def create(self, **_: Any) -> _FakeResponse:
            return _FakeResponse()

    class _FakeClient:
        messages = _FakeMessages()

    extractor._client = _FakeClient()  # type: ignore[assignment]
    extractor._ensure_client = lambda: _FakeClient()  # type: ignore[assignment]

    result = await extractor.extract(
        title="Backend developer",
        description="Asyncio service with FastAPI and Postgres.",
    )
    assert result.source == "llm"
    # Dictionary hits come first, LLM appended after dedupe.
    assert "FastAPI" in result.skills
    assert "Celery" in result.skills


@pytest.mark.asyncio
async def test_extractor_llm_failure_degrades_to_fallback() -> None:
    """If the LLM call raises, we degrade to whatever dictionary produced."""
    extractor = SkillExtractor(api_key="sk-test", model="claude-opus-4-6", min_dictionary_hits=5)

    class _ExplodingMessages:
        async def create(self, **_: Any) -> Any:
            raise RuntimeError("upstream 500")

    class _Client:
        messages = _ExplodingMessages()

    extractor._client = _Client()  # type: ignore[assignment]
    extractor._ensure_client = lambda: _Client()  # type: ignore[assignment]

    result = await extractor.extract(
        title="Backend developer",
        description="Asyncio service with FastAPI",
    )
    assert result.source == "fallback"
    assert "FastAPI" in result.skills


def test_extraction_result_comma_joined() -> None:
    """The ``comma_joined`` helper renders the cache payload."""
    er = ExtractionResult(skills=["FastAPI", "PostgreSQL", "Python"], source="dictionary")
    assert er.comma_joined == "FastAPI,PostgreSQL,Python"
