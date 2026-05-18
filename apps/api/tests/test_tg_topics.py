"""Unit tests for the TG forum-topic classifier.

These tests exercise the deterministic rule-based path — production
``classify()`` falls back to it when ``ANTHROPIC_API_KEY`` is empty, so
the same expectations hold in CI. The LLM path is tested separately at
the integration layer (out of scope here).
"""

from __future__ import annotations

import pytest
from app.services.tg_topics import (
    TOPICS,
    Topic,
    get_topic,
    is_valid_topic_id,
    rule_based_classify,
)


def test_topics_are_28_in_order() -> None:
    """Catch accidental list edits — the design spec hard-codes 28 topics.

    ``id`` must equal the 1-based index so callers can store the id and
    look up the topic by ``TOPICS[id - 1]`` without scanning.
    """
    assert len(TOPICS) == 28
    for idx, topic in enumerate(TOPICS, start=1):
        assert topic.id == idx, f"TOPICS[{idx - 1}].id = {topic.id}"
    # Niche is the last + the catch-all (no hints).
    assert TOPICS[-1].id == 28
    assert TOPICS[-1].hints == ()


def test_is_valid_topic_id_bounds() -> None:
    assert is_valid_topic_id(1)
    assert is_valid_topic_id(28)
    assert not is_valid_topic_id(0)
    assert not is_valid_topic_id(29)
    assert not is_valid_topic_id("3")  # type: ignore[arg-type]
    assert not is_valid_topic_id(None)  # type: ignore[arg-type]


def test_get_topic_returns_topic_or_none() -> None:
    assert get_topic(1) == TOPICS[0]
    assert isinstance(get_topic(10), Topic)
    assert get_topic(99) is None


@pytest.mark.parametrize(
    "title,description,expected_id",
    [
        # Tight stack → unambiguous topic.
        ("Senior Python Engineer", "FastAPI, asyncio, postgres", 1),
        ("Frontend React Developer", "react + typescript + nextjs", 7),
        ("DevOps Engineer", "Kubernetes, Terraform, observability", 24),
        ("ML Engineer", "PyTorch, LLM, NLP", 10),
        ("QA Engineer", "Manual + selenium automation", 16),
        # Russian terms must classify too.
        ("Системный аналитик", "Требования, UML", 13),
        ("Бизнес-аналитик", "BPMN, процессы", 14),
        # Off-topic → Niche.
        (
            "Уборщица",
            "Уборка офиса в центре Москвы.",
            28,
        ),
    ],
)
def test_rule_based_classify_known_buckets(
    title: str, description: str, expected_id: int
) -> None:
    """Common shapes get their dedicated topic; outliers land in Niche."""
    assert rule_based_classify(title=title, description=description) == expected_id


def test_rule_based_classify_is_deterministic() -> None:
    """Same input → same output, always. Property tests rely on this."""
    fixture = ("Senior Python", "Django + asyncio backend")
    first = rule_based_classify(title=fixture[0], description=fixture[1])
    for _ in range(5):
        assert (
            rule_based_classify(title=fixture[0], description=fixture[1]) == first
        )


def test_rule_based_classify_falls_back_to_niche_on_empty_input() -> None:
    """Empty strings must still produce a valid id — no exceptions."""
    assert rule_based_classify(title="", description="") == 28
