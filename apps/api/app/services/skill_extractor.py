"""Vacancy skill extractor — pulls top-N technical skills from descriptions.

Two-stage pipeline:

1. :func:`extract_skills_dictionary` — fast curated-dictionary scan.
   ~150 skill tokens (frameworks, languages, tools, ML libraries) with
   word-boundary regex matching to dodge substring false positives
   (the same trick :mod:`app.services.tg_topics` uses — "go" mustn't
   match "Django", "ml" mustn't match "UML"). Tokens are de-duplicated
   while preserving insertion order (which respects priority in
   :data:`SKILL_DICTIONARY` — frameworks before languages before
   generic tools), so the top-3 are the most informative.

2. :class:`SkillExtractor.extract` — production entry point. Calls the
   dictionary path first; if it returns < 2 skills (description didn't
   trigger enough hits to be useful), falls back to a Claude tool-use
   call that returns a JSON array of skills. Caches the result on
   ``vacancy.parsed_skills`` so a re-publish never re-extracts.

The dictionary is intentionally conservative — false negatives (a real
skill we missed) downgrade to the LLM path, which is the slow-but-
accurate fallback. False positives (matching "go" inside "go through")
spam every post with the wrong skill, so we err on the side of
specificity.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, cast

import structlog
from app.config import settings
from app.services.ai_metrics import record_outcome, record_usage

log = structlog.get_logger(__name__)


# Ordered priority list — frameworks first because "FastAPI" is more
# informative than "Python" when both appear, and the renderer slices
# to top-3. Within each tier the order doesn't matter much; we keep
# alphabetical for ease of editing.
#
# Each entry is ``(display_name, *aliases)``. The first item is what
# we show in the post; aliases are case-insensitive substrings used
# for matching. Aliases shorter than 4 chars get word-boundary matching
# (same rule as the topic classifier).
SKILL_DICTIONARY: tuple[tuple[str, ...], ...] = (
    # ---- Backend frameworks (most informative) ----
    ("FastAPI", "fastapi"),
    ("Django", "django"),
    ("Flask", "flask"),
    ("Spring", "spring boot", "spring"),
    ("NestJS", "nestjs", "nest.js"),
    ("Express", "express.js", "expressjs"),
    ("Laravel", "laravel"),
    ("Ruby on Rails", "ruby on rails", "rails"),
    ("ASP.NET", "asp.net", "aspnet"),
    # ---- Frontend frameworks ----
    ("React", "react.js", "reactjs", "react"),
    ("Next.js", "next.js", "nextjs"),
    ("Vue", "vue.js", "vuejs", "vue"),
    ("Angular", "angular"),
    ("Svelte", "svelte"),
    # ---- Mobile ----
    ("SwiftUI", "swiftui"),
    ("Jetpack Compose", "jetpack compose", "compose"),
    ("React Native", "react native"),
    ("Flutter", "flutter"),
    # ---- ML / Data ----
    ("PyTorch", "pytorch"),
    ("TensorFlow", "tensorflow"),
    ("LangChain", "langchain"),
    ("Hugging Face", "huggingface", "hugging face"),
    ("scikit-learn", "scikit-learn", "sklearn"),
    ("pandas", "pandas"),
    ("NumPy", "numpy"),
    ("Airflow", "airflow"),
    ("Spark", "spark"),
    ("Kafka", "kafka"),
    ("dbt", "dbt"),
    ("Databricks", "databricks"),
    # ---- Databases ----
    ("PostgreSQL", "postgresql", "postgres"),
    ("MySQL", "mysql"),
    ("MongoDB", "mongodb"),
    ("Redis", "redis"),
    ("Elasticsearch", "elasticsearch", "elastic"),
    ("ClickHouse", "clickhouse"),
    ("Cassandra", "cassandra"),
    ("DynamoDB", "dynamodb"),
    # ---- Cloud / infra / DevOps ----
    ("Kubernetes", "kubernetes", "k8s"),
    ("Docker", "docker"),
    ("Terraform", "terraform"),
    ("Ansible", "ansible"),
    ("Helm", "helm"),
    ("AWS", "aws"),
    ("GCP", "gcp", "google cloud"),
    ("Azure", "azure"),
    ("Yandex Cloud", "yandex cloud", "yandex.cloud"),
    ("Prometheus", "prometheus"),
    ("Grafana", "grafana"),
    ("Jenkins", "jenkins"),
    ("GitLab CI", "gitlab ci", "gitlab-ci"),
    ("GitHub Actions", "github actions"),
    # ---- Messaging / search ----
    ("RabbitMQ", "rabbitmq"),
    ("Celery", "celery"),
    ("Meilisearch", "meilisearch"),
    ("OpenSearch", "opensearch"),
    # ---- Languages (less informative than frameworks; ordered last) ----
    ("Python", "python"),
    ("TypeScript", "typescript"),
    ("JavaScript", "javascript"),
    ("Go", "golang", " go "),  # " go " word-boundary trick
    ("Rust", "rust"),
    ("Java", "java"),
    ("Kotlin", "kotlin"),
    ("Swift", "swift"),
    ("C#", "c#"),
    ("C++", "c++"),
    ("PHP", "php"),
    ("Ruby", "ruby"),
    ("Scala", "scala"),
    ("Elixir", "elixir"),
    # ---- Testing / QA ----
    ("Selenium", "selenium"),
    ("Cypress", "cypress"),
    ("Playwright", "playwright"),
    ("pytest", "pytest"),
    ("Jest", "jest"),
    # ---- BI / analytics ----
    ("Tableau", "tableau"),
    ("Power BI", "power bi"),
    ("Looker", "looker"),
    ("Metabase", "metabase"),
    # ---- Design ----
    ("Figma", "figma"),
    ("Sketch", "sketch"),
)


def _alias_matches(alias: str, haystack: str) -> bool:
    """Substring or word-boundary match, depending on alias length.

    Aliases shorter than 4 non-space chars get word-boundary regex to
    avoid the "go" in "Django" / "ml" in "UML" trap. The same rule as
    the topic classifier — keep the two paths symmetric so a future
    edit to one prompts an edit to the other.
    """
    stripped = alias.strip()
    if not stripped:
        return False
    if len(stripped) <= 3:
        return re.search(rf"(?<!\w){re.escape(stripped)}(?!\w)", haystack) is not None
    # Aliases with a leading or trailing space are word-boundary
    # tricks (" go " catches "go" but not "going"). Strip + boundary.
    if alias != stripped:
        return re.search(rf"(?<!\w){re.escape(stripped)}(?!\w)", haystack) is not None
    return stripped in haystack


def extract_skills_dictionary(text: str, *, limit: int = 8) -> list[str]:
    """Return up to ``limit`` skills from the curated dictionary.

    Order follows :data:`SKILL_DICTIONARY` priority (frameworks first),
    so callers slicing to ``[:3]`` get the most informative subset.
    Pure function — same input always yields the same output.
    """
    if not text:
        return []
    haystack = text.lower()
    seen: list[str] = []
    for entry in SKILL_DICTIONARY:
        display, *aliases = entry
        for alias in aliases:
            if _alias_matches(alias, haystack):
                if display not in seen:
                    seen.append(display)
                break  # Don't double-add per skill.
        if len(seen) >= limit:
            return seen
    return seen


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """One run's output. Carries provenance for logging/debug."""

    skills: list[str]
    source: str  # "dictionary" | "llm" | "fallback"

    @property
    def comma_joined(self) -> str:
        return ",".join(self.skills)


