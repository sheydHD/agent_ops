"""Langfuse Prompt Management — fetch and list prompts from Langfuse.

Uses the Langfuse Python SDK for prompt retrieval and the REST API
for listing all available prompts.
"""

import logging

import httpx
from langfuse import Langfuse

from src.config.settings import settings

logger = logging.getLogger("agentops.service.langfuse_prompts")

_langfuse_client: Langfuse | None = None


def _get_langfuse() -> Langfuse:
    """Return a cached Langfuse client instance."""
    global _langfuse_client
    if _langfuse_client is None:
        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_internal_host,
        )
        logger.info("langfuse_client_init | host=%s", settings.langfuse_internal_host)
    return _langfuse_client


def get_prompt_text(name: str, label: str = "production") -> str | None:
    """Fetch a prompt's compiled text from Langfuse by name and label.

    Returns the prompt string, or None if not found.
    """
    try:
        client = _get_langfuse()
        prompt = client.get_prompt(name, label=label)
        compiled = prompt.compile()
        logger.info("langfuse_prompt_fetched | name=%s label=%s", name, label)
        return compiled
    except Exception:
        logger.warning("langfuse_prompt_fetch_error | name=%s", name, exc_info=True)
        return None


async def list_prompts() -> list[dict]:
    """List all prompts from Langfuse via REST API.

    Returns a list of dicts with keys: name, type, labels, latest_version.
    """
    import base64

    token = base64.b64encode(
        f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}".encode()
    ).decode()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.langfuse_internal_host}/api/public/v2/prompts",
                headers={
                    "Authorization": f"Basic {token}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code >= 300:
                logger.warning(
                    "langfuse_list_prompts_error | status=%d body=%s",
                    resp.status_code,
                    resp.text[:200],
                )
                return []

            data = resp.json()
            prompts = data.get("data", [])

            result = [
                {
                    "name": p.get("name", ""),
                    "type": p.get("type", "text"),
                    "labels": p.get("labels", []),
                    "latest_version": p.get("version"),
                }
                for p in prompts
            ]

            logger.info("langfuse_list_prompts | count=%d", len(result))
            return result
    except Exception:
        logger.warning("langfuse_list_prompts_error", exc_info=True)
        return []
