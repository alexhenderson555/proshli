"""Tests for ``app.services.ai_guardrails.is_career_related``.

The keyword gate must pass professional queries in both Russian and English
(including narrow IT-role names like ``system analyst`` or ``devops engineer``)
and still reject obvious off-topic prompts.
"""

from __future__ import annotations

import pytest

from app.services.ai_guardrails import is_career_related


class TestIsCareerRelated:
    """Gate should accept career queries in ru/en and block off-topic ones."""

    @pytest.mark.parametrize(
        "query",
        [
            # --- Russian (regression — must keep passing) ---
            "ищу работу backend",
            "обнови резюме",
            "хочу зарплату 300к",
            "вакансия системного аналитика",
            # --- English IT roles (these were false rejects before the fix) ---
            "system analyst senior",
            "data scientist remote",
            "devops engineer with kubernetes",
            "qa lead manual or automation",
            "ml engineer pytorch",
            "fullstack developer node react",
            "ios mobile developer swift",
            "site reliability engineer",
            "product manager fintech",
            "ux designer figma",
            # --- Mixed ru+en ---
            "ищу senior frontend позицию",
            "data engineer на удалёнке",
        ],
    )
    def test_passes_career_queries(self, query: str) -> None:
        assert is_career_related(query), f"должно быть career-related: {query!r}"

    @pytest.mark.parametrize(
        "query",
        [
            "расскажи анекдот",
            "что такое квантовая запутанность",
            "погода в москве",
            "как готовить борщ",
        ],
    )
    def test_blocks_offtopic(self, query: str) -> None:
        assert not is_career_related(query), f"должно быть отклонено: {query!r}"
