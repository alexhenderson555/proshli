"""External webhook receivers.

These endpoints intentionally bypass the cookie/bearer auth chain because the
callers (payment processors, etc.) cannot present a user token. Each handler
must implement its own trust mechanism.

The ЮKassa receiver uses the official source-IP allowlist (the provider does
not sign payloads, so we treat the network origin as the trust anchor). The
list is encoded in ``services/yookassa.py``.

XFF is only honoured when the *immediate* peer (``request.client.host``) sits
inside ``settings.trusted_proxies``. Otherwise the request reaches us
directly and anybody can spoof their source IP by adding their own
``X-Forwarded-For`` header — which would walk straight past the ЮKassa
IP allow-list. Default config keeps the safe posture (no trusted proxies →
always use ``request.client.host``).

Replay protection lives in ``processed_webhook_events`` (migration 0013): we
INSERT ``(source, event_id)`` *before* dispatching to a handler, and rely on
the unique index to surface duplicates as ``IntegrityError``. On a duplicate
we log + return 200 so ЮKassa stops retrying. Without this guard a single
replayed ``payment.succeeded`` extended the period by another 30 days every
delivery (free month per replay).
"""

from __future__ import annotations

import ipaddress
import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.deps import DbSession
from app.models import Plan, ProcessedWebhookEvent, Subscription, User
from app.services.yookassa import verify_webhook_ip
from app.time_utils import now_utc

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

log = logging.getLogger(__name__)

_PERIOD_DAYS = 30


def _peer_is_trusted_proxy(peer_ip: str) -> bool:
    """Return True iff the immediate peer is in ``settings.trusted_proxies``.

    Accepts bare IPs and CIDR ranges in the setting; anything that fails to
    parse is dropped silently (mis-configuration is logged once at startup
    elsewhere — we don't want a typo here to take the webhook offline).
    """
    if not peer_ip:
        return False
    try:
        peer = ipaddress.ip_address(peer_ip)
    except ValueError:
        return False
    for entry in settings.trusted_proxies_list:
        try:
            net = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            continue
        if peer in net:
            return True
    return False


def _client_ip(request: Request) -> str:
    """Pick the most-trustworthy source IP from the request.

    Only trusts ``X-Forwarded-For`` when the immediate peer is in
    ``settings.trusted_proxies``. Otherwise returns ``request.client.host``
    directly — which is the only IP we can actually verify ourselves.
    """
    peer = request.client.host if request.client else ""
    if _peer_is_trusted_proxy(peer):
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # The left-most non-trusted entry is the client; walk right-to-
            # left across trusted proxies to find it. For a single-hop edge
            # (most setups) the first entry is the client and we stop there.
            hops = [h.strip() for h in xff.split(",") if h.strip()]
            for hop in hops:
                if not _peer_is_trusted_proxy(hop):
                    return hop
            # Entire chain is trusted proxies — fall through to peer.
    return peer


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
    event_id = str(body.get("event_id") or "")
    object_id = str(obj.get("id") or "") or None
    log.info(
        "billing.webhook.received",
        extra={"event": event, "event_id": event_id, "ip": ip},
    )

    # Replay-protection hinge — INSERT before dispatch. The unique index on
    # (source, event_id) makes this atomic: duplicate delivery raises
    # IntegrityError and we short-circuit with 200 so ЮKassa stops retrying.
    # We fall back to "<event>:<object_id>" when the payload has no event_id
    # so older envelopes (or tests) still get guarded; this is what keeps
    # the "free month per replay" bug from biting on legacy webhooks.
    dedupe_key = event_id or (f"{event}:{object_id}" if object_id else "")
    if dedupe_key:
        marker = ProcessedWebhookEvent(
            source="yookassa",
            event_id=dedupe_key,
            event_type=event,
            object_id=object_id,
            processed_at=now_utc(),
        )
        db.add(marker)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            log.info(
                "billing.webhook.replay_ignored",
                extra={"event": event, "event_id": dedupe_key},
            )
            return {"ok": True, "replay": True}

    if event == "payment.succeeded":
        await _handle_payment_succeeded(db, obj)
    elif event == "payment.canceled":
        await _handle_payment_canceled(db, obj)
    elif event == "refund.succeeded":
        await _handle_refund_succeeded(db, obj)
    else:
        # Don't reject — ЮKassa will retry forever otherwise.
        log.info("billing.webhook.ignored_event", extra={"event": event})

    # Commit the marker row + any handler-side mutations in one transaction.
    await db.commit()
    return {"ok": True}


async def _handle_payment_succeeded(db: DbSession, obj: dict[str, Any]) -> None:
    """Mark the subscription active and extend ``current_period_end``.

    *Requires* an existing ``Subscription`` row — we never mint one from the
    webhook payload because the metadata is attacker-supplied (anyone who can
    reach the webhook endpoint with a spoofable IP could otherwise grant
    themselves Pro by inventing a ``user_email``/``plan_slug`` pair). The
    legitimate creation point is the checkout flow in
    ``services/yookassa.py``, which writes the pending row server-side
    before redirecting the user to the payment page.

    Uses ``SELECT … FOR UPDATE`` to serialise concurrent webhook deliveries
    for the same subscription; without it two replays racing past the
    INSERT-side guard could both extend the period.
    """
    metadata = obj.get("metadata") or {}
    plan_slug = str(metadata.get("plan_slug") or "")
    user_email = str(metadata.get("user_email") or "")
    payment_id = str(obj.get("id") or "")
    payment_method = obj.get("payment_method") or {}
    pm_id = str(payment_method.get("id") or "") or None
    recurring = bool(metadata.get("recurring"))

    if not user_email:
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
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .with_for_update()
    )
    if sub is None:
        # The checkout flow is responsible for creating the pending row. If
        # we get here without one the webhook is either replayed from before
        # the row existed (already idempotently handled by the dedupe table)
        # or forged. Either way: refuse to mint a subscription.
        log.warning(
            "billing.webhook.payment_succeeded.no_subscription",
            extra={"email": user_email, "payment_id": payment_id},
        )
        return

    now = now_utc()
    if plan_slug:
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


async def _handle_payment_canceled(db: DbSession, obj: dict[str, Any]) -> None:
    payment_id = str(obj.get("id") or "")
    sub = await db.scalar(
        select(Subscription)
        .where(Subscription.last_payment_id == payment_id)
        .with_for_update()
    )
    if sub is None:
        return
    sub.status = "canceled"
    sub.updated_at = now_utc()


async def _handle_refund_succeeded(db: DbSession, obj: dict[str, Any]) -> None:
    payment_id = str(obj.get("payment_id") or "")
    sub = await db.scalar(
        select(Subscription)
        .where(Subscription.last_payment_id == payment_id)
        .with_for_update()
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
