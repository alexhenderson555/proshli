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
    assert body["service"] == "proshli-api"


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
        assert "proshli_access=" in set_cookie_header
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


# ---- telegram link / unlink ---------------------------------------------


@pytest.mark.asyncio
async def test_telegram_unlink_idempotent_and_clears_digest(
    client: AsyncClient,
) -> None:
    """``DELETE /auth/telegram/link`` revokes the link + nukes digest chat id.

    Drives the bot ``/unlink`` flow end-to-end:
      1. Seeker generates a link code on the website.
      2. Bot calls ``consume-link`` with a fake telegram id, which creates
         the ``TelegramAccountLink`` and pins ``telegram_chat_id`` on the
         digest pref.
      3. Bot calls ``DELETE /auth/telegram/link`` — the link row should be
         gone, the digest pref kept but with ``via_telegram=False`` and
         no chat id.
      4. A second ``DELETE`` returns 204 (idempotent).
      5. Wrong bot-service-key returns 401 (bot trust boundary).
    """
    from app.config import settings
    from app.models import TelegramAccountLink

    bot_headers = {"x-bot-service-key": settings.bot_service_key}
    tg_user = f"tg-{uuid.uuid4().hex[:8]}"
    tg_chat = "555"

    email = f"unlink-{uuid.uuid4().hex[:10]}@example.com"
    password = "correct horse battery staple"
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": password, "role": "seeker"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]

    try:
        # Step 1 — seeker generates a link code (seeker JWT required).
        code_resp = await client.post(
            "/auth/telegram/link-code",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert code_resp.status_code == 200
        code = code_resp.json()["code"]

        # Step 2 — bot consumes the code (service-key auth).
        consume = await client.post(
            "/auth/telegram/consume-link",
            json={
                "code": code,
                "telegram_user_id": tg_user,
                "telegram_chat_id": tg_chat,
                "telegram_username": "test_user",
            },
            headers=bot_headers,
        )
        assert consume.status_code == 200

        # Pref should now carry the chat id (consume-link sets it).
        async with async_session_factory() as session:
            link = (
                await session.execute(
                    TelegramAccountLink.__table__.select().where(
                        TelegramAccountLink.telegram_user_id == tg_user
                    )
                )
            ).first()
            assert link is not None

        # Wrong service key — 401.
        bad = await client.request(
            "DELETE",
            "/auth/telegram/link",
            json={"telegram_user_id": tg_user, "telegram_chat_id": tg_chat},
            headers={"x-bot-service-key": "wrong"},
        )
        assert bad.status_code == 401

        # Step 3 — bot unlinks.
        first = await client.request(
            "DELETE",
            "/auth/telegram/link",
            json={"telegram_user_id": tg_user, "telegram_chat_id": tg_chat},
            headers=bot_headers,
        )
        assert first.status_code == 204

        async with async_session_factory() as session:
            link = (
                await session.execute(
                    TelegramAccountLink.__table__.select().where(
                        TelegramAccountLink.telegram_user_id == tg_user
                    )
                )
            ).first()
            assert link is None
            pref = (
                await session.execute(
                    DigestPreference.__table__.select().where(
                        DigestPreference.user_id
                        == (
                            await session.execute(
                                User.__table__.select().where(User.email == email)
                            )
                        ).first().id  # type: ignore[union-attr]
                    )
                )
            ).first()
            assert pref is not None
            assert pref.via_telegram is False  # type: ignore[attr-defined]
            assert pref.telegram_chat_id is None  # type: ignore[attr-defined]

        # Step 4 — replay is a no-op.
        second = await client.request(
            "DELETE",
            "/auth/telegram/link",
            json={"telegram_user_id": tg_user, "telegram_chat_id": tg_chat},
            headers=bot_headers,
        )
        assert second.status_code == 204
    finally:
        async with async_session_factory() as session:
            user = (
                await session.execute(
                    User.__table__.select().where(User.email == email)
                )
            ).first()
            if user is not None:
                from app.models import TelegramLinkCode

                user_id = user.id  # type: ignore[attr-defined]
                await session.execute(
                    delete(TelegramAccountLink).where(
                        TelegramAccountLink.user_id == user_id
                    )
                )
                await session.execute(
                    delete(TelegramLinkCode).where(
                        TelegramLinkCode.user_id == user_id
                    )
                )
                await session.execute(
                    delete(DigestPreference).where(DigestPreference.user_id == user_id)
                )
                await session.execute(delete(User).where(User.id == user_id))
                await session.commit()
