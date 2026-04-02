"""LLM service — ChatOllama wrapper for local Ollama inference.

Wraps langchain_ollama.ChatOllama as a singleton for the application.
Single model (no MoE) — simplified from the main aeromat project.
"""

import logging

from langchain_ollama import ChatOllama

from src.config.settings import settings

logger = logging.getLogger("agentops.service.llm")

_llm_instance: ChatOllama | None = None


def get_llm() -> ChatOllama:
    """Return a configured ChatOllama instance (cached singleton)."""
    global _llm_instance

    if _llm_instance is None:
        logger.info(
            "llm_init | model=%s base_url=%s temperature=%.1f num_ctx=%d",
            settings.llm_model,
            settings.llm_base_url,
            settings.llm_temperature,
            settings.llm_num_ctx,
        )
        _llm_instance = ChatOllama(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            num_ctx=settings.llm_num_ctx,
        )
        logger.info("llm_ready | model=%s", settings.llm_model)

    return _llm_instance
