"""Telemetry — Dual-export: Langfuse v3 + Arize Phoenix via shared OTel TracerProvider.

Architecture:
  One global OTel TracerProvider with two OTLP span exporters:
    1. OTLPSpanExporter → Langfuse v3 /api/public/otel (sessions, users, scores, tags)
    2. OTLPSpanExporter → Arize Phoenix (evaluation, sessions, annotations)

  LangChainInstrumentor patches LangChain to emit OTel spans automatically.
  Both backends receive identical span data via standard OTLP/HTTP.

Per-request attributes (session_id, user_id, tags) are set on a parent OTel span
so they propagate to both Langfuse and Phoenix simultaneously.

All services run 100% locally — no cloud connections.
"""

import base64
import logging
import time
from dataclasses import dataclass

import httpx
from opentelemetry import trace

from src.config.settings import settings

logger = logging.getLogger("agentops.service.telemetry")

# ---------------------------------------------------------------------------
# Lazy globals — initialized once on startup via init_telemetry()
# ---------------------------------------------------------------------------
_phoenix_session = None
_initialized = False
_tracer = None


@dataclass
class RequestMetrics:
    """Token efficiency and latency metrics for a single request."""

    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    token_efficiency: float = 0.0  # output / input ratio
    retrieval_docs: int = 0
    max_relevance: float = 0.0  # orchestrator relevance score

    def log(self) -> None:
        logger.info(
            "request_metrics | tokens_in=%d tokens_out=%d tokens_total=%d "
            "efficiency=%.2f latency=%.0fms docs=%d relevance=%.3f",
            self.input_tokens,
            self.output_tokens,
            self.total_tokens,
            self.token_efficiency,
            self.latency_ms,
            self.retrieval_docs,
            self.max_relevance,
        )

    def to_dict(self) -> dict:
        return {
            "latency_ms": round(self.latency_ms, 1),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "token_efficiency": round(self.token_efficiency, 3),
            "retrieval_docs": self.retrieval_docs,
            "max_relevance": round(self.max_relevance, 3),
        }


# ---------------------------------------------------------------------------
# Initialization — Shared TracerProvider with dual export
# ---------------------------------------------------------------------------


def init_telemetry() -> None:
    """Initialize dual-export tracing (Langfuse + Phoenix). Call once at startup."""
    global _phoenix_session, _initialized, _tracer

    if _initialized:
        logger.debug("telemetry_skip | reason=already_initialized")
        return

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider()

    # --- Phoenix: Launch in-process app + add OTLP exporter ----------------
    if settings.phoenix_enabled:
        try:
            import phoenix as px

            _phoenix_session = px.launch_app(host="0.0.0.0", port=settings.phoenix_port)  # noqa: S104
            logger.info("phoenix_init | port=%d", settings.phoenix_port)

            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            phoenix_exporter = OTLPSpanExporter(
                endpoint=f"http://localhost:{settings.phoenix_port}/v1/traces"
            )
            provider.add_span_processor(BatchSpanProcessor(phoenix_exporter))
            logger.info(
                "phoenix_otlp_exporter | endpoint=http://localhost:%d/v1/traces",
                settings.phoenix_port,
            )
        except Exception:
            logger.warning("phoenix_init_error", exc_info=True)

    # --- Langfuse: OTLP exporter to /api/public/otel endpoint ---------------
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter as LangfuseOTLPExporter,
        )

        auth_bytes = f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}".encode()
        auth_b64 = base64.b64encode(auth_bytes).decode()

        langfuse_exporter = LangfuseOTLPExporter(
            endpoint=f"{settings.langfuse_internal_host}/api/public/otel/v1/traces",
            headers={
                "Authorization": f"Basic {auth_b64}",
                "x-langfuse-ingestion-version": "4",
            },
        )
        provider.add_span_processor(BatchSpanProcessor(langfuse_exporter))
        logger.info(
            "langfuse_otlp_exporter | endpoint=%s/api/public/otel/v1/traces",
            settings.langfuse_internal_host,
        )
    except Exception:
        logger.warning("langfuse_otlp_exporter_error", exc_info=True)

    # --- Register as the global TracerProvider -----------------------------
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("agentops")

    # --- Instrument LangChain via OpenInference ----------------------------
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor

        LangChainInstrumentor().instrument()
        logger.info("otel_langchain_instrumented")
    except Exception:
        logger.warning("langchain_instrumentor_error", exc_info=True)

    _initialized = True
    logger.info(
        "telemetry_ready | phoenix=%s langfuse=enabled",
        "enabled" if _phoenix_session else "disabled",
    )


