"""Smoke tests for utility functions."""

from src.services.telemetry import LatencyTracker, RequestMetrics, build_metrics


def test_build_metrics_basic() -> None:
    """build_metrics returns correct totals and efficiency."""
    m = build_metrics(
        latency_ms=100.0,
        input_tokens=100,
        output_tokens=50,
        retrieval_docs=3,
        max_relevance=0.85,
    )
    assert isinstance(m, RequestMetrics)
    assert m.total_tokens == 150
    assert m.token_efficiency == 0.5
    assert m.latency_ms == 100.0
    assert m.retrieval_docs == 3


def test_build_metrics_zero_input_tokens() -> None:
    """build_metrics handles zero input tokens without division error."""
    m = build_metrics(latency_ms=50.0, input_tokens=0, output_tokens=10)
    assert m.token_efficiency == 0.0
    assert m.total_tokens == 10


def test_latency_tracker() -> None:
    """LatencyTracker measures non-negative elapsed time."""
    with LatencyTracker() as t:
        _ = sum(range(100))
    assert t.elapsed_ms >= 0.0


def test_request_metrics_to_dict() -> None:
    """RequestMetrics.to_dict returns expected keys."""
    m = build_metrics(latency_ms=200.0, input_tokens=50, output_tokens=25)
    d = m.to_dict()
    assert "latency_ms" in d
    assert "input_tokens" in d
    assert "output_tokens" in d
    assert "total_tokens" in d
    assert "token_efficiency" in d
