"""Tests for embedding generation on resume upload (Task 2 / match-score wave).

The embedding service in CI uses the rule-based fallback (no VOYAGE_API_KEY)
which always produces a deterministic 1024-d vector, so the happy-path test
reliably gets a non-null embedding without any network calls.
"""

from __future__ import annotations

import io

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from tests.helpers import auth_headers, register_test_user

from app.db import async_session_factory
from app.models import Resume


@pytest.mark.asyncio
async def test_upload_resume_persists_embedding(client: AsyncClient) -> None:
    """Uploaded resume should have a non-null 1024-d embedding stored in DB."""
    _, token, cleanup = await register_test_user(client, role="seeker")
    headers = auth_headers(token)
    try:
        body = b"Python developer, 5 years FastAPI"
        resp = await client.post(
            "/resumes/upload",
            params={"name": "cv"},
            files={"file": ("cv.txt", io.BytesIO(body), "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        resume_id = resp.json()["id"]

        async with async_session_factory() as session:
            row = await session.scalar(select(Resume).where(Resume.id == resume_id))

        assert row is not None
        assert row.embedding is not None
        assert len(row.embedding) == 1024
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_upload_resume_embedding_failure_does_not_block_upload(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the embedding service raises, the upload should still return 201 with embedding=None."""
    _, token, cleanup = await register_test_user(client, role="seeker")
    headers = auth_headers(token)
    try:
        class BrokenService:
            async def embed_texts(self, texts, *, input_type="document"):
                raise RuntimeError("voyage-3 down")

        monkeypatch.setattr(
            "app.routes.resumes.get_embedding_service", lambda: BrokenService()
        )

        body = b"Some resume text"
        resp = await client.post(
            "/resumes/upload",
            params={"name": "cv"},
            files={"file": ("cv.txt", io.BytesIO(body), "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text

        resume_id = resp.json()["id"]

        async with async_session_factory() as session:
            row = await session.scalar(select(Resume).where(Resume.id == resume_id))

        assert row is not None
        assert row.embedding is None
    finally:
        await cleanup()