# Tool schema for the LLM enrichment path. Constrains the model to a
# JSON array of short strings so we don't have to parse free-form
# Russian prose.
_TOOL_SCHEMA: dict[str, Any] = {
    "name": "emit_skills",
    "description": (
        "Extract up to 8 short technical-skill tokens from an IT vacancy "
        "description. Prefer frameworks/languages/tools over generic words. "
        "Each token MUST be a short (≤30 chars) noun phrase suitable for a "
        "Telegram-post chip. Russian or English."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "skills": {
                "type": "array",
                "items": {"type": "string", "maxLength": 30},
                "maxItems": 8,
            }
        },
        "required": ["skills"],
    },
}

_LLM_SYSTEM = (
    "You extract concise technical-skill tokens from Russian-language IT "
    "vacancy descriptions. Use the emit_skills tool. Prefer specific "
    'tokens ("FastAPI", "PyTorch") over generic ones ("Python", '
    '"backend"). Skip soft skills. Return at most 8 items, ordered '
    "by importance."
)


class SkillExtractor:
    """Production entry point — dictionary + optional LLM enrichment.

    Stateless aside from the lazily-built Anthropic client. The same
    ``api_key=""`` short-circuit pattern as :class:`TopicClassifier` —
    no key, no LLM call, just the dictionary path. The dictionary
    output is always returned, even when the LLM ran; the LLM is used
    only to *augment* on low-hit inputs.
    """

    def __init__(
        self,
        *,
        api_key: str = "",
        model: str = "",
        max_tokens: int = 200,
        min_dictionary_hits: int = 2,
        target_count: int = 5,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._min_dictionary_hits = min_dictionary_hits
        self._target_count = target_count
        self._client: Any | None = None

    def _ensure_client(self) -> Any | None:
        if not self._api_key:
            return None
        if self._client is not None:
            return self._client
        try:
            from anthropic import AsyncAnthropic
        except ImportError:  # pragma: no cover
            log.warning("skill_extractor.anthropic_sdk_missing")
            return None
        self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def extract(self, *, title: str, description: str, limit: int = 8) -> ExtractionResult:
        """Extract up to ``limit`` skills; never raises.

        The contract mirrors :meth:`TopicClassifier.classify` — error
        paths degrade to whatever the dictionary produced rather than
        propagating. Callers can treat the return as a total function.
        """
        combined = f"{title}\n{description}"
        dict_skills = extract_skills_dictionary(combined, limit=limit)

        if len(dict_skills) >= self._min_dictionary_hits:
            return ExtractionResult(skills=dict_skills, source="dictionary")

        client = self._ensure_client()
        if client is None:
            return ExtractionResult(skills=dict_skills, source="fallback")

        try:
            llm_skills = await self._llm_extract(client, title, description)
        except Exception as exc:  # noqa: BLE001 - intentional: never raise from extract
            log.warning("skill_extractor.llm_failed", error=str(exc))
            record_outcome("skill_extract", "error")
            return ExtractionResult(skills=dict_skills, source="fallback")

        merged = _merge_dedup(dict_skills, llm_skills, limit=limit)
        record_outcome("skill_extract", "success")
        return ExtractionResult(skills=merged, source="llm")

    async def _llm_extract(self, client: Any, title: str, description: str) -> list[str]:
        """Call Claude with the emit_skills tool; return the array."""
        user_message = f"Title: {title}\n\nDescription:\n{description[:3000]}"
        response = await client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=cast(
                Any,
                [
                    {
                        "type": "text",
                        "text": _LLM_SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            ),
            tools=cast(Any, [_TOOL_SCHEMA]),
            tool_choice=cast(Any, {"type": "tool", "name": "emit_skills"}),
            messages=cast(Any, [{"role": "user", "content": user_message}]),
        )
        record_usage("skill_extract", getattr(response, "usage", None))

        for block in getattr(response, "content", []):
            if getattr(block, "type", "") == "tool_use":
                payload = getattr(block, "input", {}) or {}
                skills_raw = payload.get("skills") or []
                if isinstance(skills_raw, str):
                    # Defensive: model occasionally returns a JSON string
                    # instead of a real array. Decode best-effort.
                    try:
                        skills_raw = json.loads(skills_raw)
                    except json.JSONDecodeError:
                        return []
                return [s.strip() for s in skills_raw if isinstance(s, str) and s.strip()]
        return []


def _merge_dedup(primary: Iterable[str], secondary: Iterable[str], *, limit: int) -> list[str]:
    """Merge two ordered lists, preserve order, dedupe case-insensitively."""
    seen_lower: set[str] = set()
    merged: list[str] = []
    for skill in list(primary) + list(secondary):
        key = skill.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        merged.append(skill)
        if len(merged) >= limit:
            break
    return merged


_extractor_singleton: SkillExtractor | None = None


def get_skill_extractor() -> SkillExtractor:
    """Process-wide cached extractor instance."""
    global _extractor_singleton
    if _extractor_singleton is None:
        _extractor_singleton = SkillExtractor(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=200,
        )
    return _extractor_singleton
