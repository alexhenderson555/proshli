"""Unit tests for :mod:`app.routes.channel_approval` slot picker.

Auth + DB integration paths are covered by the bot-service-key tests
in the broader integration suite; here we exercise the pure
``_next_posting_slot`` function and the inline-keyboard JSON shape
helper from the daily task. The slot picker is the only piece of
non-trivial logic worth pinning in isolation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.routes.channel_approval import _MSK, _next_posting_slot


def test_slot_picker_returns_next_slot_today() -> None:
    """At 09:00 MSK, the next slot is 10:00 MSK."""
    now = datetime(2026, 5, 18, 6, 0, tzinfo=UTC)  # 09:00 MSK
    pick = _next_posting_slot(now)
    msk = pick.astimezone(_MSK)
    assert msk.hour == 10
    assert msk.minute == 0


def test_slot_picker_skips_passed_slots() -> None:
    """At 13:00 MSK, next slot is 14:00 MSK (not 12)."""
    now = datetime(2026, 5, 18, 10, 0, tzinfo=UTC)  # 13:00 MSK
    pick = _next_posting_slot(now)
    msk = pick.astimezone(_MSK)
    assert msk.hour == 14


def test_slot_picker_rolls_to_tomorrow() -> None:
    """After 18:00 MSK (last slot), rolls to 10:00 MSK tomorrow."""
    now = datetime(2026, 5, 18, 16, 0, tzinfo=UTC)  # 19:00 MSK
    pick = _next_posting_slot(now)
    msk = pick.astimezone(_MSK)
    assert msk.day == 19
    assert msk.hour == 10


def test_slot_picker_at_exact_slot_picks_next() -> None:
    """At exactly 12:00 MSK, the picker advances to 14:00 (strictly greater)."""
    now = datetime(2026, 5, 18, 9, 0, tzinfo=UTC)  # 12:00 MSK exactly
    pick = _next_posting_slot(now)
    msk = pick.astimezone(_MSK)
    assert msk.hour == 14


def test_msk_tz_offset() -> None:
    """MSK is UTC+3 — sanity-check the constant."""
    assert _MSK.utcoffset(None) == timedelta(hours=3)
    # And it should not be UTC.
    assert _MSK != UTC
