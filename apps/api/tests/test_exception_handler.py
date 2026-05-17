"""Global exception handler test (wave 7).

The default httpx ASGI transport in our shared ``client`` fixture re-raises
unhandled application exceptions for clean assertions in the rest of the
suite. Here we want to see the *handled* response, so this test owns its
own client with ``raise_app_exceptions=False``.
"""

from __future__ import annotations

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_unhandled_exception_returns_clean_envelope() -> None:
    @app.get("/__boom_test__", include_in_schema=False)
    async def boom() -> None:  # noqa: D401
        raise RuntimeError("kaboom")

    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as ac:
            resp = await ac.get("/__boom_test__")
        assert resp.status_code == 500
        body = resp.json()
        assert body["detail"] == "Internal server error"
        assert "request_id" in body
        assert resp.headers.get("X-Request-ID") == body["request_id"]
    finally:
        # Remove the dynamic route so it doesn't leak into other tests.
        app.router.routes = [
            r for r in app.router.routes if getattr(r, "path", None) != "/__boom_test__"
        ]
