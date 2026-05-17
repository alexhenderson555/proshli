"""Integration tests for /ai/chat (wave 5; extended for wave 3 LLM wiring).

The endpoint is a gate + LLM proxy. These tests cover:

* off-topic rejection
* successful filter extraction
* per-day budget enforcement (tier-aware as of Wave 3 — limit is read from
  the user's plan, with a fallback to ``settings.ai_daily_request_limit``)
* free / pro tier denial messages include the correct cap
* streaming path emits ``data-content`` for assistant reply tokens and
  ``data-filter`` for tool-use-derived filters (via a fake LLMService)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from app.config import settings
from app.db import async_session_factory
from app.models import AiUsageEvent, Plan, Subscription
from app.routes import ai as ai_route
from app.services import llm as llm_module
from app.time_utils import now_utc
from httpx import AsyncClient
from sqlalchemy import select
from tests.helpers import auth_headers, register_test_user


@pytest.mark.asyncio
async def test_off_topic_message_rejected(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.post(
            "/ai/chat",
            json={"message": "Какая сегодня погода в Москве?"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["accepted"] is False
        assert body["extracted_filters"] is None
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_career_message_extracts_filters(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.post(
            "/ai/chat",
            json={"message": "Ищу удаленную работу senior python"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["accepted"] is True
        assert body["extracted_filters"]["work_mode"] == "remote"
        assert body["extracted_filters"]["level"] == "senior"
        assert body["extracted_filters"]["stack"] == "python"
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_daily_limit_enforced(client: AsyncClient) -> None:
    email, token, cleanup = await register_test_user(client, role="seeker")
    try:
        # Pre-fill the per-day budget directly in the DB.
        async with async_session_factory() as session:
            from app.models import User
            from sqlalchemy import select

            user_id = (
                await session.execute(select(User.id).where(User.email == email))
            ).scalar_one()
            for _ in range(settings.ai_daily_request_limit):
                session.add(
                    AiUsageEvent(
                        user_id=user_id, prompt_chars=10, created_at=now_utc()
                    )
                )
            await session.commit()

        resp = await client.post(
            "/ai/chat",
            json={"message": "вакансия python remote"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["accepted"] is False
        assert "лимит" in body["message"]
    finally:
        await cleanup()


def _parse_sse(body: str) -> list[tuple[str, dict[str, object]]]:
    """Parse an SSE body into a list of ``(event, payload)`` tuples.

    Frames are separated by a blank line; each frame has ``event:`` and
    ``data:`` lines. We tolerate (but don't require) leading whitespace.
    """
    import json

    frames: list[tuple[str, dict[str, object]]] = []
    for raw in body.strip().split("\n\n"):
        event = ""
        data = ""
        for line in raw.splitlines():
            if line.startswith("event:"):
                event = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data = line[len("data:") :].strip()
        if event:
            payload = json.loads(data) if data else {}
            frames.append((event, payload))
    return frames


@pytest.mark.asyncio
async def test_stream_extracts_filters_and_terminates(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.post(
            "/ai/chat/stream",
            json={"message": "Ищу удаленную работу senior python"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        frames = _parse_sse(resp.text)
        events = [e for e, _ in frames]
        assert "data-status" in events
        assert "data-done" in events
        assert events[-1] == "data-done"

        filter_frames = [p for e, p in frames if e == "data-filter"]
        keys = {f["key"] for f in filter_frames}
        assert {"work_mode", "level", "stack"} <= keys

        # Usage frame must report the post-increment count.
        usage_frames = [p for e, p in frames if e == "data-usage"]
        assert usage_frames, "expected a data-usage frame"
        assert int(usage_frames[-1]["used_today"]) >= 1
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_stream_off_topic_emits_error(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.post(
            "/ai/chat/stream",
            json={"message": "Какая сегодня погода в Москве?"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        frames = _parse_sse(resp.text)
        events = [e for e, _ in frames]
        assert "data-error" in events
        error_frame = next(p for e, p in frames if e == "data-error")
        assert error_frame["code"] == "off_topic"
        assert events[-1] == "data-done"
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_oversized_message_rejected(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        too_long = "python " * (settings.ai_max_input_chars // 2)
        resp = await client.post(
            "/ai/chat",
            json={"message": too_long},
            headers=auth_headers(token),
        )
        # Pydantic catches it at validation (422); 400 only if it slips through.
        assert resp.status_code in (400, 422)
    finally:
        await cleanup()


# ----------------------------------------------------------- tier-aware quota


async def _ensure_plan(slug: str, ai_daily_limit: int) -> int:
    """Idempotent helper. The billing tests seed all three plans via their
    autouse fixture, but this suite is independent; we materialise on demand
    so a developer running only ``test_ai_chat.py`` doesn't have to know.
    """
    async with async_session_factory() as session:
        existing = await session.scalar(select(Plan).where(Plan.slug == slug))
        if existing is not None:
            return existing.id
        plan = Plan(
            slug=slug,
            name_ru=slug.title(),
            price_rub=0 if slug == "free" else 490,
            ai_daily_limit=ai_daily_limit,
            semantic_search=False,
            digest_frequency="weekly",
            created_at=now_utc(),
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
        return plan.id


async def _attach_subscription(email: str, plan_slug: str) -> None:
    async with async_session_factory() as session:
        from app.models import User as UserM

        user = await session.scalar(select(UserM).where(UserM.email == email))
        assert user is not None
        plan = await session.scalar(select(Plan).where(Plan.slug == plan_slug))
        assert plan is not None
        now = now_utc()
        session.add(
            Subscription(
                user_id=user.id,
                plan_id=plan.id,
                status="active",
                last_payment_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_free_tier_limit_five(client: AsyncClient) -> None:
    """Free plan has ai_daily_limit=5; six events should trip the gate."""
    await _ensure_plan("free", ai_daily_limit=5)
    email, token, cleanup = await register_test_user(client, role="seeker")
    try:
        await _attach_subscription(email, "free")
        # Fill exactly the free cap.
        async with async_session_factory() as session:
            from app.models import User as UserM

            user_id = (
                await session.execute(select(UserM.id).where(UserM.email == email))
            ).scalar_one()
            for _ in range(5):
                session.add(
                    AiUsageEvent(user_id=user_id, prompt_chars=10, created_at=now_utc())
                )
            await session.commit()

        resp = await client.post(
            "/ai/chat",
            json={"message": "вакансия python remote"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["accepted"] is False
        assert "лимит" in body["message"]
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_pro_tier_allows_more_than_free(client: AsyncClient) -> None:
    """Pro plan has ai_daily_limit=50; six events should still leave headroom."""
    await _ensure_plan("free", ai_daily_limit=5)
    await _ensure_plan("pro", ai_daily_limit=50)
    email, token, cleanup = await register_test_user(client, role="seeker")
    try:
        await _attach_subscription(email, "pro")
        async with async_session_factory() as session:
            from app.models import User as UserM

            user_id = (
                await session.execute(select(UserM.id).where(UserM.email == email))
            ).scalar_one()
            for _ in range(6):
                session.add(
                    AiUsageEvent(user_id=user_id, prompt_chars=10, created_at=now_utc())
                )
            await session.commit()

        resp = await client.post(
            "/ai/chat",
            json={"message": "вакансия python remote"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        # 6 < 50 → still accepted; this is the whole point of the upgrade.
        assert body["accepted"] is True
    finally:
        await cleanup()


# --------------------------------------------------------- streaming + LLM


class _FakeLLM:
    """Test double for :class:`LLMService`. Deterministic, no network."""

    name = "fake"

    def __init__(
        self,
        *,
        filters: dict[str, str] | None = None,
        chunks: list[str] | None = None,
    ) -> None:
        self._filters = filters or {}
        self._chunks = chunks or ["ok"]

    async def stream_chat(self, message: str) -> AsyncIterator[tuple[str, Any]]:
        for k, v in self._filters.items():
            yield "filter", {"key": k, "value": v}
        for chunk in self._chunks:
            yield "content", chunk
        yield "usage", {"input_tokens": 12, "output_tokens": 34}


@pytest.mark.asyncio
async def test_stream_emits_data_content_from_llm(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The streaming endpoint should pipe LLM text chunks through as
    ``data-content`` frames, in order.
    """
    fake = _FakeLLM(
        filters={"stack": "python", "level": "senior"},
        chunks=["Привет! ", "Подобрал ", "вакансии."],
    )
    monkeypatch.setattr(llm_module, "get_llm_service", lambda: fake)
    monkeypatch.setattr(ai_route, "get_llm_service", lambda: fake)

    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.post(
            "/ai/chat/stream",
            json={"message": "Senior python вакансия"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        frames = _parse_sse(resp.text)
        events = [e for e, _ in frames]
        assert "data-content" in events, events
        content_texts = [p["text"] for e, p in frames if e == "data-content"]
        assert content_texts == ["Привет! ", "Подобрал ", "вакансии."]

        filter_keys = {p["key"] for e, p in frames if e == "data-filter"}
        assert {"stack", "level"} <= filter_keys

        assert events[-1] == "data-done"
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_stream_daily_limit_message_uses_plan_cap(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the user hits their plan limit, the error message should mention
    *their* cap (free=5), not the process-wide default."""
    await _ensure_plan("free", ai_daily_limit=5)
    fake = _FakeLLM(filters={"stack": "python"}, chunks=["…"])
    monkeypatch.setattr(llm_module, "get_llm_service", lambda: fake)
    monkeypatch.setattr(ai_route, "get_llm_service", lambda: fake)

    email, token, cleanup = await register_test_user(client, role="seeker")
    try:
        await _attach_subscription(email, "free")
        async with async_session_factory() as session:
            from app.models import User as UserM

            user_id = (
                await session.execute(select(UserM.id).where(UserM.email == email))
            ).scalar_one()
            for _ in range(5):
                session.add(
                    AiUsageEvent(user_id=user_id, prompt_chars=10, created_at=now_utc())
                )
            await session.commit()

        resp = await client.post(
            "/ai/chat/stream",
            json={"message": "вакансия python"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        frames = _parse_sse(resp.text)
        events = [e for e, _ in frames]
        assert "data-error" in events
        error = next(p for e, p in frames if e == "data-error")
        assert error["code"] == "daily_limit_reached"
        # The plan's cap (5) must be present in the error copy — that's the
        # whole point of going tier-aware.
        assert "5" in error["message"]

        usage = next(p for e, p in frames if e == "data-usage")
        assert usage["limit"] == 5
    finally:
        await cleanup()


def test_rule_based_service_extracts_filters_when_no_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sanity check on the fallback: empty API key wires up the rule-based
    extractor, which mirrors filters straight through the keyword path.

    Done as a sync unit-style test — no DB, no HTTP, just service-level
    contract verification. Keeps the suite honest about which path is active
    in CI (where the key is unset).
    """
    import asyncio

    # Clear the lru_cache so the selector re-evaluates with the patched key.
    llm_module.get_llm_service.cache_clear()
    monkeypatch.setattr(llm_module.settings, "anthropic_api_key", "")
    svc = llm_module.get_llm_service()
    assert svc.name == "rule_based"

    async def _collect() -> list[tuple[str, Any]]:
        out: list[tuple[str, Any]] = []
        async for kind, payload in svc.stream_chat("Ищу senior python удаленно"):
            out.append((kind, payload))
        return out

    events = asyncio.run(_collect())
    kinds = [k for k, _ in events]
    assert "filter" in kinds
    assert "content" in kinds
    # Three filters from the rule-based extractor: stack, level, work_mode.
    filter_keys = {p["key"] for k, p in events if k == "filter"}
    assert {"stack", "level", "work_mode"} <= filter_keys

    # Reset for downstream tests.
    llm_module.get_llm_service.cache_clear()
