"""Integration tests for /ai/chat (wave 5).

The endpoint is a gate, not a model call.  These tests cover:

* off-topic rejection
* successful filter extraction
* per-day budget enforcement (we forcefully insert AiUsageEvent rows for the
  current calendar date up to the configured limit).
"""

from __future__ import annotations

import pytest
from app.config import settings
from app.db import async_session_factory
from app.models import AiUsageEvent
from app.time_utils import now_utc
from httpx import AsyncClient
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
