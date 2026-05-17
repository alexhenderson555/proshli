"""HTTP middleware: request-id correlation, rate-limiting, structlog binding.

Each module exposes a single ``add_*`` helper that wires the middleware into a
``FastAPI`` instance.  They're applied in :func:`app.main.create_app` in this
order:

1. ``RequestIdMiddleware`` — generates / propagates ``X-Request-ID`` first so
   downstream middleware and route handlers can include it in log records.
2. ``StructlogContextMiddleware`` — binds the request id into structlog's
   ``contextvars`` so every log line during the request is tagged.
3. ``CORSMiddleware`` (FastAPI built-in) — last, because preflight responses
   must inherit the request id header.
"""
