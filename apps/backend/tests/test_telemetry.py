"""Tests for telemetry utilities."""

from src.services.telemetry import RequestMetrics, build_metrics, LatencyTracker


class TestRequestMetrics:
    def test_to_dict(self):
        m = RequestMetrics(
            latency_ms=123.456,
            input_tokens=100,
            output_tokens=30,
            total_tokens=130,
            token_efficiency=0.3,
            retrieval_docs=3,
            max_relevance=0.82,
        )
        d = m.to_dict()
        assert d["latency_ms"] == 123.5
        assert d["input_tokens"] == 100
        assert d["output_tokens"] == 30
        assert d["total_tokens"] == 130
        assert d["token_efficiency"] == 0.3
        assert d["retrieval_docs"] == 3
        assert d["max_relevance"] == 0.82


class TestBuildMetrics:
    def test_basic(self):
        m = build_metrics(latency_ms=200.0, input_tokens=50, output_tokens=25)
        assert m.latency_ms == 200.0
        assert m.total_tokens == 75
        assert m.token_efficiency == 0.5

    def test_zero_input_tokens(self):
        m = build_metrics(latency_ms=100.0, input_tokens=0, output_tokens=10)
        assert m.token_efficiency == 0.0

    def test_with_retrieval(self):
        m = build_metrics(
            latency_ms=300.0,
            input_tokens=100,
            output_tokens=50,
            retrieval_docs=4,
            max_relevance=0.9,
        )
        assert m.retrieval_docs == 4
        assert m.max_relevance == 0.9


class TestLatencyTracker:
    def test_measures_time(self):
        with LatencyTracker() as tracker:
            # Just run a trivial operation
            _ = sum(range(1000))
        assert tracker.elapsed_ms >= 0
