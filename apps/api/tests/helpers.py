"""Test helpers used across integration suites.

The local Postgres is shared across tests so each test cleans up the rows it
creates.  ``register_test_user`` returns the access token plus a callable
that drops the user, their digest pref, and any owned vacancies/action logs.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from app.db import async_session_factory
from app.models import (
    AiUsageEvent,
    DigestPreference,
    EmployerActionLog,
    EmployerProfile,
    EmployerVacancy,
    Resume,
    ResumeVersion,
    SeekerProfile,
    Subscription,
    TelegramAccountLink,
    TelegramLinkCode,
    User,
    Vacancy,
)
from httpx import AsyncClient
from sqlalchemy import delete, select


async def register_test_user(
    client: AsyncClient, *, role: str = "seeker"
) -> tuple[str, str, Callable[[], Awaitable[None]]]:
    """Register a fresh user with a random email; return (email, token, cleanup)."""
    email = f"wave-{uuid.uuid4().hex[:10]}@example.com"
    password = "correct horse battery staple"

    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]

    async def _cleanup() -> None:
        async with async_session_factory() as session:
            user_row = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if user_row is None:
                return
            user_id = user_row.id

            owned_vacancy_ids = list(
                (
                    await session.execute(
                        select(EmployerVacancy.vacancy_id).where(
                            EmployerVacancy.user_id == user_id
                        )
                    )
                ).scalars()
            )
            await session.execute(
                delete(EmployerActionLog).where(EmployerActionLog.user_id == user_id)
            )
            await session.execute(
                delete(EmployerVacancy).where(EmployerVacancy.user_id == user_id)
            )
            if owned_vacancy_ids:
                await session.execute(
                    delete(Vacancy).where(Vacancy.id.in_(owned_vacancy_ids))
                )
            await session.execute(
                delete(DigestPreference).where(DigestPreference.user_id == user_id)
            )
            await session.execute(
                delete(SeekerProfile).where(SeekerProfile.user_id == user_id)
            )
            await session.execute(
                delete(EmployerProfile).where(EmployerProfile.user_id == user_id)
            )
            await session.execute(
                delete(AiUsageEvent).where(AiUsageEvent.user_id == user_id)
            )
            await session.execute(
                delete(Subscription).where(Subscription.user_id == user_id)
            )
            await session.execute(
                delete(Resume).where(Resume.user_id == user_id)
            )
            await session.execute(
                delete(ResumeVersion).where(ResumeVersion.user_id == user_id)
            )
            await session.execute(
                delete(TelegramAccountLink).where(TelegramAccountLink.user_id == user_id)
            )
            await session.execute(
                delete(TelegramLinkCode).where(TelegramLinkCode.user_id == user_id)
            )
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()

    return email, token, _cleanup


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
