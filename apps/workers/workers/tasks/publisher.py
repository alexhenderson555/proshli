"""TG-publication batch task — Phase 1 of the publication design.

Drains rows from ``publication_queue`` where ``status='pending'`` and
``scheduled_for <= now``, posts each into the configured forum supergroup
via Telegram's ``sendMessage`` API, and writes back the outcome.

State machine, condensed:

* ``pending`` → ``published`` on a 2xx Bot-API response (we stash the
  remote ``message_id`` for later moderation tooling).
* ``pending`` → ``pending`` with bumped ``scheduled_for`` on a ``429`` /
  ``retry_after`` — the spec says FloodWait reschedules silently.
* ``pending`` → ``pending`` with ``attempts+=1`` and exponential backoff
  on a transient (network, 5xx) error.
* ``pending`` → ``failed`` once ``attempts`` reaches the configured cap,
  or immediately on a permanent client error (``400`` / ``403`` —
  ``MessageEmpty``, ``ChatNotFound``, bot kicked, etc.).

Implementation notes:

* Direct ``httpx`` against ``https://api.telegram.org/bot<token>/...`` —
  same pattern as :mod:`app.services.delivery`. Avoids dragging
  ``aiogram`` into the worker venv just to send one message type.
* Synchronous httpx because the surrounding Celery task is sync. The
  prefilter does the heavy lifting (LLM classify, render) on the async
  side; the publisher's job is pure I/O loop, sync is fine.
* When ``telegram_publication_group_id`` is empty (dev/CI), the task
  logs ``publisher.disabled`` and returns a zeroed summary — beat keeps
  ticking without errors so we don't need a separate "is publication
  configured" guard at the scheduler level.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import httpx
import structlog
from app.config import settings
from app.models import PublicationQueueItem
from app.time_utils import now_utc
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from workers._async_bridge import run_with_session

log = structlog.get_logger(__name__)


# Exponential backoff for transient errors. Matches the spec's
# "60s / 300s / 1800s" cadence — index by attempt count so the first
# failure waits 60 s, the second waits 5 min, the third waits 30 min,
# and anything past that hits the attempts cap and gets marked failed.
_BACKOFF_SECONDS: tuple[int, ...] = (60, 300, 1800)

# Telegram Bot API is forgiving but we still want a tight timeout so a
# single hung request doesn't eat the whole batch's wall budget.
_HTTP_TIMEOUT = 10.0


def _bot_api_url(method: str) -> str:
    """Compose the Bot-API URL for ``method`` (e.g. ``"sendMessage"``)."""
    return f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}"


def _build_payload(item: PublicationQueueItem, chat_id: str) -> dict[str, Any]:
    """Construct the ``sendMessage`` JSON body for one queue row.

    ``message_thread_id`` is only included for forum-group posts where a
    topic id was assigned. Channel posts (Phase 2) leave it out — the
    Bot API rejects ``message_thread_id`` on non-forum chats.
    """
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": item.rendered_text,
        "parse_mode": "HTML",
        # Link previews look noisy on a feed of cards — kill them so the
        # post stays the size we rendered.
        "disable_web_page_preview": True,
    }
    if item.target == "group" and item.topic_id is not None:
        payload["message_thread_id"] = item.topic_id
    return payload


def _classify_error(status: int, body: dict[str, Any]) -> str:
    """Return ``"transient"`` / ``"permanent"`` / ``"rate_limit"``.

    Pulls the verdict out of the Bot-API response so the caller can pick
    the right state transition. ``rate_limit`` is special-cased because
    its retry hint lives inside ``parameters.retry_after``.
    """
    if status == 429:
        return "rate_limit"
    # 4xx other than 429 → permanent. Bot kicked, chat not found,
    # message empty, parse-mode error — none of these get better with a
    # retry, log and move on.
    if 400 <= status < 500:
        return "permanent"
    # 5xx / network → transient. Backoff and retry.
    return "transient"


async def _drain_batch(
    db: AsyncSession,
    *,
    batch_size: int,
    chat_id: str,
    max_attempts: int,
) -> dict[str, Any]:
    """Drain up to ``batch_size`` pending rows; return a counter dict.

    Each row is processed in a try/except so one poison message doesn't
    sink the whole batch. The session is flushed implicitly by the
    surrounding ``run_with_session`` wrapper.
    """
    now = now_utc()

    rows = list(
        (
            await db.scalars(
                select(PublicationQueueItem)
                .where(PublicationQueueItem.status == "pending")
                .where(PublicationQueueItem.scheduled_for <= now)
                .order_by(PublicationQueueItem.scheduled_for.asc())
                .limit(batch_size)
            )
        ).all()
    )

    sent = 0
    rate_limited = 0
    transient = 0
    failed = 0

    if not rows:
        return {
            "considered": 0,
            "sent": 0,
            "rate_limited": 0,
            "transient": 0,
            "failed": 0,
        }

    with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
        for row in rows:
            outcome = _publish_one(
                client,
                row,
                chat_id=chat_id,
                max_attempts=max_attempts,
            )
            if outcome == "sent":
                sent += 1
            elif outcome == "rate_limited":
                rate_limited += 1
            elif outcome == "transient":
                transient += 1
            else:
                failed += 1

    return {
        "considered": len(rows),
        "sent": sent,
        "rate_limited": rate_limited,
        "transient": transient,
        "failed": failed,
    }


def _publish_one(
    client: httpx.Client,
    row: PublicationQueueItem,
    *,
    chat_id: str,
    max_attempts: int,
) -> str:
    """POST one row to ``sendMessage`` and mutate it in place.

    Returns one of ``"sent" | "rate_limited" | "transient" | "failed"`` so
    the batch wrapper can tally. The row mutation is queued in the
    session; the outer ``run_with_session`` decides when to commit.
    """
    payload = _build_payload(row, chat_id)
    try:
        response = client.post(_bot_api_url("sendMessage"), json=payload)
    except Exception as exc:
        # Network-level failure — same treatment as a 5xx.
        return _handle_transient_failure(row, str(exc), max_attempts)

    try:
        body = response.json()
    except ValueError:
        body = {}

    if response.status_code < 400 and body.get("ok"):
        message_id = (body.get("result") or {}).get("message_id")
        row.status = "published"
        row.published_message_id = (
            int(message_id) if isinstance(message_id, int) else None
        )
        row.published_at = now_utc()
        row.failure_reason = None
        log.info(
            "publisher.published",
            queue_id=row.id,
            vacancy_id=row.vacancy_id,
            target=row.target,
            topic_id=row.topic_id,
            message_id=row.published_message_id,
        )
        return "sent"

    verdict = _classify_error(response.status_code, body)
    description = str(body.get("description") or response.text or "")

    if verdict == "rate_limit":
        # Honour Telegram's ``retry_after`` hint exactly. We do NOT bump
        # ``attempts`` here — flood waits aren't the row's fault.
        retry_after = (
            (body.get("parameters") or {}).get("retry_after")
            or response.headers.get("retry-after")
            or 30
        )
        try:
            seconds = int(retry_after)
        except (TypeError, ValueError):
            seconds = 30
        row.scheduled_for = now_utc() + timedelta(seconds=seconds)
        log.info(
            "publisher.flood_wait",
            queue_id=row.id,
            vacancy_id=row.vacancy_id,
            retry_after=seconds,
        )
        return "rate_limited"

    if verdict == "permanent":
        row.status = "failed"
        row.failure_reason = description[:500]
        log.warning(
            "publisher.permanent_failure",
            queue_id=row.id,
            vacancy_id=row.vacancy_id,
            status_code=response.status_code,
            description=description[:200],
        )
        return "failed"

    return _handle_transient_failure(row, description, max_attempts)


def _handle_transient_failure(
    row: PublicationQueueItem,
    reason: str,
    max_attempts: int,
) -> str:
    """Bump ``attempts``, reschedule with backoff, or give up.

    The attempts counter only advances on transient outcomes — rate
    limits (which retry "for free") and permanent errors (which skip
    to ``failed``) bypass this path. Once we exhaust ``max_attempts``,
    the row is marked ``failed`` for human inspection.
    """
    row.attempts = (row.attempts or 0) + 1
    if row.attempts >= max_attempts:
        row.status = "failed"
        row.failure_reason = reason[:500]
        log.warning(
            "publisher.exhausted_attempts",
            queue_id=row.id,
            vacancy_id=row.vacancy_id,
            attempts=row.attempts,
            reason=reason[:200],
        )
        return "failed"

    # 0-indexed lookup with a clamp: attempt #1 waits index 0 = 60 s,
    # attempt #2 waits 300 s, attempt #3 waits 1800 s. Beyond that we'd
    # already be in the ``failed`` branch above.
    delay_index = min(row.attempts - 1, len(_BACKOFF_SECONDS) - 1)
    delay = _BACKOFF_SECONDS[delay_index]
    row.scheduled_for = now_utc() + timedelta(seconds=delay)
    row.failure_reason = reason[:500]
    log.info(
        "publisher.transient_failure",
        queue_id=row.id,
        vacancy_id=row.vacancy_id,
        attempts=row.attempts,
        retry_in_seconds=delay,
        reason=reason[:200],
    )
    return "transient"


async def _publish_pending(db: AsyncSession) -> dict[str, Any]:
    """Async entry point — checked-out by the Celery wrapper below."""
    chat_id = settings.telegram_publication_group_id
    token = settings.telegram_bot_token
    if not chat_id or not token:
        log.info(
            "publisher.disabled",
            has_group=bool(chat_id),
            has_token=bool(token),
        )
        return {
            "considered": 0,
            "sent": 0,
            "rate_limited": 0,
            "transient": 0,
            "failed": 0,
            "disabled": True,
        }

    return await _drain_batch(
        db,
        batch_size=settings.telegram_publication_batch_size,
        chat_id=chat_id,
        max_attempts=settings.telegram_publication_max_attempts,
    )


@shared_task(
    name="workers.tasks.publisher.publish_pending_batch",
    bind=True,
    # The batch is itself the retry mechanism — every 15 min beat tick
    # re-evaluates the queue. We don't want Celery's autoretry stacking
    # on top of our in-row scheduling. A single forceful exception still
    # bubbles up so structlog/sentry sees it.
    max_retries=0,
)
def publish_pending_batch(self: Any) -> dict[str, Any]:
    """Beat-driven entry point — drain pending publications.

    Returns the counter dict produced by :func:`_drain_batch` so the
    Celery result backend has something human-readable to inspect.
    """
    log.info("publisher.start")
    result = run_with_session(_publish_pending)
    log.info("publisher.done", **result)
    return result
