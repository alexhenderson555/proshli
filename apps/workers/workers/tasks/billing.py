"""Hourly subscription renewal task.

The Celery beat schedule (see ``workers/celery_app.py``) fires this task once
an hour. It scans for subscriptions whose ``current_period_end`` is within the
next hour and ``status == 'active'``, then charges the saved ЮKassa
``payment_method_id`` via ``services.yookassa.charge_recurring``.

Failure handling:

* Successful charge → extend ``current_period_end`` by 30 days; the webhook
  ``payment.succeeded`` event also extends, so this is a belt-and-suspenders
  update — whichever wins, the row converges.
* Failed charge → flip the row to ``past_due`` and, if the user has a linked
  Telegram chat, notify them via the bot-service callback (same pattern as
  Sprint 1's digest dispatcher).

The task is intentionally tolerant of dev environments without credentials:
``charge_recurring`` raises ``RuntimeError`` when credentials are missing, and
we log + skip in that case instead of failing the whole worker.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import structlog
from app.models import Plan, Subscription, User
from app.services import yookassa as yk
from app.time_utils import now_utc
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from workers._async_bridge import run_with_session

log = structlog.get_logger(__name__)

_RENEW_LOOKAHEAD = timedelta(hours=1)
_PERIOD_DAYS = 30


async def _resolve_telegram_chat_id(db: AsyncSession, user_id: int) -> str | None:
    """Return the user's Telegram chat id if linked, else None.

    We deliberately query ``DigestPreference`` rather than ``TelegramAccountLink``
    because the dispatcher already uses that same source-of-truth for delivery
    in Sprint 1. Keeping the lookup uniform avoids two diverging copies of the
    same predicate.
    """
    from app.models import DigestPreference

    pref = await db.scalar(
        select(DigestPreference).where(DigestPreference.user_id == user_id)
    )
    if pref is None or not pref.via_telegram:
        return None
    return pref.telegram_chat_id


async def _notify_past_due(chat_id: str | None, plan_name: str) -> None:
    """Best-effort notification on failed renewal.

    Implemented as a log statement for now — when the Telegram bot service
    exposes a callback endpoint (Wave 5), wire ``httpx.post`` here.
    """
    if not chat_id:
        return
    # The Cyrillic letters trigger RUF001 (ambiguous-unicode) — they are
    # intentional, this string is Russian-language copy for a Telegram chat.
    message_ru = f"Не удалось продлить подписку «{plan_name}». Проверьте карту в личном кабинете."  # noqa: RUF001
    log.info(
        "billing.renew.notify_past_due",
        telegram_chat_id=chat_id,
        plan=plan_name,
        message_ru=message_ru,
    )


async def _renew(db: AsyncSession) -> dict[str, Any]:
    now = now_utc()
    horizon = now + _RENEW_LOOKAHEAD

    candidates = list(
        (
            await db.scalars(
                select(Subscription).where(
                    Subscription.status == "active",
                    Subscription.current_period_end.is_not(None),
                    Subscription.current_period_end <= horizon,
                    Subscription.yookassa_payment_method_id.is_not(None),
                )
            )
        ).all()
    )

    renewed = 0
    failed = 0
    skipped = 0

    for sub in candidates:
        plan = await db.get(Plan, sub.plan_id)
        user = await db.get(User, sub.user_id)
        if plan is None or user is None or sub.yookassa_payment_method_id is None:
            skipped += 1
            continue

        # Idempotency seed = (sub.id, period_end). If beat fires twice in
        # the same hour, or autoretry kicks in mid-charge, the second POST
        # collides with the first on the ЮKassa side and returns the
        # original payment — no double-charge. The period end is enough to
        # rotate the seed once the subscription is extended.
        period_end_iso = (
            sub.current_period_end.isoformat()
            if sub.current_period_end
            else "no-end"
        )
        try:
            result = yk.charge_recurring(
                payment_method_id=sub.yookassa_payment_method_id,
                price_rub=plan.price_rub,
                user_email=user.email,
                description=f"Proshli — продление тарифа {plan.name_ru}",
                idempotency_seed=f"{sub.id}:{period_end_iso}",
            )
        except RuntimeError:
            # Missing credentials in dev — quietly skip without escalation.
            log.warning("billing.renew.credentials_missing")
            skipped += 1
            continue
        except Exception as exc:
            log.warning(
                "billing.renew.charge_failed",
                user_id=user.id,
                plan=plan.slug,
                error=str(exc),
            )
            sub.status = "past_due"
            sub.updated_at = now
            chat_id = await _resolve_telegram_chat_id(db, user.id)
            await _notify_past_due(chat_id, plan.name_ru)
            failed += 1
            continue

        if result.status in {"succeeded", "pending"}:
            base = sub.current_period_end or now
            sub.current_period_end = base + timedelta(days=_PERIOD_DAYS)
            sub.last_payment_id = result.payment_id
            sub.status = "active"
            sub.updated_at = now
            renewed += 1
        else:
            sub.status = "past_due"
            sub.updated_at = now
            chat_id = await _resolve_telegram_chat_id(db, user.id)
            await _notify_past_due(chat_id, plan.name_ru)
            failed += 1

    return {
        "considered": len(candidates),
        "renewed": renewed,
        "failed": failed,
        "skipped": skipped,
    }


@shared_task(
    name="workers.tasks.billing.renew_expiring_subscriptions",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
)
def renew_expiring_subscriptions(self: Any) -> dict[str, Any]:
    """Periodic task — beat fires every hour (see ``celery_app.py``)."""
    log.info("billing.renew.start")
    result = run_with_session(_renew)
    log.info("billing.renew.done", **result)
    return result