# ---------------------------------------------------------------------------
# Tracer access
# ---------------------------------------------------------------------------


def get_tracer():
    """Return the OTel tracer (or a no-op tracer if not initialized)."""
    return _tracer or trace.get_tracer("agentops")


# ---------------------------------------------------------------------------
# Trace URL helpers
# ---------------------------------------------------------------------------


def get_trace_url(trace_id: str | None = None) -> str | None:
    """Build a Langfuse trace URL for the browser."""
    if trace_id:
        return f"{settings.langfuse_public_url}/trace/{trace_id}"
    return None


def get_phoenix_url() -> str | None:
    """Return the Phoenix dashboard URL if available."""
    if _phoenix_session is not None:
        return f"http://localhost:{settings.phoenix_port}"
    return None


def get_current_trace_id() -> str | None:
    """Get the current OTel trace ID as a 32-char hex string."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id:
        return format(ctx.trace_id, "032x")
    return None


# ---------------------------------------------------------------------------
# Langfuse scoring (REST API — no SDK needed)
# ---------------------------------------------------------------------------


def _langfuse_auth_header() -> str:
    """Build Basic auth header for Langfuse public API."""
    token = base64.b64encode(
        f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}".encode()
    ).decode()
    return f"Basic {token}"


async def score_trace(
    trace_id: str,
    name: str,
    value: float,
    comment: str | None = None,
    data_type: str = "NUMERIC",
    score_id: str | None = None,
) -> None:
    """Score a trace in Langfuse via REST API.

    Args:
        score_id: Optional idempotency key — prevents duplicate scores on retry.
    """
    try:
        payload: dict = {
            "traceId": trace_id,
            "name": name,
            "value": value,
            "dataType": data_type,
        }
        if comment:
            payload["comment"] = comment
        if score_id:
            payload["id"] = score_id

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.langfuse_internal_host}/api/public/scores",
                headers={
                    "Authorization": _langfuse_auth_header(),
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code < 300:
                logger.debug("langfuse_score | trace=%s name=%s value=%.1f", trace_id, name, value)
            else:
                logger.warning(
                    "langfuse_score_error | status=%d body=%s",
                    resp.status_code,
                    resp.text[:200],
                )
    except Exception:
        logger.warning("langfuse_score_error", exc_info=True)


async def annotate_phoenix_trace(
    trace_id: str,
    name: str,
    label: str | None = None,
    score: float | None = None,
    explanation: str | None = None,
) -> None:
    """Annotate a trace in Phoenix via REST API."""
    if _phoenix_session is None:
        return
    try:
        annotation = {
            "trace_id": trace_id,
            "name": name,
            **({"label": label} if label else {}),
            **({"score": score} if score is not None else {}),
            **({"explanation": explanation} if explanation else {}),
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"http://localhost:{settings.phoenix_port}/v1/trace_annotations",
                json={"data": [annotation]},
            )
            if resp.status_code < 300:
                logger.debug("phoenix_annotation | trace=%s name=%s", trace_id, name)
            else:
                logger.warning(
                    "phoenix_annotation_error | status=%d body=%s",
                    resp.status_code,
                    resp.text[:200],
                )
    except Exception:
        logger.warning("phoenix_annotation_error", exc_info=True)


# ---------------------------------------------------------------------------
# Latency tracking
# ---------------------------------------------------------------------------


class LatencyTracker:
    """Context manager to measure wall-clock latency."""

    def __init__(self) -> None:
        self._start: float = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> "LatencyTracker":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000


def build_metrics(
    latency_ms: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
    retrieval_docs: int = 0,
    max_relevance: float = 0.0,
) -> RequestMetrics:
    """Build a RequestMetrics object with computed efficiency."""
    total = input_tokens + output_tokens
    efficiency = (output_tokens / input_tokens) if input_tokens > 0 else 0.0
    return RequestMetrics(
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total,
        token_efficiency=efficiency,
        retrieval_docs=retrieval_docs,
        max_relevance=max_relevance,
    )
