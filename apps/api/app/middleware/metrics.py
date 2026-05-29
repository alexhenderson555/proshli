"""HTTP request-latency Prometheus middleware.

Exposes ``proshli_http_request_duration_seconds`` — a histogram labelled
by route template, method, and status code — so Grafana can render the
RED triad (rate, errors, duration) against the FastAPI surface without
parsing access logs.

Implementation notes
====================

* **Route template, not raw path.** Without this guard, ``/vacancies/123``
  and ``/vacancies/124`` produce different label values; with hundreds of
  vacancies the Prometheus series count blows up. We resolve the matched
  route's ``path_format`` (the original ``"/vacancies/{vacancy_id}"`` string)
  via ``scope["route"]`` once routing has run, and fall back to ``"unknown"``
  for 404s.
* **Pure ASGI**, not ``BaseHTTPMiddleware``. Same reasoning as
  ``RequestIdMiddleware`` — keeps the exception flow simple and lets us
  observe ``http.response.start`` to read the status code before the
  response body is sent.
* **Histogram buckets** are tuned for typical FastAPI handler latencies
  (5ms–10s). Bucket count stays low to keep the registry small under
  high request volume.

Counters live at module scope so re-importing this module under tests
does not duplicate them in the Prometheus default registry.
"""

from __future__ import annotations

import time

from prometheus_client import Histogram
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Buckets in seconds. The defaults (0.005..10) match Prometheus' own
# recommended HTTP buckets and cover everything from a cached health
# check (<5ms) up to the 10s task-soft-time-limit boundary.
HTTP_REQUEST_DURATION = Histogram(
    "proshli_http_request_duration_seconds",
    "HTTP request latency, by route template, method, and status code.",
    labelnames=("route", "method", "status"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


def _resolve_route_template(scope: Scope) -> str:
    """Return the original route template, e.g. ``"/vacancies/{vacancy_id}"``.

    Starlette stashes the matched route on ``scope["route"]`` after the
    router runs. If the request 404'd before matching anything, we use
    ``"unknown"`` to avoid leaking the raw path into the label and
    blowing up cardinality from scanner traffic.
    """
    route = scope.get("route")
    if route is not None:
        # Starlette ``Route`` exposes ``path``; ``Mount`` exposes ``path``
        # too. ``APIRoute`` (FastAPI) keeps the format string in ``path``.
        path = getattr(route, "path", None)
        if isinstance(path, str) and path:
            return path
    return "unknown"


class MetricsMiddleware:
    """Pure-ASGI middleware that records request duration."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip self-instrumentation: scraping /metrics would otherwise
        # generate a request series for itself every scrape interval.
        if scope.get("path") == "/metrics":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        start = time.perf_counter()
        status_holder: dict[str, int] = {"status": 0}

        async def send_capturing_status(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = int(message.get("status", 0))
            await send(message)

        try:
            await self.app(scope, receive, send_capturing_status)
        finally:
            elapsed = time.perf_counter() - start
            route = _resolve_route_template(scope)
            # Status defaults to 500 if the inner app never sent a
            # response.start (e.g. a connection drop) so error budgets
            # see the failure rather than silently dropping the sample.
            status = status_holder["status"] or 500
            HTTP_REQUEST_DURATION.labels(
                route=route,
                method=method,
                status=str(status),
            ).observe(elapsed)
