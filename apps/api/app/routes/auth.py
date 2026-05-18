"""Authentication endpoints: email/password + Telegram link flow.

Telegram endpoints accept a service-key header (``X-Bot-Service-Key``) checked
with ``secrets.compare_digest`` so they're safe to expose only to the bot
service; routing them behind the same router keeps OpenAPI coherent.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select

from app.auth import (
    clear_access_cookie,
    create_access_token,
    get_current_user,
    hash_password,
    set_access_cookie,
    verify_password,
)
from app.config import settings
from app.deps import DbSession
from app.middleware.rate_limit import RateLimit
from app.models import (
    DigestPreference,
    TelegramAccountLink,
    TelegramLinkCode,
    User,
)
from app.schemas import (
    LoginRequest,
    RegisterRequest,
    TelegramBotLoginRequest,
    TelegramLinkCodeOut,
    TelegramLinkConsumeRequest,
    TokenResponse,
)
from app.time_utils import now_utc

router = APIRouter(prefix="/auth", tags=["auth"])


async def _require_bot_service_key(
    x_bot_service_key: str | None = Header(default=None),
) -> None:
    if not x_bot_service_key or not secrets.compare_digest(
        x_bot_service_key, settings.bot_service_key
    ):
        raise HTTPException(status_code=401, detail="Invalid bot service key")


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(RateLimit("auth-register", limit=5, window_seconds=60)),
    ],
)
async def register(
    payload: RegisterRequest, response: Response, db: DbSession
) -> TokenResponse:
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        created_at=now_utc(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    db.add(
        DigestPreference(
            user_id=user.id,
            frequency="daily",
            via_telegram=True,
            via_email=False,
        )
    )
    await db.commit()

    token = create_access_token(str(user.id))
    set_access_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[
        Depends(RateLimit("auth-login", limit=10, window_seconds=60)),
    ],
)
async def login(
    payload: LoginRequest, response: Response, db: DbSession
) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user.id))
    set_access_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> Response:
    """Clear the HttpOnly access cookie.

    Stateless logout: the JWT itself can't be revoked server-side without
    introducing a denylist (a Sprint 3 concern). What we *can* do is tell
    the browser to drop the cookie so the next request doesn't carry it.
    Bearer-token clients have no cookie to clear; they just stop sending
    the header.
    """
    clear_access_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/telegram/link-code",
    response_model=TelegramLinkCodeOut,
    dependencies=[
        # User-facing endpoint: tight cap so a stolen JWT can't churn out
        # hundreds of codes (each one invalidates the previous, so abuse
        # would also lock the legit user out of linking).
        Depends(RateLimit("auth-telegram-link-code", limit=5, window_seconds=60)),
    ],
)
async def create_telegram_link_code(
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> TelegramLinkCodeOut:
    if current_user.role != "seeker":
        raise HTTPException(
            status_code=403, detail="Only seekers can create Telegram link code"
        )

    now = now_utc()
    # Invalidate previous unused codes for this user.
    old_codes = (
        await db.scalars(
            select(TelegramLinkCode)
            .where(TelegramLinkCode.user_id == current_user.id)
            .where(TelegramLinkCode.used_at.is_(None))
        )
    ).all()
    for item in old_codes:
        item.used_at = now

    code = "".join(
        secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8)
    )
    expires_at = now + timedelta(minutes=settings.telegram_link_code_ttl_minutes)
    db.add(
        TelegramLinkCode(
            user_id=current_user.id,
            code=code,
            expires_at=expires_at,
            used_at=None,
            created_at=now,
        )
    )
    await db.commit()
    return TelegramLinkCodeOut(code=code, expires_at=expires_at)


@router.post(
    "/telegram/consume-link",
    response_model=TokenResponse,
    dependencies=[
        # Defence-in-depth on top of the bot service key: if the key ever
        # leaks, the 8-char alphanumeric code (~30 bits of entropy) is the
        # only thing standing between an attacker and arbitrary account
        # takeover, so cap brute-force throughput.
        Depends(RateLimit("auth-telegram-consume", limit=30, window_seconds=60)),
    ],
)
async def consume_telegram_link_code(
    payload: TelegramLinkConsumeRequest,
    response: Response,
    db: DbSession,
    _: None = Depends(_require_bot_service_key),
) -> TokenResponse:
    now = now_utc()
    link_code = await db.scalar(
        select(TelegramLinkCode)
        .where(TelegramLinkCode.code == payload.code.strip().upper())
        .where(TelegramLinkCode.used_at.is_(None))
        .where(TelegramLinkCode.expires_at >= now)
    )
    if not link_code:
        raise HTTPException(status_code=404, detail="Link code not found or expired")

    user = await db.get(User, link_code.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="User not found or inactive")

    existing_tg = await db.scalar(
        select(TelegramAccountLink).where(
            TelegramAccountLink.telegram_user_id == payload.telegram_user_id
        )
    )
    if existing_tg and existing_tg.user_id != user.id:
        raise HTTPException(
            status_code=400, detail="Telegram account already linked to another user"
        )

    user_link = await db.scalar(
        select(TelegramAccountLink).where(TelegramAccountLink.user_id == user.id)
    )
    if not user_link:
        user_link = TelegramAccountLink(
            user_id=user.id,
            telegram_user_id=payload.telegram_user_id,
            telegram_chat_id=payload.telegram_chat_id,
            telegram_username=payload.telegram_username,
            created_at=now,
            updated_at=now,
        )
        db.add(user_link)
    else:
        user_link.telegram_user_id = payload.telegram_user_id
        user_link.telegram_chat_id = payload.telegram_chat_id
        user_link.telegram_username = payload.telegram_username
        user_link.updated_at = now

    pref = await db.scalar(
        select(DigestPreference).where(DigestPreference.user_id == user.id)
    )
    if not pref:
        pref = DigestPreference(
            user_id=user.id,
            frequency="daily",
            via_telegram=True,
            via_email=False,
        )
        db.add(pref)
    pref.telegram_chat_id = payload.telegram_chat_id
    pref.updated_at = now

    link_code.used_at = now
    await db.commit()
    token = create_access_token(str(user.id))
    set_access_cookie(response, token)
    return TokenResponse(access_token=token)


@router.delete(
    "/telegram/link",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        # Same rationale as consume-link: bot key is the primary auth but
        # we throttle to limit damage if it leaks.
        Depends(RateLimit("auth-telegram-unlink", limit=30, window_seconds=60)),
    ],
)
async def unlink_telegram(
    payload: TelegramBotLoginRequest,
    db: DbSession,
    _: None = Depends(_require_bot_service_key),
) -> Response:
    """Drop the ``TelegramAccountLink`` for the given Telegram identity.

    Bot calls this from ``/unlink`` so the user can revoke the bot's
    access without going back to the website. We also flip the digest
    transport off so the worker stops sending to a chat that may no
    longer be the user's. The actual ``User`` row is untouched — the
    user keeps their email/password account.
    """
    link = await db.scalar(
        select(TelegramAccountLink).where(
            TelegramAccountLink.telegram_user_id == payload.telegram_user_id
        )
    )
    if link is None:
        # Idempotent: unlinking an already-unlinked identity is a no-op.
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    pref = await db.scalar(
        select(DigestPreference).where(DigestPreference.user_id == link.user_id)
    )
    if pref is not None:
        pref.via_telegram = False
        pref.telegram_chat_id = None
        pref.updated_at = now_utc()

    await db.delete(link)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/telegram/login",
    response_model=TokenResponse,
    dependencies=[
        # Loose cap (the bot calls this frequently during normal use) but
        # still bounded so a leaked bot key can't be used to enumerate
        # every linked telegram_user_id at line rate.
        Depends(RateLimit("auth-telegram-login", limit=100, window_seconds=60)),
    ],
)
async def login_by_telegram(
    payload: TelegramBotLoginRequest,
    response: Response,
    db: DbSession,
    _: None = Depends(_require_bot_service_key),
) -> TokenResponse:
    link = await db.scalar(
        select(TelegramAccountLink).where(
            TelegramAccountLink.telegram_user_id == payload.telegram_user_id
        )
    )
    if not link:
        raise HTTPException(status_code=404, detail="Telegram account not linked")

    user = await db.get(User, link.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    now = now_utc()
    if link.telegram_chat_id != payload.telegram_chat_id:
        link.telegram_chat_id = payload.telegram_chat_id
        link.updated_at = now

    pref = await db.scalar(
        select(DigestPreference).where(DigestPreference.user_id == user.id)
    )
    if pref and pref.telegram_chat_id != payload.telegram_chat_id:
        pref.telegram_chat_id = payload.telegram_chat_id
        pref.updated_at = now

    await db.commit()
    token = create_access_token(str(user.id))
    set_access_cookie(response, token)
    return TokenResponse(access_token=token)
