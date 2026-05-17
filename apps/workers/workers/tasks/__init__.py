"""Celery task modules.

Each task is a sync thin shim that:

1. Bridges to async via ``workers._async_bridge.run_with_session``
2. Delegates the actual work to ``app.services.*`` (which already has tests)
3. Returns a JSON-serialisable dict so the result backend is debuggable
"""
