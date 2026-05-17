"""End-to-end async integration test for the wave-2 endpoints.

Covers ``/health``, ``/auth/register``, ``/auth/login``, and ``/users/me``
through the actual ASGI app so we exercise the FastAPI dependency graph and
the async SQLAlchemy session machinery together.
"""

from __future__ import annotations

import uuid

import pytest
from app.db import async_session_factory
from app.models import DigestPreference, User
from httpx import AsyncClient
from sqlalchemy import delete


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "otklik-api"


@pytest.mark.asyncio
async def test_register_login_me_roundtrip(client: AsyncClient) -> None:
    email = f"wave2-{uuid.uuid4().hex[:10]}@example.com"
    password = "correct horse battery staple"

    try:
        reg = await client.post(
            "/auth/register",
            json={"email": email, "password": password, "role": "seeker"},
        )
        assert reg.status_code == 201, reg.text
        token = reg.json()["access_token"]
        assert token

        # Duplicate registration is rejected.
        dup = await client.post(
            "/auth/register",
            json={"email": email, "password": password, "role": "seeker"},
        )
        assert dup.status_code == 400

        # Login returns a fresh bearer token.
        log = await client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert log.status_code == 200
        login_token = log.json()["access_token"]
        assert login_token

        # /users/me reflects the registered identity.
        me = await client.get(
            "/users/me", headers={"Authorization": f"Bearer {login_token}"}
        )
        assert me.status_code == 200
        body = me.json()
        assert body["email"] == email
        assert body["role"] == "seeker"

        # Without a token we get 401/403.
        unauth = await client.get("/users/me")
        assert unauth.status_code in (401, 403)
    finally:
        async with async_session_factory() as session:
            user = (
                await session.execute(
                    User.__table__.select().where(User.email == email)
                )
            ).first()
            if user is not None:
                user_id = user.id  # type: ignore[attr-defined]
                await session.execute(
                    delete(DigestPreference).where(DigestPreference.user_id == user_id)
                )
                await session.execute(delete(User).where(User.id == user_id))
                await session.commit()


@pytest.mark.asyncio
async def test_login_with_bad_password(client: AsyncClient) -> None:
    email = f"wave2-bad-{uuid.uuid4().hex[:10]}@example.com"
    password = "correct horse battery staple"

    try:
        reg = await client.post(
            "/auth/register",
            json={"email": email, "password": password, "role": "employer"},
        )
        assert reg.status_code == 201

        bad = await client.post(
            "/auth/login", json={"email": email, "password": "wrong-wrong-wrong"}
        )
        assert bad.status_code == 401
    finally:
        async with async_session_factory() as session:
            user = (
                await session.execute(
                    User.__table__.select().where(User.email == email)
                )
            ).first()
            if user is not None:
                user_id = user.id  # type: ignore[attr-defined]
                await session.execute(
                    delete(DigestPreference).where(DigestPreference.user_id == user_id)
                )
                await session.execute(delete(User).where(User.id == user_id))
                await session.commit()
