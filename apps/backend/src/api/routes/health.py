"""Health API route — GET /health."""

import logging

import httpx
from fastapi import APIRouter

from src.config.settings import settings
from src.services.rag_service import get_collection_count

logger = logging.getLogger("agentops.api.health")

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Service health check — verifies Ollama, ChromaDB, and Langfuse connectivity."""
    status = {
        "status": "ok",
        "ollama": "unknown",
        "chromadb": "unknown",
        "langfuse": "unknown",
        "phoenix": "unknown",
        "documents_indexed": 0,
    }

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.llm_base_url}/api/tags")
            if resp.status_code == 200:
                status["ollama"] = "connected"
            else:
                status["ollama"] = "error"
                status["status"] = "degraded"
                logger.warning("health_ollama | status=error http_status=%d", resp.status_code)
    except Exception as exc:
        status["ollama"] = "unreachable"
        status["status"] = "degraded"
        logger.warning("health_ollama | status=unreachable err=%s", exc)

    # Check ChromaDB
    try:
        count = get_collection_count()
        status["chromadb"] = "connected"
        status["documents_indexed"] = count
    except Exception as exc:
        status["chromadb"] = "error"
        status["status"] = "degraded"
        logger.warning("health_chromadb | status=error err=%s", exc)

    # Check Langfuse
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.langfuse_internal_host}/api/public/health")
            if resp.status_code == 200:
                status["langfuse"] = "connected"
            else:
                status["langfuse"] = "error"
                status["status"] = "degraded"
                logger.warning("health_langfuse | status=error http_status=%d", resp.status_code)
    except Exception as exc:
        status["langfuse"] = "unreachable"
        status["status"] = "degraded"
        logger.warning("health_langfuse | status=unreachable err=%s", exc)

    # Check Phoenix
    if settings.phoenix_enabled:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"http://localhost:{settings.phoenix_port}")
                status["phoenix"] = "running" if resp.status_code == 200 else "error"
        except Exception:
            status["phoenix"] = "not running"
    else:
        status["phoenix"] = "disabled"

    logger.debug(
        "health_result | overall=%s ollama=%s chroma=%s langfuse=%s phoenix=%s docs=%d",
        status["status"],
        status["ollama"],
        status["chromadb"],
        status["langfuse"],
        status["phoenix"],
        status["documents_indexed"],
    )

    return status
