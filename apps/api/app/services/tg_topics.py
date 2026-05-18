"""Telegram forum-group topic registry + classifier.

The forum supergroup ``@proshli_jobs`` is segmented into 28 fixed topics
keyed off role/stack — see the design doc
``docs/superpowers/specs/2026-05-18-tg-publication-design.md`` §Topics.

This module owns:

* :data:`TOPICS` — the canonical ordered list. ``TOPICS[i].id`` matches
  ``vacancies.topic_id`` and ``publication_queue.topic_id``.
* :func:`is_valid_topic_id` — guard helper for callers that take a topic
  id from untrusted input (admin UI, API).
* :func:`rule_based_classify` — deterministic keyword-driven fallback. Used
  when no LLM key is configured, and also as the safety net inside the LLM
  classifier when the model returns garbage (out-of-range, non-numeric).
* :class:`TopicClassifier` — the production entry point. Wraps the
  :class:`app.services.llm.LLMService` selector so production gets a real
  classification and CI / offline dev gets the rule-based path. Calling
  ``classify(vacancy)`` is idempotent — it does not write to the DB. The
  caller (prefilter task) is responsible for persisting ``topic_id`` and
  ``classified_at``.

Topic 28 (``Niche``) is the catch-all — if neither the LLM nor the
keyword path can confidently assign a category, we route to Niche rather
than risk landing a Python vacancy in the Frontend topic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, cast

import structlog
from app.config import settings
from app.services.ai_metrics import record_outcome, record_usage

log = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Topic:
    """One forum-group topic.

    ``hints`` is a tuple of substring matchers used by the rule-based
    classifier. Matching is case-insensitive on the joined
    ``title + " " + description`` string. Order in :data:`TOPICS` matches
    the design doc — ``id`` is the 1-based index.
    """

    id: int
    title: str
    hints: tuple[str, ...]


# The hint lists are deliberately tight — false positives are worse than
# false negatives because Niche is a graceful fallback. We err on the side
# of "send to Niche" and let humans reclassify rather than silently route
# a Senior Python role into the QA topic.
TOPICS: tuple[Topic, ...] = (
    Topic(1, "Python Backend", ("python", "django", "fastapi", "flask", "asyncio")),
    Topic(2, "Go Backend", ("golang", " go ", "grpc", "microservice")),
    Topic(3, "Java/Kotlin Backend", ("java", "kotlin", "spring", "jvm")),
    Topic(4, "Node.js Backend", ("node.js", "nodejs", "node ", "nestjs", "express")),
    Topic(5, ".NET Backend", (".net", "c#", "asp.net", "dotnet")),
    Topic(6, "Other Backend", ("php", "ruby", "rust", "elixir", "scala", "laravel")),
    Topic(7, "Frontend", ("react", "vue", "angular", "svelte", "frontend", "next.js")),
    Topic(8, "iOS", ("ios", "swift", "swiftui", "objective-c")),
    Topic(9, "Android", ("android",)),
    Topic(10, "ML/AI/Data Science", ("ml", "machine learning", "llm", "nlp", "pytorch", "tensorflow", "data scientist")),
    Topic(11, "Data Engineering", ("data engineer", "airflow", "spark", "kafka", "dbt")),
    Topic(12, "Аналитика данных", ("аналитик данных", "data analyst", "bi", "tableau", "power bi")),
    Topic(13, "Системный аналитик", ("системный аналитик", "system analyst", "uml")),
    Topic(14, "Бизнес-аналитик", ("бизнес-аналитик", "business analyst", "bpmn")),
    Topic(15, "Маркетинговая/Web-аналитика", ("маркетинг-аналитик", "web analyst", "yandex.metrika", "google analytics", "attribution")),
    Topic(16, "QA / Тестирование", ("qa", "тестировщик", "automation tester", "selenium", "manual testing")),
    Topic(17, "Project Management", ("project manager", "проект-менеджер", "scrum master")),
    Topic(18, "Product Management", ("product manager", "продакт", "product owner")),
    Topic(19, "Служба поддержки", ("служба поддержки", "technical support", "l1", "l2")),
    Topic(20, "Customer Success Manager", ("customer success", "csm", "account retention")),
    Topic(21, "HR / Tech Recruiter", ("recruiter", "рекрутер", "tech recruiter", "sourcer")),
    Topic(22, "Marketing", ("marketing", "маркетолог", "smm", "контент")),
    Topic(23, "Sales / Account Manager", ("sales", "account manager", "продаж", "b2b sales")),
    Topic(24, "DevOps / SRE", ("devops", "sre", "kubernetes", "terraform", "ansible")),
    Topic(25, "UX/UI Design", ("ux", "ui designer", "дизайнер интерфейс", "product designer")),
    Topic(26, "Information Security", ("information security", "appsec", "infosec", "pentest", "soc analyst")),
    Topic(27, "Gamedev", ("gamedev", "unity", "unreal engine", "game developer")),
    Topic(28, "Niche", ()),  # Catch-all; no hints — always last-resort.
)


# Pre-build a {id -> Topic} dict so callers don't pay the linear scan tax.
_TOPICS_BY_ID: dict[int, Topic] = {t.id: t for t in TOPICS}

# The system prompt is module-level so the Anthropic prompt cache keys
# stably across requests — any per-request interpolation would invalidate
# the prefix and cost us the cache discount.
_TOPIC_ENUMERATION = "\n".join(
    f"{t.id}. {t.title}" for t in TOPICS
)
_CLASSIFIER_SYSTEM_PROMPT = (
    "You classify Russian-language IT job vacancies into exactly one of "
    "28 fixed categories. Return ONLY the category id (1-28). If unsure, "
    "if the role is not IT-related, or if it doesn't fit any specific "
    "category, return 28 (Niche).\n\n"
    "Categories:\n" + _TOPIC_ENUMERATION
)


def is_valid_topic_id(value: object) -> bool:
    """Return True if ``value`` is an integer in ``[1, 28]``."""
    return isinstance(value, int) and 1 <= value <= 28


def get_topic(topic_id: int) -> Topic | None:
    """Look up a topic by id; returns ``None`` for out-of-range input."""
    return _TOPICS_BY_ID.get(topic_id)


def _hint_matches(hint: str, haystack: str) -> bool:
    """Return True iff ``hint`` is present in ``haystack`` as a token.

    Short hints (≤3 non-space chars like ``"ml"``, ``"bi"``, ``"go"``,
    ``"qa"``) get a word-boundary check so they don't false-positive on
    substrings — ``"u**ml**"`` mustn't claim Системный аналитик for the
    ML/AI topic, ``"observa**bi**lity"`` mustn't claim Аналитика данных
    for the DevOps topic. Longer hints are substring-matched as before
    because they're specific enough (``"python"``, ``"kubernetes"``,
    ``"data analyst"``).
    """
    stripped = hint.strip()
    if not stripped:
        return False
    if len(stripped) <= 3:
        # ``\b`` honours Russian letters in modern Python regex.
        return re.search(rf"(?<!\w){re.escape(stripped)}(?!\w)", haystack) is not None
    return hint in haystack


def rule_based_classify(*, title: str, description: str) -> int:
    """Deterministic keyword scan returning a topic id (always 1..28).

    Winner-takes-longest across topics: every matching hint records its
    length, and the topic owning the longest match wins. This protects
    against short-token false positives like ``"ml"`` matching
    ``"UML"`` — the more specific ``"системный аналитик"`` would beat
    it. Topic 28 (Niche) is the safety net when nothing matches.

    Behaviour is fully deterministic — same input always yields the
    same id. Ties are broken by lowest topic id (i.e. table order) so
    the result is stable across runs. Tests rely on this.
    """
    haystack = f"{title} {description}".lower()

    best_id = 28
    best_len = 0
    for topic in TOPICS:
        for hint in topic.hints:
            if not _hint_matches(hint, haystack):
                continue
            hint_len = len(hint.strip())
            if hint_len > best_len:
                best_len = hint_len
                best_id = topic.id
    return best_id


# Regex extracts the FIRST integer in the model's reply — robust to
# stray punctuation ("Topic 7", "**3**", "7.\n"). We don't trust a
# string-equal match because models occasionally wrap the answer.
_ID_RE = re.compile(r"\b(\d{1,2})\b")


class TopicClassifier:
    """Production-side classifier wrapping the LLM service.

    Uses the same Anthropic client as :class:`app.services.llm.AnthropicLLMService`
    but with a separate, narrower prompt — no tool use, single-token
    response (the topic id). Falls back to :func:`rule_based_classify` when:

    * no API key is configured (CI / offline dev);
    * the SDK raises (network, rate limit, etc.);
    * the model's reply doesn't contain a 1..28 integer.

    The classifier is stateless — instances are cheap to construct. We
    keep a module-level cached one via :func:`get_topic_classifier`
    mostly to avoid re-loading the lazy ``anthropic`` import per call.
    """

    def __init__(self, *, api_key: str = "", model: str = "", max_tokens: int = 16) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._client: Any | None = None

    def _ensure_client(self) -> Any | None:
        """Lazy-construct the Anthropic client; return None if unavailable."""
        if not self._api_key:
            return None
        if self._client is not None:
            return self._client
        try:
            from anthropic import AsyncAnthropic
        except ImportError:  # pragma: no cover — stripped CI images
            log.warning("tg_topics.anthropic_sdk_missing")
            return None
        self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def classify(self, *, title: str, description: str) -> int:
        """Return a topic id in ``[1, 28]`` for the given vacancy text.

        Never raises — every error path degrades to the rule-based
        classifier. The caller can therefore treat this as a total
        function and skip its own try/except.
        """
        client = self._ensure_client()
        if client is None:
            return rule_based_classify(title=title, description=description)

        user_message = f"Title: {title}\n\nDescription:\n{description[:4000]}"
        try:
            response = await client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=cast(
                    Any,
                    [
                        {
                            "type": "text",
                            "text": _CLASSIFIER_SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                ),
                messages=cast(
                    Any, [{"role": "user", "content": user_message}]
                ),
            )
            record_usage("topic_classify", getattr(response, "usage", None))
        except Exception as exc:  # pragma: no cover — network/quota
            log.warning("tg_topics.llm_failed", error=str(exc))
            record_outcome("topic_classify", "error")
            return rule_based_classify(title=title, description=description)

        # Walk the content blocks for the first piece of text. ``response``
        # follows the same SDK shape as the chat path — ``content`` is a
        # list of typed blocks; we only care about ``text`` blocks here.
        text = ""
        for block in getattr(response, "content", []):
            if getattr(block, "type", "") == "text":
                text = getattr(block, "text", "") or ""
                if text:
                    break

        match = _ID_RE.search(text)
        if match is None:
            log.warning("tg_topics.llm_unparseable", raw=text[:80])
            record_outcome("topic_classify", "error")
            return rule_based_classify(title=title, description=description)

        candidate = int(match.group(1))
        if not is_valid_topic_id(candidate):
            log.warning("tg_topics.llm_out_of_range", value=candidate)
            record_outcome("topic_classify", "error")
            return rule_based_classify(title=title, description=description)
        record_outcome("topic_classify", "success")
        return candidate


_classifier_singleton: TopicClassifier | None = None


def get_topic_classifier() -> TopicClassifier:
    """Return the process-wide classifier instance (lazy)."""
    global _classifier_singleton
    if _classifier_singleton is None:
        _classifier_singleton = TopicClassifier(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=16,
        )
    return _classifier_singleton
