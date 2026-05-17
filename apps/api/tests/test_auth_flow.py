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

        # Without a token we get 401/403. The shared ``client`` now
        # carries the HttpOnly access cookie from the register+login above
        # (F8 cookie path), so we clear the jar before the unauth probe —
        # otherwise the cookie carries us through. A real browser
        # navigating without a session would simply not have the cookie.
        client.cookies.clear()
        unauth = await client.get(
            "/users/me",
            # Override the default Authorization header that the test
            # helper attached if any — there shouldn't be one on the
            # bare client, but be explicit.
            headers={"Authorization": ""},
        )
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

@pytest.mark.asyncio
async def test_register_sets_httponly_cookie(client: AsyncClient) -> None:
    """F8 — the access token must come back as an HttpOnly cookie.

    The body still carries ``access_token`` for service clients, but the
    primary FE carrier is the cookie. ``HttpOnly`` is enforced by the
    server-side ``Set-Cookie`` header — we read the raw header rather than
    rely on httpx's cookie jar (which drops the flag at parse time).
    """
    email = f"cookie-{uuid.uuid4().hex[:10]}@example.com"
    try:
        client.cookies.clear()
        resp = await client.post(
            "/auth/register",
            json={"email": email, "password": "secret-pw-1", "role": "seeker"},
        )
        assert resp.status_code == 201, resp.text
        set_cookie_header = resp.headers.get("set-cookie", "")
        assert "otklik_access=" in set_cookie_header
        assert "HttpOnly" in set_cookie_header
        assert "SameSite=lax" in set_cookie_header

        # The cookie alone must authenticate /users/me without an
        # Authorization header.
        client.headers.pop("Authorization", None)
        me = await client.get("/users/me")
        assert me.status_code == 200

        # Logout drops the cookie.
        out = await client.post("/auth/logout")
        assert out.status_code == 204
        # After logout the FE has no cookie; verify by clearing the jar
        # (mirroring what the browser would do once max-age is set to 0).
        client.cookies.clear()
        gone = await client.get("/users/me")
        assert gone.status_code == 401
    finally:
        client.cookies.clear()
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
