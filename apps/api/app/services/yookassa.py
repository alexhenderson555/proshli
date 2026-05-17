"""ЮKassa SDK wrapper for the billing flow.

The real SDK (`yookassa>=3.5`) is imported lazily inside the helpers so that
local dev environments without credentials still boot — the route handlers
short-circuit to a 503 if ``yookassa_secret_key`` is empty. Tests monkey-patch
``Payment.create`` directly on the SDK module, so no extra abstraction layer is
needed.

Recurring billing is implemented via ЮKassa "save payment method" / autopayments:

* Initial checkout calls ``create_payment(... save_payment_method=True)`` and
  returns a ``confirmation_url`` the frontend redirects the user to.
* After ``payment.succeeded`` lands on the webhook, we read
  ``payment.payment_method.id`` from the payload and store it on the
  ``Subscription`` row.
* The hourly Celery beat task (``charge_recurring``) drives subsequent renewals
  by passing the stored ``payment_method_id`` back to the SDK; no user action
  required.

ЮKassa does not sign webhook payloads — instead the documentation publishes an
official IP allowlist. ``verify_webhook_ip`` enforces it.
"""

from __future__ import annotations

import ipaddress
import logging
import uuid
from dataclasses import dataclass

from app.config import settings

log = logging.getLogger(__name__)

# Official ЮKassa webhook source IPs / ranges.
# Source: https://yookassa.ru/developers/using-api/webhooks#ip
# We keep them in code (vs. a config field) because the list rarely changes
# and an operator-overridable list invites accidental "0.0.0.0/0" disasters.
YOOKASSA_WEBHOOK_IP_RANGES: tuple[str, ...] = (
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11/32",
    "77.75.156.35/32",
    "77.75.154.128/25",
    "2a02:5180::/32",
)


@dataclass(slots=True, frozen=True)
class CheckoutResult:
    """Lightweight value object returned to the route handler.

    Decoupling the route from the raw SDK response keeps the seam between API
    and provider explicit — if we ever swap to a different acquirer, only this
    module changes.
    """

    payment_id: str
    confirmation_url: str
    status: str


def _ensure_configured() -> None:
    """Raise ``RuntimeError`` if billing credentials are missing.

    The route handlers translate this to a 503; the renew Celery task uses the
    same guard to skip itself in dev without spamming Sentry.
    """
    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        raise RuntimeError(
            "ЮKassa credentials are not configured: "
            "set YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY."
        )


def _configure_sdk() -> None:
    """Apply credentials to the SDK module-level singleton.

    The SDK reads ``Configuration.account_id`` / ``Configuration.secret_key``
    at request time, so we reset them on every call rather than once at import:
    cheap, and tolerant of mid-process settings reloads.
    """
    _ensure_configured()
    from yookassa import Configuration

    Configuration.account_id = settings.yookassa_shop_id
    Configuration.secret_key = settings.yookassa_secret_key


def create_payment(
    *,
    plan_slug: str,
    price_rub: int,
    user_email: str,
    description: str,
    save_payment_method: bool = True,
    return_url: str | None = None,
) -> CheckoutResult:
    """Create an initial checkout payment with save-payment-method = True.

    Returns the ``confirmation_url`` the frontend must redirect the user to.
    The webhook handler resolves the user / plan link from ``metadata`` once
    the payment succeeds.
    """
    _configure_sdk()
    from yookassa import Payment

    final_return_url = (
        return_url
        or f"{settings.app_base_url.rstrip('/')}/billing/success"
    )

    payload = {
        "amount": {"value": f"{price_rub:.2f}", "currency": "RUB"},
        "capture": True,
        "save_payment_method": save_payment_method,
        "confirmation": {
            "type": "redirect",
            "return_url": final_return_url,
        },
        "description": description,
        "metadata": {"plan_slug": plan_slug, "user_email": user_email},
        "receipt": {
            "customer": {"email": user_email},
            "items": [
                {
                    "description": description[:128],
                    "quantity": "1.00",
                    "amount": {
                        "value": f"{price_rub:.2f}",
                        "currency": "RUB",
                    },
                    "vat_code": 1,
                }
            ],
        },
    }
    idempotence_key = str(uuid.uuid4())
    payment = Payment.create(payload, idempotence_key)
    return CheckoutResult(
        payment_id=str(payment.id),
        confirmation_url=str(payment.confirmation.confirmation_url),
        status=str(payment.status),
    )


def charge_recurring(
    *,
    payment_method_id: str,
    price_rub: int,
    user_email: str,
    description: str,
) -> CheckoutResult:
    """Charge a saved payment-method handle without user interaction.

    Per ЮKassa autopayments docs, supplying ``payment_method_id`` and omitting
    ``confirmation`` triggers an off-session charge.
    """
    _configure_sdk()
    from yookassa import Payment

    payload = {
        "amount": {"value": f"{price_rub:.2f}", "currency": "RUB"},
        "capture": True,
        "payment_method_id": payment_method_id,
        "description": description,
        "metadata": {"recurring": True, "user_email": user_email},
        "receipt": {
            "customer": {"email": user_email},
            "items": [
                {
                    "description": description[:128],
                    "quantity": "1.00",
                    "amount": {
                        "value": f"{price_rub:.2f}",
                        "currency": "RUB",
                    },
                    "vat_code": 1,
                }
            ],
        },
    }
    idempotence_key = str(uuid.uuid4())
    payment = Payment.create(payload, idempotence_key)
    # Recurring charges don't need a confirmation URL, so we return an empty
    # string rather than tightening the dataclass with Optional everywhere.
    confirmation_url = (
        str(payment.confirmation.confirmation_url)
        if getattr(payment, "confirmation", None)
        and getattr(payment.confirmation, "confirmation_url", None)
        else ""
    )
    return CheckoutResult(
        payment_id=str(payment.id),
        confirmation_url=confirmation_url,
        status=str(payment.status),
    )


def verify_webhook_ip(client_ip: str) -> bool:
    """Return True if ``client_ip`` is in ЮKassa's published source list.

    We parse the address once and let ``ipaddress`` handle IPv6 v. IPv4
    discrimination; an invalid input returns False rather than raising so
    callers can map it to a clean 403.
    """
    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        log.warning("billing.webhook.invalid_ip", extra={"ip": client_ip})
        return False
    for cidr in YOOKASSA_WEBHOOK_IP_RANGES:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            continue
        if addr.version != network.version:
            continue
        if addr in network:
            return True
    return False
