"""Integration tests for /digest/*, /sources, and /ingest/* (wave 5)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from tests.helpers import auth_headers, register_test_user


@pytest.mark.asyncio
async def test_digest_preferences_round_trip(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    headers = auth_headers(token)
    try:
        # First read auto-creates the row (or reuses the default created at register).
        first = await client.get("/digest/preferences", headers=headers)
        assert first.status_code == 200

        upd = await client.put(
            "/digest/preferences",
            json={
                "frequency": "weekly",
                "via_telegram": False,
                "via_email": True,
                "telegram_chat_id": None,
            },
            headers=headers,
        )
        assert upd.status_code == 200
        body = upd.json()
        assert body["frequency"] == "weekly"
        assert body["via_email"] is True
        assert body["via_telegram"] is False

        fetch = await client.get("/digest/preferences", headers=headers)
        assert fetch.json()["frequency"] == "weekly"
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_digest_off_zeros_transports_but_keeps_row(client: AsyncClient) -> None:
    """DELETE /digest/preferences flips both transports off, keeping the row.

    Wave-5 bot ``/digest_off`` calls this so the seeker can opt out without
    losing the saved ``telegram_chat_id`` — re-enabling later via
    ``/digest_daily`` doesn't require typing the chat id again.
    """
    _, token, cleanup = await register_test_user(client, role="seeker")
    headers = auth_headers(token)
    try:
        # Establish a chat id so the test can confirm it's preserved.
        await client.put(
            "/digest/preferences",
            json={
                "frequency": "daily",
                "via_telegram": True,
                "via_email": False,
                "telegram_chat_id": "999",
            },
            headers=headers,
        )

        delete_resp = await client.delete("/digest/preferences", headers=headers)
        assert delete_resp.status_code == 204

        after = await client.get("/digest/preferences", headers=headers)
        body = after.json()
        assert body["via_telegram"] is False
        assert body["via_email"] is False
        # Frequency / chat id preserved so re-enabling is cheap.
        assert body["telegram_chat_id"] == "999"
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_digest_preview_returns_payload(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.get("/digest/preview", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        # No matching vacancies expected in a clean test DB, but the envelope
        # must be present and correctly shaped.
        assert "items" in body
        assert "channels" in body
        assert body["frequency"] in {"daily", "weekly"}
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_sources_list_is_anonymous(client: AsyncClient) -> None:
    resp = await client.get("/sources")
    assert resp.status_code == 200
    names = [item["name"] for item in resp.json()]
    # Registry contains the three demo connectors.
    assert {"hh", "company_sites", "rss"} <= set(names)


@pytest.mark.asyncio
async def test_ingest_requires_employer_role(client: AsyncClient) -> None:
    _, seeker_token, seeker_cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.post(
            "/ingest/company_sites", headers=auth_headers(seeker_token)
        )
        assert resp.status_code == 403
    finally:
        await seeker_cleanup()


@pytest.mark.asyncio
async def test_ingest_unknown_source(client: AsyncClient) -> None:
    _, emp_token, emp_cleanup = await register_test_user(client, role="employer")
    try:
        resp = await client.post(
            "/ingest/no-such-source", headers=auth_headers(emp_token)
        )
        assert resp.status_code == 404
    finally:
        await emp_cleanup()
