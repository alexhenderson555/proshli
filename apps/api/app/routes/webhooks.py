"""External webhook receivers.

These endpoints intentionally bypass the cookie/bearer auth chain because the
callers (payment processors, etc.) cannot present a user token. Each handler
must implement its own trust mechanism.

The ЮKassa receiver uses the official source-IP allowlist (the provider does
not sign payloads, so we treat the network origin as the trust anchor). The
list is encoded in ``services/yookassa.py``.

We honour the standard reverse-proxy convention of trusting the *first* entry
of ``X-Forwarded-For`` when present — Fly.io, Vercel, and nginx all populate
it. Direct connections fall back to ``request.client.host``.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.deps import DbSession
from app.models import Plan, Subscription, User
from app.services.yookassa import verify_webhook_ip
from app.time_utils import now_utc

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

log = logging.getLogger(__name__)

_PERIOD_DAYS = 30


def _client_ip(request: Request) -> str:
    """Pick the most-trustworthy source IP from the request.

    The first XFF hop is the client (subsequent hops are proxies we control);
    falling through to ``request.client.host`` covers the no-proxy dev case.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else ""


@router.post("/yookassa", status_code=status.HTTP_200_OK)
async def yookassa_webhook(request: Request, db: DbSession) -> dict[str, Any]:
    """Process payment notifications from ЮKassa.

    Handled events:

    * ``payment.succeeded``     — flip the subscription to ``active``,
      capture the saved ``payment_method.id`` for recurring renewals.
    * ``payment.canceled``      — flip to ``canceled``; access keeps until
      ``current_period_end`` (set by the previous success, if any).
    * ``refund.succeeded``      — full refund: clear the period end and the
      saved payment method so the user is back to free immediately.

    Unknown event types are ack'd with 200 to stop ЮKassa retrying — the
    provider treats any non-2xx response as a retryable failure, and we'd
    rather log + drop than build up a retry queue we don't read.
    """
    ip = _client_ip(request)
    if not verify_webhook_ip(ip):
        log.warning("billing.webhook.forbidden_ip", extra={"ip": ip})
        raise HTTPException(
            status_code=403, detail="Source IP is not allowed for ЮKassa webhooks"
        )

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    event = str(body.get("event", ""))
    obj = body.get("object") or {}
    log.info("billing.webhook.received", extra={"event": event, "ip": ip})

    if event == "payment.succeeded":
        await _handle_payment_succeeded(db, obj)
    elif event == "payment.canceled":
        await _handle_payment_canceled(db, obj)
    elif event == "refund.succeeded":
        await _handle_refund_succeeded(db, obj)
    else:
        # Don't reject — ЮKassa will retry forever otherwise.
        log.info("billing.webhook.ignored_event", extra={"event": event})

    return {"ok": True}


async def _handle_payment_succeeded(db: DbSession, obj: dict[str, Any]) -> None:
    metadata = obj.get("metadata") or {}
    plan_slug = str(metadata.get("plan_slug") or "")
    user_email = str(metadata.get("user_email") or "")
    payment_id = str(obj.get("id") or "")
    payment_method = obj.get("payment_method") or {}
    pm_id = str(payment_method.get("id") or "") or None
    recurring = bool(metadata.get("recurring"))

    if not user_email or (not plan_slug and not recurring):
        log.warning(
            "billing.webhook.payment_succeeded.missing_metadata",
            extra={"payment_id": payment_id, "metadata": metadata},
        )
        return

    user = await db.scalar(select(User).where(User.email == user_email))
    if user is None:
        log.warning(
            "billing.webhook.payment_succeeded.user_missing",
            extra={"email": user_email, "payment_id": payment_id},
        )
        return

    sub = await db.scalar(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    now = now_utc()

    if sub is None:
        # Pure recurring path can't reach here (subscription must already exist
        # to have a saved payment method), so this is an initial-checkout edge:
        # the user finished payment but the row was never created. Fall back
        # to building it from metadata.
        if not plan_slug:
            return
        plan = await db.scalar(select(Plan).where(Plan.slug == plan_slug))
        if plan is None:
            return
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status="active",
            created_at=now,
            updated_at=now,
        )
        db.add(sub)
    elif plan_slug:
        plan = await db.scalar(select(Plan).where(Plan.slug == plan_slug))
        if plan is not None:
            sub.plan_id = plan.id

    sub.status = "active"
    if pm_id:
        sub.yookassa_payment_method_id = pm_id
    sub.last_payment_id = payment_id
    base = sub.current_period_end if recurring and sub.current_period_end else now
    sub.current_period_end = base + timedelta(days=_PERIOD_DAYS)
    sub.updated_at = now
    await db.commit()


async def _handle_payment_canceled(db: DbSession, obj: dict[str, Any]) -> None:
    payment_id = str(obj.get("id") or "")
    sub = await db.scalar(
        select(Subscription).where(Subscription.last_payment_id == payment_id)
    )
    if sub is None:
        return
    sub.status = "canceled"
    sub.updated_at = now_utc()
    await db.commit()


async def _handle_refund_succeeded(db: DbSession, obj: dict[str, Any]) -> None:
    payment_id = str(obj.get("payment_id") or "")
    sub = await db.scalar(
        select(Subscription).where(Subscription.last_payment_id == payment_id)
    )
    if sub is None:
        return
    free_plan = await db.scalar(select(Plan).where(Plan.slug == "free"))
    if free_plan is not None:
        sub.plan_id = free_plan.id
    sub.status = "canceled"
    sub.current_period_end = None
    sub.yookassa_payment_method_id = None
    sub.updated_at = now_utc()
    await db.commit()
