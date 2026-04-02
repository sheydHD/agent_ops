"""Prompts API route — list and fetch Langfuse-managed prompts."""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from src.services.langfuse_prompt_service import list_prompts

logger = logging.getLogger("agentops.api.prompts")

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class PromptSummary(BaseModel):
    name: str
    type: str
    labels: list[str]
    latest_version: int | None


class PromptsListResponse(BaseModel):
    prompts: list[PromptSummary]


@router.get("", response_model=PromptsListResponse)
async def get_prompts() -> PromptsListResponse:
    """List all prompts available in Langfuse."""
    raw = await list_prompts()
    return PromptsListResponse(
        prompts=[PromptSummary(**p) for p in raw],
    )
