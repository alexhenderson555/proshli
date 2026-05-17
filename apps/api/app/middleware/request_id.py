"""Request-ID middleware.

Generates a UUID4 for every incoming request and:

* stores it on ``request.state.request_id`` for route handlers and dependencies
* echoes it in the ``X-Request-ID`` response header
* binds it into ``structlog`` ``contextvars`` so every log emitted while the
  request is in flight carries the same id

If the caller already supplied ``X-Request-ID`` we trust them (with a length
cap to keep log records sane) — this lets a frontend or a Telegram-bot
wrapper propagate its own correlation id across the boundary.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
_HEADER_BYTES = REQUEST_ID_HEADER.lower().encode("latin-1")
_MAX_INCOMING_ID_LEN = 64


class RequestIdMiddleware:
    """Pure ASGI request-id middleware.

    Avoids ``BaseHTTPMiddleware`` because its ``call_next`` re-raises
    exceptions *after* FastAPI's global ``Exception`` handler has already
    produced a response, which trips the test transport. Pure ASGI lets the
    inner ``ExceptionMiddleware`` swallow exceptions cleanly while still
    giving us access to ``Scope`` (for ``request.state``) and the outgoing
    ``http.response.start`` message (to inject the header).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        incoming = None
        for name, value in scope.get("headers", ()):
            if name == _HEADER_BYTES:
                try:
                    incoming = value.decode("latin-1")
                except UnicodeDecodeError:
                    incoming = None
                break

        request_id = (
            incoming[:_MAX_INCOMING_ID_LEN] if incoming else uuid.uuid4().hex
        )

        # Expose to handlers via ``request.state.request_id``.
        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        header_pair = (_HEADER_BYTES, request_id.encode("latin-1"))

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                # Strip any existing header to avoid duplicates from downstream.
                headers = [(k, v) for (k, v) in headers if k != _HEADER_BYTES]
                headers.append(header_pair)
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            structlog.contextvars.clear_contextvars()
