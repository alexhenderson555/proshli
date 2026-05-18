"""Authentication primitives: password hashing, JWT issuance, and the
``get_current_user`` dependency.

The dependency is async (uses :class:`AsyncSession`) so that it composes with
the rest of the FastAPI app — which is being migrated to fully async I/O in
Sprint 1. Password hashing stays synchronous because passlib's CPU work is
trivial relative to a DB round-trip and not worth threadpool overhead.

Sprint 2 introduces an HTTP-only cookie carrier for the access token (F8).
The bearer-token path stays supported so the Telegram bot and admin
tooling that talk directly to the API don't need to handle cookies. The
priority order is:

1. ``Authorization: Bearer <token>`` — explicit, used by the bot service
   and CLI scripts.
2. ``proshli_access`` cookie — what the Next.js frontend uses. The cookie
   is set ``HttpOnly`` + ``SameSite=Lax`` + ``Secure`` (in non-dev) so a
   browser-side XSS can't read it the way ``localStorage`` would expose
   it.

Both produce a User the rest of the handler can read without caring which
carrier was used.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import Cookie, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.deps import DbSession
from app.models import User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
# ``auto_error=False`` so missing-bearer falls through to the cookie path;
# the dependency raises 401 itself if BOTH carriers are absent.
bearer_scheme = HTTPBearer(auto_error=False)

ACCESS_COOKIE_NAME = "proshli_access"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire = datetime.now(UTC) + expires_delta
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def set_access_cookie(response: Response, token: str) -> None:
    """Attach the access token as an HttpOnly cookie.

    ``Secure`` is on in non-dev environments only — the Next.js dev server
    talks to the API over ``http://localhost``, where ``Secure`` would
    silently drop the cookie. ``SameSite=Lax`` allows top-level
    navigations from the frontend to carry the cookie (the form-submit
    OAuth flow we use for ЮKassa redirect-back), but blocks
    third-party-iframe leaks.
    """
    is_dev = settings.app_env in {"development", "test"}
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=not is_dev,
        samesite="lax",
        path="/",
    )


def clear_access_cookie(response: Response) -> None:
    """Expire the access cookie on logout. Path must match ``set_access_cookie``."""
    response.delete_cookie(key=ACCESS_COOKIE_NAME, path="/")


async def get_current_user(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    proshli_access: str | None = Cookie(default=None),
) -> User:
    # Bearer takes precedence — it's the explicit carrier used by service
    # accounts. The cookie path is the FE's default.
    token: str | None = None
    if credentials is not None and credentials.credentials:
        token = credentials.credentials
    elif proshli_access:
        token = proshli_access

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ValueError("Missing sub")
        user_id = int(user_id_str)
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user
