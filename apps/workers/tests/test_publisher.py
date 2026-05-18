"""Publisher batch task — state-transition tests.

The publisher posts queued rows to Telegram's Bot API. We don't want to
hit the real api.telegram.org in tests, so the whole ``httpx.Client`` is
stubbed via ``monkeypatch``: each test supplies a tiny callable that
returns a canned ``httpx.Response`` and the publisher's state machine is
asserted against the row mutations that follow.

The tests speak directly to ``_drain_batch`` rather than through Celery
— the wrapper is one log + one ``run_with_session`` call, not worth a
broker integration test at this layer.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import pytest
import pytest_asyncio

# Importing workers first extends sys.path with ../api/ so ``app.*`` resolves.
import workers  # noqa: F401
from app.db import Base, async_session_factory, engine
from app.models import PublicationQueueItem, Vacancy
from app.time_utils import now_utc
from sqlalchemy import delete


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _bootstrap_schema() -> AsyncIterator[None]:
    """Create the schema once per session — workers don't ship migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


async def _seed_pending(
    *,
    topic_id: int | None = 1,
    target: str = "group",
    scheduled_offset_seconds: int = -10,
    rendered_text: str = "🟢 <b>Test</b> · Yandex",
) -> tuple[int, int]:
    """Insert a vacancy + pending publication-queue row. Returns (vacancy_id, queue_id)."""
    async with async_session_factory() as session:
        vacancy = Vacancy(
            source="test",
            external_id=f"ext-{uuid.uuid4().hex[:10]}",
            title="Senior Python Engineer",
            company="Yandex",
            location="Москва",
            description="a" * 200,
        )
        session.add(vacancy)
        await session.commit()
        await session.refresh(vacancy)

        item = PublicationQueueItem(
            vacancy_id=vacancy.id,
            target=target,
            topic_id=topic_id,
            rendered_text=rendered_text,
            status="pending",
            scheduled_for=now_utc() + timedelta(seconds=scheduled_offset_seconds),
            attempts=0,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return vacancy.id, item.id


async def _cleanup(vacancy_id: int) -> None:
    async with async_session_factory() as session:
        await session.execute(
            delete(PublicationQueueItem).where(
                PublicationQueueItem.vacancy_id == vacancy_id
            )
        )
        await session.execute(delete(Vacancy).where(Vacancy.id == vacancy_id))
        await session.commit()


class _FakeResponse:
    """Quack-typed ``httpx.Response`` substitute with just the bits we touch.

    The publisher reads ``status_code``, ``.json()``, ``.text`` and
    ``.headers``. Building a real ``httpx.Response`` requires an underlying
    request — easier to fake.
    """

    def __init__(
        self,
        status_code: int,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._body = body
        self.text = text or (str(body) if body is not None else "")
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        if self._body is None:
            raise ValueError("no json body")
        return self._body


class _FakeClient:
    """Stand-in for ``httpx.Client`` used inside ``_drain_batch``."""

    def __init__(self, responder: Any) -> None:
        self._responder = responder
        self.calls: list[dict[str, Any]] = []

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        return None

    def post(self, url: str, json: dict[str, Any]) -> _FakeResponse:
        self.calls.append({"url": url, "json": json})
        return self._responder(url, json)


def _install_fake_client(
    monkeypatch: pytest.MonkeyPatch, responder: Any
) -> _FakeClient:
    """Patch the publisher's ``httpx.Client`` with our fake."""
    from workers.tasks import publisher as pub

    client = _FakeClient(responder)
    monkeypatch.setattr(pub.httpx, "Client", lambda timeout=None: client)
    return client


def _force_publication_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sure the publisher believes it's configured to post."""
    from workers.tasks import publisher as pub

    monkeypatch.setattr(pub.settings, "telegram_bot_token", "TEST-BOT-TOKEN")
    monkeypatch.setattr(
        pub.settings, "telegram_publication_group_id", "-1001234567890"
    )
    monkeypatch.setattr(pub.settings, "telegram_publication_batch_size", 25)
    monkeypatch.setattr(pub.settings, "telegram_publication_max_attempts", 3)


@pytest.mark.asyncio
async def test_publisher_disabled_without_chat_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No configured group → task short-circuits with ``disabled: True``."""
    from workers.tasks import publisher as pub

    monkeypatch.setattr(pub.settings, "telegram_bot_token", "")
    monkeypatch.setattr(pub.settings, "telegram_publication_group_id", "")

    async with async_session_factory() as session:
        result = await pub._publish_pending(session)
    assert result == {
        "considered": 0,
        "sent": 0,
        "rate_limited": 0,
        "transient": 0,
        "failed": 0,
        "disabled": True,
    }


@pytest.mark.asyncio
async def test_publisher_marks_published_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_publication_settings(monkeypatch)
    vacancy_id, queue_id = await _seed_pending()
    try:

        def _ok(url: str, json: dict[str, Any]) -> _FakeResponse:
            return _FakeResponse(
                200, {"ok": True, "result": {"message_id": 4242}}
            )

        client = _install_fake_client(monkeypatch, _ok)

        from workers.tasks import publisher as pub

        async with async_session_factory() as session:
            result = await pub._publish_pending(session)
            await session.commit()

        assert result["sent"] == 1
        assert result["considered"] == 1
        # The Bot-API call included the topic id (forum group post).
        assert client.calls[0]["json"]["message_thread_id"] == 1
        assert client.calls[0]["json"]["parse_mode"] == "HTML"

        async with async_session_factory() as session:
            row = await session.get(PublicationQueueItem, queue_id)
            assert row is not None
            assert row.status == "published"
            assert row.published_message_id == 4242
            assert row.published_at is not None
    finally:
        await _cleanup(vacancy_id)


@pytest.mark.asyncio
async def test_publisher_reschedules_on_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """429 → row stays ``pending`` with ``scheduled_for`` pushed out."""
    _force_publication_settings(monkeypatch)
    vacancy_id, queue_id = await _seed_pending()
    try:

        def _flood(url: str, json: dict[str, Any]) -> _FakeResponse:
            return _FakeResponse(
                429,
                {
                    "ok": False,
                    "error_code": 429,
                    "description": "Too Many Requests: retry after 17",
                    "parameters": {"retry_after": 17},
                },
            )

        _install_fake_client(monkeypatch, _flood)
        from workers.tasks import publisher as pub

        before = now_utc()
        async with async_session_factory() as session:
            result = await pub._publish_pending(session)
            await session.commit()

        assert result["rate_limited"] == 1
        assert result["sent"] == 0

        async with async_session_factory() as session:
            row = await session.get(PublicationQueueItem, queue_id)
            assert row is not None
            assert row.status == "pending"
            assert row.attempts == 0  # no attempt bump on rate limit
            assert row.scheduled_for >= before + timedelta(seconds=15)
    finally:
        await _cleanup(vacancy_id)


@pytest.mark.asyncio
async def test_publisher_fails_on_permanent_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """400/403 → row jumps straight to ``failed`` with a reason."""
    _force_publication_settings(monkeypatch)
    vacancy_id, queue_id = await _seed_pending()
    try:

        def _bad(url: str, json: dict[str, Any]) -> _FakeResponse:
            return _FakeResponse(
                400,
                {
                    "ok": False,
                    "error_code": 400,
                    "description": "Bad Request: chat not found",
                },
            )

        _install_fake_client(monkeypatch, _bad)
        from workers.tasks import publisher as pub

        async with async_session_factory() as session:
            result = await pub._publish_pending(session)
            await session.commit()

        assert result["failed"] == 1

        async with async_session_factory() as session:
            row = await session.get(PublicationQueueItem, queue_id)
            assert row is not None
            assert row.status == "failed"
            assert row.failure_reason is not None
            assert "chat not found" in row.failure_reason
    finally:
        await _cleanup(vacancy_id)


@pytest.mark.asyncio
async def test_publisher_transient_failure_backs_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5xx → ``attempts`` bumps and ``scheduled_for`` slides forward."""
    _force_publication_settings(monkeypatch)
    vacancy_id, queue_id = await _seed_pending()
    try:

        def _flap(url: str, json: dict[str, Any]) -> _FakeResponse:
            return _FakeResponse(
                502,
                {"ok": False, "description": "Bad gateway"},
            )

        _install_fake_client(monkeypatch, _flap)
        from workers.tasks import publisher as pub

        before = now_utc()
        async with async_session_factory() as session:
            result = await pub._publish_pending(session)
            await session.commit()

        assert result["transient"] == 1

        async with async_session_factory() as session:
            row = await session.get(PublicationQueueItem, queue_id)
            assert row is not None
            assert row.status == "pending"
            assert row.attempts == 1
            # First-attempt backoff is 60 s; allow a small wall clock budget.
            assert row.scheduled_for >= before + timedelta(seconds=55)
    finally:
        await _cleanup(vacancy_id)


@pytest.mark.asyncio
async def test_publisher_marks_failed_after_max_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A row already at ``attempts == max-1`` flips to ``failed`` on next miss."""
    _force_publication_settings(monkeypatch)
    vacancy_id, queue_id = await _seed_pending()
    try:
        # Prime the row to "last chance" state.
        async with async_session_factory() as session:
            row = await session.get(PublicationQueueItem, queue_id)
            assert row is not None
            row.attempts = 2  # max_attempts is 3 → next miss must give up
            await session.commit()

        def _flap(url: str, json: dict[str, Any]) -> _FakeResponse:
            return _FakeResponse(503, {"ok": False, "description": "down"})

        _install_fake_client(monkeypatch, _flap)
        from workers.tasks import publisher as pub

        async with async_session_factory() as session:
            result = await pub._publish_pending(session)
            await session.commit()

        assert result["failed"] == 1

        async with async_session_factory() as session:
            row = await session.get(PublicationQueueItem, queue_id)
            assert row is not None
            assert row.status == "failed"
            assert row.attempts == 3
    finally:
        await _cleanup(vacancy_id)


@pytest.mark.asyncio
async def test_publisher_skips_future_scheduled_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A row scheduled an hour from now must not be touched by this batch."""
    _force_publication_settings(monkeypatch)
    vacancy_id, queue_id = await _seed_pending(scheduled_offset_seconds=3600)
    try:

        def _never_called(url: str, json: dict[str, Any]) -> _FakeResponse:
            raise AssertionError("future-scheduled row must not be POSTed")

        _install_fake_client(monkeypatch, _never_called)
        from workers.tasks import publisher as pub

        async with async_session_factory() as session:
            result = await pub._publish_pending(session)
            await session.commit()

        assert result["considered"] == 0
        assert result["sent"] == 0

        async with async_session_factory() as session:
            row = await session.get(PublicationQueueItem, queue_id)
            assert row is not None
            assert row.status == "pending"
            assert row.attempts == 0
    finally:
        await _cleanup(vacancy_id)


@pytest.mark.asyncio
async def test_publisher_does_not_send_topic_id_for_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Channel posts (Phase 2 plumbing) must NOT include ``message_thread_id``."""
    _force_publication_settings(monkeypatch)
    vacancy_id, _queue_id = await _seed_pending(target="channel", topic_id=None)
    try:

        def _ok(url: str, json: dict[str, Any]) -> _FakeResponse:
            return _FakeResponse(
                200, {"ok": True, "result": {"message_id": 7777}}
            )

        client = _install_fake_client(monkeypatch, _ok)
        from workers.tasks import publisher as pub

        async with async_session_factory() as session:
            await pub._publish_pending(session)
            await session.commit()

        assert client.calls
        assert "message_thread_id" not in client.calls[0]["json"]
    finally:
        await _cleanup(vacancy_id)
