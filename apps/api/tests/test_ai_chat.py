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
