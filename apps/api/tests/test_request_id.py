"""Tests for the X-Request-ID middleware (wave 7)."""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient

UUID_HEX_RE = re.compile(r"^[0-9a-f]{32}$")


@pytest.mark.asyncio
async def test_request_id_generated_when_absent(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    request_id = resp.headers.get("X-Request-ID")
    assert request_id is not None
    assert UUID_HEX_RE.match(request_id), f"unexpected id format: {request_id!r}"


@pytest.mark.asyncio
async def test_incoming_request_id_propagated(client: AsyncClient) -> None:
    """If the caller supplies an id we keep it (trust but truncate)."""
    given = "trace-abcd-1234"
    resp = await client.get("/health", headers={"X-Request-ID": given})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == given


@pytest.mark.asyncio
async def test_incoming_request_id_truncated(client: AsyncClient) -> None:
    """Long ids are capped so they don't blow up log records."""
    over_limit = "x" * 200
    resp = await client.get("/health", headers={"X-Request-ID": over_limit})
    assert resp.status_code == 200
    echoed = resp.headers.get("X-Request-ID", "")
    assert echoed != over_limit
    assert len(echoed) == 64
