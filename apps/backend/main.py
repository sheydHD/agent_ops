"""AgentOps Demo — FastAPI Backend Entry Point.

Initializes:
  1. Structured logging (JSON or text)
  2. AgentOps telemetry (Langfuse + Phoenix + OTel)
  3. Document ingestion into ChromaDB (from ./data/)
  4. FastAPI app with request-tracing middleware + routes
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.logging_config import setup_logging
from src.config.settings import settings

# Configure logging BEFORE any other module-level logger is created so the
# root handler is in place from the start.
setup_logging(level=settings.log_level, log_format=settings.log_format)

logger = logging.getLogger("agentops.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info(
        "startup_begin | llm=%s base_url=%s embed=%s",
        settings.llm_model,
        settings.llm_base_url,
        settings.embedding_model,
    )

    # 1. Initialize telemetry (Langfuse + Phoenix + OTel)
    from src.services.telemetry import init_telemetry

    init_telemetry()

    # 2. Auto-ingest documents from data/ directory
    from src.services.rag_service import get_collection_count, ingest_documents

    existing = get_collection_count()
    if existing == 0:
        logger.info("vectorstore_empty | ingesting from dir=%s", settings.docs_dir)
        count = ingest_documents()
        logger.info("ingest_complete | chunks=%d", count)
    else:
        logger.info("vectorstore_ready | docs=%d", existing)

    logger.info("startup_complete | api=http://0.0.0.0:8000")

    yield

    # --- Shutdown ---
    logger.info("shutdown")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=(
        "AgentOps Demo — RAG pipeline with Langfuse + Phoenix + OTel observability. 100% local."
    ),
    lifespan=lifespan,
)

# --- Middleware (order matters: last added = first executed) ----------------
# CORS first so preflight requests are handled before any other middleware.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
)

# Request tracing — assigns request_id, logs start/finish + latency
from src.api.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# --- Routes ----------------------------------------------------------------
from src.api.routes.chat import router as chat_router
from src.api.routes.feedback import router as feedback_router
from src.api.routes.health import router as health_router
from src.api.routes.prompts import router as prompts_router

app.include_router(chat_router)
app.include_router(feedback_router)
app.include_router(health_router)
app.include_router(prompts_router)


# --- Global exception handler — never leak stack traces to clients ---------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception | path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
