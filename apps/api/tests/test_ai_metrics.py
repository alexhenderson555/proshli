"""AI metrics — unit tests for the Prometheus counter helpers.

We don't hit Anthropic here; the tests build a tiny fake ``Usage`` object
and verify the labelled counter bumps in the expected dimensions. The
``/metrics`` endpoint is also smoke-tested via the FastAPI test client.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.main import app
from app.services.ai_metrics import AI_CALLS, AI_TOKENS, record_outcome, record_usage


@dataclass
class _FakeUsage:
    """Stand-in for ``anthropic.types.Usage`` — only the fields we read."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


def _read_counter(counter: object, **labels: str) -> float:
    """Pull the current value of a labelled Counter sample.

    Goes through the global registry so a stale cache on the counter
    object itself can't hide a bump from us.
    """
    name = getattr(counter, "_name", "")  # e.g. "proshli_ai_tokens"
    metric = name + "_total"
    for sample in REGISTRY.collect():
        for s in sample.samples:
            if s.name == metric and all(s.labels.get(k) == v for k, v in labels.items()):
                return float(s.value)
    return 0.0


def test_record_usage_bumps_token_counters() -> None:
    """All four token kinds (input/output/cache_*) increment independently."""
    before_input = _read_counter(AI_TOKENS, endpoint="chat", kind="input")
    before_output = _read_counter(AI_TOKENS, endpoint="chat", kind="output")
    before_cache_read = _read_counter(AI_TOKENS, endpoint="chat", kind="cache_read")
    before_cache_create = _read_counter(AI_TOKENS, endpoint="chat", kind="cache_creation")

    record_usage(
        "chat",
        _FakeUsage(
            input_tokens=10,
            output_tokens=20,
            cache_read_input_tokens=7,
            cache_creation_input_tokens=3,
        ),
    )

    assert _read_counter(AI_TOKENS, endpoint="chat", kind="input") == before_input + 10
    assert _read_counter(AI_TOKENS, endpoint="chat", kind="output") == before_output + 20
    assert _read_counter(AI_TOKENS, endpoint="chat", kind="cache_read") == before_cache_read + 7
    assert (
        _read_counter(AI_TOKENS, endpoint="chat", kind="cache_creation")
        == before_cache_create + 3
    )


def test_record_usage_handles_none_and_missing_attrs() -> None:
    """``None`` and partially-populated usage objects do not raise."""
    record_usage("cover_letter", None)
    record_usage("cover_letter", _FakeUsage(input_tokens=5))  # no output / no cache
    # Verifying the call didn't blow up is the contract; counter sampling
    # is covered by the previous test.


def test_record_outcome_bumps_call_counter() -> None:
    """``success`` / ``error`` / ``fallback`` are tracked independently."""
    before_success = _read_counter(AI_CALLS, endpoint="topic_classify", outcome="success")
    before_error = _read_counter(AI_CALLS, endpoint="topic_classify", outcome="error")

    record_outcome("topic_classify", "success")
    record_outcome("topic_classify", "success")
    record_outcome("topic_classify", "error")

    assert (
        _read_counter(AI_CALLS, endpoint="topic_classify", outcome="success")
        == before_success + 2
    )
    assert (
        _read_counter(AI_CALLS, endpoint="topic_classify", outcome="error")
        == before_error + 1
    )


def test_metrics_endpoint_serves_prometheus_format() -> None:
    """``GET /metrics`` returns the registry in Prometheus exposition format."""
    record_usage("smoke", _FakeUsage(input_tokens=1, output_tokens=1))
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    # The counter names must appear in the exposition; the labels appear
    # only after at least one ``.inc()`` call, hence the bump above.
    assert "proshli_ai_tokens_total" in body
    assert 'endpoint="smoke"' in body
