"""Renewal task tests — call ``_renew`` directly to avoid the Celery layer.

The shared API DB is the same one the api suite uses (single Postgres in
docker-compose for local dev / CI). We seed the three plan rows + a single
subscription row, monkey-patch ``services.yookassa.charge_recurring`` on the
task module's import, and assert state transitions.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import pytest
import pytest_asyncio

# Import the workers package first so it extends ``sys.path`` with ../api/.
# Without this side-effect the ``from app.*`` imports below cannot resolve when
# pytest collects this module from the workers directory.
import workers  # noqa: F401
from app.db import Base, async_session_factory, engine
from app.models import DigestPreference, Plan, Subscription, User
from app.services import yookassa as yk_service
from app.time_utils import now_utc
from sqlalchemy import delete, select


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _bootstrap_schema() -> AsyncIterator[None]:
    """Create-all once per session — workers don't ship alembic of their own.

    Session scope keeps a single event loop alive across all tests in this
    module so asyncpg's connection pool remains bound to a live loop.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


async def _seed_plan(slug: str, name_ru: str, price_rub: int) -> int:
    async with async_session_factory() as session:
        existing = await session.scalar(select(Plan).where(Plan.slug == slug))
        if existing is not None:
            return existing.id
        plan = Plan(
            slug=slug,
            name_ru=name_ru,
            price_rub=price_rub,
            ai_daily_limit=50,
            semantic_search=True,
            digest_frequency="daily",
            created_at=now_utc(),
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
        return plan.id


async def _make_user_and_sub(
    *,
    plan_slug: str,
    pm_id: str,
    period_minutes: int = 10,
) -> tuple[int, int]:
    """Create a fresh user + ``active`` subscription expiring within the
    lookahead horizon. Returns (user_id, sub_id) for later cleanup."""
    await _seed_plan("free", "Бесплатный", 0)
    if plan_slug == "pro":
        await _seed_plan("pro", "Pro", 490)
    else:
        await _seed_plan(plan_slug, plan_slug.title(), 490)

    async with async_session_factory() as session:
        email = f"renew-{uuid.uuid4().hex[:10]}@example.com"
        user = User(
            email=email,
            password_hash="x",
            role="seeker",
            is_active=True,
            created_at=now_utc(),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        plan = await session.scalar(select(Plan).where(Plan.slug == plan_slug))
        assert plan is not None
        now = now_utc()
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status="active",
            yookassa_payment_method_id=pm_id,
            current_period_end=now + timedelta(minutes=period_minutes),
            last_payment_id="pay-prev",
            created_at=now,
            updated_at=now,
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return user.id, sub.id


async def _cleanup_user(user_id: int) -> None:
    async with async_session_factory() as session:
        await session.execute(
            delete(Subscription).where(Subscription.user_id == user_id)
        )
        await session.execute(
            delete(DigestPreference).where(DigestPreference.user_id == user_id)
        )
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


@pytest.fixture(autouse=True)
async def _seed_pro_plan() -> None:
    # The api suite seeds pro/employer too, but we run independently here.
    await _seed_plan("pro", "Pro", 490)


@pytest.mark.asyncio
async def test_renew_extends_period_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, _sub_id = await _make_user_and_sub(plan_slug="pro", pm_id="pm-ok-1")
    try:
        from workers.tasks import billing as billing_task

        def _ok(**kwargs: Any) -> yk_service.CheckoutResult:
            return yk_service.CheckoutResult(
                payment_id="pay-ok-1", confirmation_url="", status="succeeded"
            )

        monkeypatch.setattr(billing_task.yk, "charge_recurring", _ok)

        async with async_session_factory() as session:
            result = await billing_task._renew(session)
            await session.commit()
        assert result["renewed"] == 1
        assert result["failed"] == 0

        async with async_session_factory() as session:
            sub = await session.scalar(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            assert sub is not None
            assert sub.last_payment_id == "pay-ok-1"
            assert sub.status == "active"
            assert sub.current_period_end is not None
            assert sub.current_period_end > now_utc() + timedelta(days=25)
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_renew_flips_past_due_on_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, _sub_id = await _make_user_and_sub(plan_slug="pro", pm_id="pm-fail-1")
    try:
        from workers.tasks import billing as billing_task

        def _fail(**kwargs: Any) -> None:
            raise ValueError("simulated provider error")

        monkeypatch.setattr(billing_task.yk, "charge_recurring", _fail)

        async with async_session_factory() as session:
            result = await billing_task._renew(session)
            await session.commit()
        assert result["failed"] >= 1

        async with async_session_factory() as session:
            sub = await session.scalar(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            assert sub is not None
            assert sub.status == "past_due"
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_renew_skips_when_credentials_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, _sub_id = await _make_user_and_sub(plan_slug="pro", pm_id="pm-skip-1")
    try:
        from workers.tasks import billing as billing_task

        def _missing(**kwargs: Any) -> None:
            raise RuntimeError("ЮKassa credentials are not configured")

        monkeypatch.setattr(billing_task.yk, "charge_recurring", _missing)

        async with async_session_factory() as session:
            result = await billing_task._renew(session)
            await session.commit()
        assert result["skipped"] >= 1
        assert result["renewed"] == 0
        assert result["failed"] == 0

        async with async_session_factory() as session:
            sub = await session.scalar(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            assert sub is not None
            assert sub.status == "active"
    finally:
        await _cleanup_user(user_id)
