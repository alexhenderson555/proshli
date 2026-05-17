"""Global exception handlers.

Goal: never leak a raw stack trace or internal driver error message to a
client. Every unhandled exception becomes a stable JSON envelope::

    {
      "detail": "Internal server error",
      "request_id": "<uuid hex>"
    }

structlog records the full traceback server-side with the same request id so
support can correlate. The handler is intentionally permissive about
``HTTPException`` and Starlette's own validation errors — FastAPI's defaults
for those are fine; we only step in for the actually-unhandled cases.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Install global handlers on ``app``. Idempotent."""

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001
        request_id = getattr(request.state, "request_id", None)
        log.exception(
            "request.unhandled_exception",
            path=request.url.path,
            method=request.method,
            request_id=request_id,
        )
        body: dict[str, Any] = {"detail": "Internal server error"}
        headers: dict[str, str] = {}
        if request_id:
            body["request_id"] = request_id
            # ServerErrorMiddleware sends our response with the *outer* send,
            # which sits above RequestIdMiddleware in the stack — so the
            # middleware's send-wrapper never runs for the 500 path. Inject
            # the header here so clients still get correlation parity between
            # the JSON envelope and the response headers.
            headers["X-Request-ID"] = request_id
        return JSONResponse(status_code=500, content=body, headers=headers)
