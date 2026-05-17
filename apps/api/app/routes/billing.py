"""Billing routes — plans listing, current subscription, checkout, cancel.

The ЮKassa webhook itself is **not** here — it has different auth (IP allow-
list, no bearer token) and lives in ``routes/webhooks.py``. Keeping it separate
means a developer reading ``billing.py`` never has to wonder why one route is
exempt from ``get_current_user``.

Recurring billing is autopayment-based (see ``services/yookassa.py``):
``/checkout`` is only used for the *initial* card-on-file capture; renewals
happen server-side from the Celery beat task.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.auth import get_current_user
from app.deps import DbSession
from app.models import Plan, Subscription, User
from app.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    PlanOut,
    SubscriptionOut,
)
from app.services import yookassa as yk
from app.time_utils import now_utc

router = APIRouter(prefix="/billing", tags=["billing"])

log = logging.getLogger(__name__)


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(db: DbSession) -> list[Plan]:
    """Public catalog — used by the pricing page and Telegram bot."""
    rows = await db.scalars(select(Plan).order_by(Plan.price_rub.asc()))
    return list(rows)


async def _resolve_or_create_free_subscription(
    db: DbSession, user: User
) -> Subscription:
    """Ensure every authenticated user has at least a free-tier row.

    Lazy-creating on first ``/billing/me`` request keeps the registration path
    free of plan-table coupling: a user is created via ``/auth/register`` long
    before they ever see the billing UI.
    """
    sub = await db.scalar(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    if sub is not None:
        return sub

    free_plan = await db.scalar(select(Plan).where(Plan.slug == "free"))
    if free_plan is None:
        # Should never happen after the 0011 migration seeds rows.
        raise HTTPException(
            status_code=500, detail="Бесплатный тариф не настроен"
        )

    now = now_utc()
    sub = Subscription(
        user_id=user.id,
        plan_id=free_plan.id,
        status="active",
        current_period_end=None,
        created_at=now,
        updated_at=now,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


@router.get("/me", response_model=SubscriptionOut)
async def my_subscription(
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> SubscriptionOut:
    sub = await _resolve_or_create_free_subscription(db, current_user)
    plan = await db.get(Plan, sub.plan_id)
    if plan is None:
        raise HTTPException(status_code=500, detail="Тариф подписки не найден")
    return SubscriptionOut(
        plan=PlanOut.model_validate(plan),
        status=sub.status,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.status == "canceled",
    )


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_checkout(
    payload: CheckoutRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> CheckoutResponse:
    plan = await db.scalar(select(Plan).where(Plan.slug == payload.plan_slug))
    if plan is None:
        raise HTTPException(status_code=404, detail="Тариф не найден")
    if plan.slug == "free":
        raise HTTPException(
            status_code=400, detail="Бесплатный тариф не требует оплаты"
        )

    try:
        checkout = yk.create_payment(
            plan_slug=plan.slug,
            price_rub=plan.price_rub,
            user_email=current_user.email,
            description=f"Otklik.ai — тариф {plan.name_ru}",
            save_payment_method=True,
            return_url=payload.return_url,
        )
    except RuntimeError as exc:
        # Missing creds — surface as 503 so the frontend can show a banner
        # instead of a generic 500.
        raise HTTPException(
            status_code=503, detail="Платёжный провайдер недоступен"
        ) from exc
    except Exception as exc:  # pragma: no cover — network errors etc.
        log.exception("billing.checkout.failed")
        raise HTTPException(
            status_code=502, detail="Не удалось создать платёж"
        ) from exc

    # Persist (or update) the subscription row in ``pending`` state. The
    # webhook will flip it to ``active`` once the user finishes the redirect.
    now = now_utc()
    sub = await db.scalar(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    if sub is None:
        sub = Subscription(
            user_id=current_user.id,
            plan_id=plan.id,
            status="pending",
            last_payment_id=checkout.payment_id,
            created_at=now,
            updated_at=now,
        )
        db.add(sub)
    else:
        sub.plan_id = plan.id
        sub.status = "pending"
        sub.last_payment_id = checkout.payment_id
        sub.updated_at = now
    await db.commit()

    return CheckoutResponse(
        confirmation_url=checkout.confirmation_url,
        payment_id=checkout.payment_id,
        status=checkout.status,
    )


@router.post("/cancel", response_model=SubscriptionOut)
async def cancel_subscription(
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> SubscriptionOut:
    sub = await db.scalar(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    if sub is None or sub.status not in {"active", "past_due"}:
        raise HTTPException(status_code=400, detail="Активная подписка не найдена")

    # Clear the saved payment method so the next renewal cycle no-ops.
    # Access stays granted until ``current_period_end``.
    sub.status = "canceled"
    sub.yookassa_payment_method_id = None
    sub.updated_at = now_utc()
    await db.commit()

    plan = await db.get(Plan, sub.plan_id)
    if plan is None:
        raise HTTPException(status_code=500, detail="Тариф подписки не найден")
    return SubscriptionOut(
        plan=PlanOut.model_validate(plan),
        status=sub.status,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=True,
    )
