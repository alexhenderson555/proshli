"""Daily channel-approval task — score top candidates and DM the admin.

Phase 2 of the TG-publication design. Runs once a day at 09:00 MSK
(06:00 UTC, no DST in Russia), kicks off:

1. :func:`app.services.channel_scoring.score_batch` over eligible
   vacancies (active, fresh, not yet decided) using the curated
   prestige index.
2. :func:`app.services.channel_scoring.persist_candidates` inserts a
   ``ChannelCandidate`` row per top-N with ``status='pending'``.
3. Sends a single admin DM with an inline keyboard: one ✅/❌ button
   pair per candidate, ``callback_data`` keyed by the candidate id.

The actual approve/reject HTTP round-trip happens from the tgbot when
the admin clicks — see :mod:`app.routes.channel_approval`.

The task is its own retry mechanism: if today's run fails halfway,
tomorrow's run picks up where it left off (the (vacancy_id,
batch_date) unique constraint means already-inserted candidates are
silently skipped). max_retries=0 keeps Celery's autoretry from
double-DM-ing the admin.
"""

from __future__ import annotations

import html
from typing import Any

import httpx
import structlog
from app.config import settings
from app.services.channel_scoring import (
    persist_candidates,
    score_batch,
)
from app.time_utils import now_utc
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from workers._async_bridge import run_with_session

log = structlog.get_logger(__name__)

_TG_API_BASE = "https://api.telegram.org"
_HTTP_TIMEOUT = 10.0


def _format_admin_message(candidates: list[dict[str, Any]]) -> str:
    """Render the admin DM body in HTML (matches the publisher format).

    Each line: ``N. <b>Title</b> · Company — score 0.78``. Buttons are
    grouped below the text via the inline keyboard, two per row.
    """
    if not candidates:
        return "<b>Channel approval</b>\nNo eligible candidates today."
    lines = [f"<b>Channel approval — {len(candidates)} candidate(s)</b>"]
    for idx, c in enumerate(candidates, start=1):
        title = html.escape(c["title"] or "—")
        company = html.escape(c["company"] or "—")
        score = c["score"]
        lines.append(f"{idx}. <b>{title}</b> · {company} — {score:.2f}")
    return "\n".join(lines)


def _build_inline_keyboard(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a Telegram inline keyboard with ✅/❌ per candidate.

    Returns the raw JSON-shape dict the Bot API expects in
    ``reply_markup``. Two buttons per row keeps the keyboard compact
    even with 8 candidates (16 buttons = 8 rows).
    """
    keyboard: list[list[dict[str, str]]] = []
    for c in candidates:
        cid = c["candidate_id"]
        keyboard.append(
            [
                {"text": f"✅ #{c['idx']}", "callback_data": f"ch_approve_{cid}"},
                {"text": f"❌ #{c['idx']}", "callback_data": f"ch_reject_{cid}"},
            ]
        )
    return {"inline_keyboard": keyboard}


def _send_admin_dm(text: str, reply_markup: dict[str, Any]) -> dict[str, Any]:
    """POST to ``sendMessage`` synchronously. Returns the raw Bot API result.

    We intentionally don't go through aiogram here — the daily task runs
    inside Celery's sync executor and the standalone HTTP shape is one
    line. The token + admin chat id are read from settings.
    """
    token = settings.telegram_bot_token
    chat_id = settings.telegram_admin_chat_id
    if not token or not chat_id:
        return {"sent": False, "reason": "disabled"}
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": reply_markup,
    }
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{_TG_API_BASE}/bot{token}/sendMessage", json=payload
            )
    except httpx.HTTPError as exc:
        log.warning("channel_approval.dm_network_error", error=str(exc))
        return {"sent": False, "reason": "network"}
    if resp.status_code != 200:
        log.warning(
            "channel_approval.dm_failed",
            status=resp.status_code,
            body=resp.text[:300],
        )
        return {"sent": False, "reason": f"status_{resp.status_code}"}
    body = resp.json()
    return {
        "sent": True,
        "message_id": body.get("result", {}).get("message_id"),
    }


async def _run(db: AsyncSession) -> dict[str, Any]:
    """Async entry point — score, persist, return summary for the sync wrapper.

    Sending the DM is deferred to the sync side because httpx + telegram
    is happier on the synchronous client inside Celery's worker pool.
    """
    top_n = settings.channel_approval_top_n
    batch_date = now_utc().date().isoformat()

    scored = await score_batch(db, top_n=top_n)
    if not scored:
        return {"batch_date": batch_date, "scored": 0, "persisted": 0}

    persisted = await persist_candidates(
        db, batch_date=batch_date, scored=scored
    )
    await db.commit()

    # Refresh so we have the ids for the inline keyboard. ``persist_candidates``
    # already flushed; the commit above made them visible.
    candidates_payload: list[dict[str, Any]] = []
    for idx, row in enumerate(persisted, start=1):
        candidate_score = next(
            (s for s in scored if s.vacancy.id == row.vacancy_id), None
        )
        if candidate_score is None:
            continue
        candidates_payload.append(
            {
                "idx": idx,
                "candidate_id": row.id,
                "title": candidate_score.vacancy.title,
                "company": candidate_score.vacancy.company,
                "score": row.score,
            }
        )

    return {
        "batch_date": batch_date,
        "scored": len(scored),
        "persisted": len(persisted),
        "candidates": candidates_payload,
    }


@shared_task(
    name="workers.tasks.channel_approval.score_and_notify_admin",
    bind=True,
    max_retries=0,
)
def score_and_notify_admin(self: Any) -> dict[str, Any]:
    """Beat-driven entry point — score, persist, DM the admin."""
    if not settings.telegram_admin_chat_id:
        log.info("channel_approval.disabled")
        return {
            "scored": 0,
            "persisted": 0,
            "dm_sent": False,
            "disabled": True,
        }

    log.info("channel_approval.start")
    db_result = run_with_session(_run)

    candidates = db_result.pop("candidates", [])
    if not candidates:
        log.info("channel_approval.no_candidates", **db_result)
        return {**db_result, "dm_sent": False}

    text = _format_admin_message(candidates)
    markup = _build_inline_keyboard(candidates)
    dm_result = _send_admin_dm(text, markup)

    log.info("channel_approval.done", **db_result, **dm_result)
    return {**db_result, **dm_result}
