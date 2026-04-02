"""Centralized logging configuration.

Provides:
  - JSON-formatted logs for production (machine-parseable, log-aggregator friendly)
  - Human-readable colored logs for local development
  - Request-scoped context (request_id, conversation_id) via contextvars
  - Noise suppression for chatty third-party libraries
"""

import logging
import logging.config
import sys
from contextvars import ContextVar
from typing import Any

# ---------------------------------------------------------------------------
# Context variables — set per-request by the middleware, automatically
# injected into every log record by _ContextFilter.
# ---------------------------------------------------------------------------
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
conversation_id_ctx: ContextVar[str] = ContextVar("conversation_id", default="-")

# Expose for use in middleware / route handlers
__all__ = [
    "request_id_ctx",
    "conversation_id_ctx",
    "setup_logging",
]

# ---------------------------------------------------------------------------
# Third-party loggers that should be quieted to WARNING unless explicitly
# turned up.  Add more here as needed.
# ---------------------------------------------------------------------------
_NOISY_LOGGERS = (
    "chromadb",
    "httpcore",
    "httpx",
    "uvicorn.access",
    "opentelemetry",
    "openinference",
    "langchain",
    "langchain_community",
    "langchain_core",
    "langfuse",
    "phoenix",
    "arize",
    "urllib3",
    "watchfiles",
)


class _ContextFilter(logging.Filter):
    """Inject request-scoped context into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("-")  # type: ignore[attr-defined]
        record.conversation_id = conversation_id_ctx.get("-")  # type: ignore[attr-defined]
        return True


class _JsonFormatter(logging.Formatter):
    """Lightweight JSON formatter — no external dependency required.

    Produces one JSON object per line, ideal for structured log aggregation
    (Datadog, ELK, CloudWatch, etc.).
    """

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        log_entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "conversation_id": getattr(record, "conversation_id", "-"),
        }
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data  # type: ignore[attr-defined]
        return json.dumps(log_entry, default=str)


# ---------------------------------------------------------------------------
# Public setup function
# ---------------------------------------------------------------------------

_LOG_FMT_TEXT = (
    "%(asctime)s | %(levelname)-8s | %(name)-30s | rid=%(request_id)s | %(message)s"
)
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: str = "INFO",
    log_format: str = "text",
) -> None:
    """Configure the root logger for the entire application.

    Args:
        level: Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: ``"text"`` for human-readable or ``"json"`` for structured.
    """
    effective_level = getattr(logging, level.upper(), logging.INFO)

    # Build handler
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_ContextFilter())

    if log_format.lower() == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(fmt=_LOG_FMT_TEXT, datefmt=_LOG_DATEFMT))

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(effective_level)
    # Remove any pre-existing handlers (e.g. from basicConfig)
    root.handlers.clear()
    root.addHandler(handler)

    # Suppress noisy third-party loggers
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger(__name__).debug(
        "Logging configured — level=%s, format=%s", level, log_format
    )
