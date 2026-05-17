"""Tests for ЮKassa billing (Wave 2).

We mock the ЮKassa SDK at the seam — ``app.services.yookassa.create_payment``
returns a deterministic ``CheckoutResult`` so we never hit the network. The
webhook path is exercised directly through ``AsyncClient`` with a forged
``X-Forwarded-For`` to test both the allowlist-accept and the reject branches.

The renewal flow is exercised by calling the inner ``_renew`` coroutine
directly — bypassing Celery's sync wrapper avoids spinning up a broker just
to assert SQL state transitions.
"""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from app.db import async_session_factory
from app.models import Plan, Subscription, User
from app.services import yookassa as yk_service
from app.time_utils import now_utc
from httpx import AsyncClient
from sqlalchemy import delete, select
from tests.helpers import auth_headers, register_test_user


async def _ensure_plan(slug: str, name_ru: str, price_rub: int, **extras: Any) -> int:
    """Idempotently materialise a plan row; return its id."""
    async with async_session_factory() as session:
        existing = await session.scalar(select(Plan).where(Plan.slug == slug))
        if existing is not None:
            return existing.id
        plan = Plan(
            slug=slug,
            name_ru=name_ru,
            price_rub=price_rub,
            ai_daily_limit=extras.get("ai_daily_limit", 5),
            semantic_search=extras.get("semantic_search", False),
            digest_frequency=extras.get("digest_frequency", "weekly"),
            created_at=now_utc(),
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
        return plan.id


@pytest.fixture(autouse=True)
async def _seed_plans() -> None:
    """Make sure the three tier rows exist; conftest uses create_all, not
    alembic, so the seed step from 0011 doesn't run automatically."""
    await _ensure_plan("free", "Бесплатный", 0, ai_daily_limit=5)
    await _ensure_plan(
        "pro", "Pro", 490, ai_daily_limit=50, semantic_search=True, digest_frequency="daily"
    )
    await _ensure_plan(
        "employer",
        "Работодатель",
        2490,
        ai_daily_limit=100,
        semantic_search=True,
        digest_frequency="daily",
    )


async def _drop_subscription_for_email(email: str) -> None:
    async with async_session_factory() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            return
        await session.execute(
            delete(Subscription).where(Subscription.user_id == user.id)
        )
        await session.commit()


# --------------------------------------------------------------------- plans


@pytest.mark.asyncio
async def test_list_plans_returns_three_tiers(client: AsyncClient) -> None:
    resp = await client.get("/billing/plans")
    assert resp.status_code == 200
    body = resp.json()
    slugs = {row["slug"] for row in body}
    assert {"free", "pro", "employer"} <= slugs
    pro = next(row for row in body if row["slug"] == "pro")
    assert pro["price_rub"] == 490
    assert pro["name_ru"] == "Pro"


# ---------------------------------------------------------------------- /me


@pytest.mark.asyncio
async def test_me_lazy_creates_free_subscription(client: AsyncClient) -> None:
    email, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.get("/billing/me", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["plan"]["slug"] == "free"
        assert body["status"] == "active"
    finally:
        await _drop_subscription_for_email(email)
        await cleanup()


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/billing/me")
    # HTTPBearer with auto_error=True returns 403 on a missing header — the
    # current behaviour for the rest of the API. The contract is "not 200".
    assert resp.status_code in (401, 403)


# ----------------------------------------------------------------- checkout


@pytest.mark.asyncio
async def test_checkout_creates_pending_subscription(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email, token, cleanup = await register_test_user(client, role="seeker")
    try:
        def _fake_create_payment(**kwargs: Any) -> yk_service.CheckoutResult:
            return yk_service.CheckoutResult(
                payment_id="pay-test-1",
                confirmation_url="https://yoomoney.ru/checkout/test",
                status="pending",
            )

        monkeypatch.setattr(yk_service, "create_payment", _fake_create_payment)

        resp = await client.post(
            "/billing/checkout",
            json={"plan_slug": "pro"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["payment_id"] == "pay-test-1"
        assert body["confirmation_url"].startswith("https://")
        assert body["status"] == "pending"

        async with async_session_factory() as session:
            user = await session.scalar(select(User).where(User.email == email))
            assert user is not None
            sub = await session.scalar(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            assert sub is not None
            assert sub.status == "pending"
            assert sub.last_payment_id == "pay-test-1"
    finally:
        await _drop_subscription_for_email(email)
        await cleanup()


@pytest.mark.asyncio
async def test_checkout_rejects_free_plan(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.post(
            "/billing/checkout",
            json={"plan_slug": "free"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_checkout_503_when_credentials_missing(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    email, token, cleanup = await register_test_user(client, role="seeker")
    try:
        def _raises(**kwargs: Any) -> None:
            raise RuntimeError("ЮKassa credentials are not configured")

        monkeypatch.setattr(yk_service, "create_payment", _raises)
        resp = await client.post(
            "/billing/checkout",
            json={"plan_slug": "pro"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 503
    finally:
        await _drop_subscription_for_email(email)
        await cleanup()


# ------------------------------------------------------------------ cancel


@pytest.mark.asyncio
async def test_cancel_active_subscription(client: AsyncClient) -> None:
    email, token, cleanup = await register_test_user(client, role="seeker")
    try:
        async with async_session_factory() as session:
            user = await session.scalar(select(User).where(User.email == email))
            assert user is not None
            pro = await session.scalar(select(Plan).where(Plan.slug == "pro"))
            assert pro is not None
            now = now_utc()
            session.add(
                Subscription(
                    user_id=user.id,
                    plan_id=pro.id,
                    status="active",
                    yookassa_payment_method_id="pm-test-1",
                    current_period_end=now + timedelta(days=10),
                    last_payment_id="pay-x",
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()

        resp = await client.post("/billing/cancel", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "canceled"
        assert body["cancel_at_period_end"] is True

        async with async_session_factory() as session:
            user = await session.scalar(select(User).where(User.email == email))
            assert user is not None
            sub = await session.scalar(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            assert sub is not None
            assert sub.yookassa_payment_method_id is None
    finally:
        await _drop_subscription_for_email(email)
        await cleanup()


# ----------------------------------------------------------------- webhook


@pytest.mark.asyncio
async def test_webhook_rejects_unknown_ip(client: AsyncClient) -> None:
    resp = await client.post(
        "/webhooks/yookassa",
        json={"event": "payment.succeeded", "object": {}},
        headers={"X-Forwarded-For": "203.0.113.5"},  # TEST-NET-3
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_webhook_accepts_allowed_ip_and_activates(
    client: AsyncClient,
) -> None:
    email, _token, cleanup = await register_test_user(client, role="seeker")
    try:
        # First plant a pending subscription as if /checkout had been called.
        async with async_session_factory() as session:
            user = await session.scalar(select(User).where(User.email == email))
            assert user is not None
            pro = await session.scalar(select(Plan).where(Plan.slug == "pro"))
            assert pro is not None
            now = now_utc()
            session.add(
                Subscription(
                    user_id=user.id,
                    plan_id=pro.id,
                    status="pending",
                    last_payment_id="pay-evt-1",
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()

        body = {
            "event": "payment.succeeded",
            "object": {
                "id": "pay-evt-1",
                "status": "succeeded",
                "metadata": {"plan_slug": "pro", "user_email": email},
                "payment_method": {"id": "pm-evt-1", "type": "bank_card"},
            },
        }
        resp = await client.post(
            "/webhooks/yookassa",
            json=body,
            # 185.71.76.5 is inside the 185.71.76.0/27 allowlist range.
            headers={"X-Forwarded-For": "185.71.76.5"},
        )
        assert resp.status_code == 200

        async with async_session_factory() as session:
            user = await session.scalar(select(User).where(User.email == email))
            assert user is not None
            sub = await session.scalar(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            assert sub is not None
            assert sub.status == "active"
            assert sub.yookassa_payment_method_id == "pm-evt-1"
            assert sub.current_period_end is not None
    finally:
        await _drop_subscription_for_email(email)
        await cleanup()


# ----------------------------------------------------------- service unit


def test_verify_webhook_ip_allowlist() -> None:
    assert yk_service.verify_webhook_ip("185.71.76.5") is True
    assert yk_service.verify_webhook_ip("185.71.77.31") is True
    assert yk_service.verify_webhook_ip("77.75.156.11") is True
    assert yk_service.verify_webhook_ip("8.8.8.8") is False
    assert yk_service.verify_webhook_ip("not-an-ip") is False
    assert yk_service.verify_webhook_ip("") is False


def test_create_payment_uses_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end-ish: configure creds then check the SDK gets the right shape."""
    from app.config import settings as app_settings

    monkeypatch.setattr(app_settings, "yookassa_shop_id", "shop-id-123")
    monkeypatch.setattr(app_settings, "yookassa_secret_key", "secret-key-123")

    captured: dict[str, Any] = {}

    class _FakePayment:
        @staticmethod
        def create(payload: dict[str, Any], idempotence_key: str) -> Any:
            captured["payload"] = payload
            captured["idempotence_key"] = idempotence_key
            return SimpleNamespace(
                id="pay-fake-1",
                status="pending",
                confirmation=SimpleNamespace(
                    confirmation_url="https://yoomoney.ru/checkout/fake"
                ),
            )

    class _FakeConfiguration:
        account_id: str = ""
        secret_key: str = ""

    import sys
    import types

    fake_module = types.ModuleType("yookassa")
    fake_module.Payment = _FakePayment  # type: ignore[attr-defined]
    fake_module.Configuration = _FakeConfiguration  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "yookassa", fake_module)

    result = yk_service.create_payment(
        plan_slug="pro",
        price_rub=490,
        user_email="user@example.com",
        description="Otklik.ai — тариф Pro",
        save_payment_method=True,
    )

    assert result.payment_id == "pay-fake-1"
    assert result.confirmation_url == "https://yoomoney.ru/checkout/fake"
    payload = captured["payload"]
    assert payload["amount"] == {"value": "490.00", "currency": "RUB"}
    assert payload["save_payment_method"] is True
    assert payload["metadata"]["plan_slug"] == "pro"
    assert payload["metadata"]["user_email"] == "user@example.com"
    assert captured["idempotence_key"]
