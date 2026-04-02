"""Request lifecycle middleware — correlation IDs and access logging.

Every inbound request gets a unique ``X-Request-ID`` (or reuses the one
supplied by the caller / reverse proxy). The ID is:

1. Stored in a ContextVar so every log line includes it automatically.
2. Returned in the response headers for end-to-end traceability.

The middleware also emits structured start/finish log lines with status code
and wall-clock duration — replacing the need for a separate access log.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.config.logging_config import conversation_id_ctx, request_id_ctx

logger = logging.getLogger("agentops.middleware")

# Paths that should only log at DEBUG (avoid noise from probes / static).
_QUIET_PATHS = frozenset({"/health", "/docs", "/openapi.json", "/favicon.ico"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach a request ID and log every request/response pair."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # --- Resolve or generate request ID ---
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(rid)

        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "-"

        log_level = logging.DEBUG if path in _QUIET_PATHS else logging.INFO

        logger.log(
            log_level,
            "request_start  | %s %s | client=%s",
            method,
            path,
            client,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_error  | %s %s | %.0fms | unhandled exception",
                method,
                path,
                elapsed_ms,
            )
            raise
        finally:
            request_id_ctx.reset(token)

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Choose log level based on status code
        status = response.status_code
        if status >= 500:
            finish_level = logging.ERROR
        elif status >= 400:
            finish_level = logging.WARNING
        else:
            finish_level = log_level

        logger.log(
            finish_level,
            "request_finish | %s %s | status=%d | %.0fms",
            method,
            path,
            status,
            elapsed_ms,
        )

        response.headers["X-Request-ID"] = rid
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to every response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        return response
