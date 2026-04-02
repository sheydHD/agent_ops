"""Feedback API routes.

POST /api/feedback          — submit user thumbs up/down for a trace
POST /api/admin/dataset     — add a trace to a Langfuse evaluation dataset
"""

import logging

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.services.telemetry import score_trace

logger = logging.getLogger("agentops.api.feedback")

router = APIRouter(tags=["feedback"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class FeedbackRequest(BaseModel):
    trace_id: str = Field(..., min_length=1)
    sentiment: str = Field(..., pattern="^(positive|negative)$")
    comment: str | None = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    ok: bool


class DatasetRequest(BaseModel):
    trace_id: str = Field(..., min_length=1)
    input: str = Field(..., min_length=1, max_length=5000)
    expected_output: str | None = Field(default=None, max_length=5000)
    dataset_name: str | None = None


class DatasetResponse(BaseModel):
    ok: bool
    dataset_name: str
    item_id: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """Record a user thumbs-up (positive) or thumbs-down (negative) for a trace."""
    value = 1.0 if request.sentiment == "positive" else 0.0
    await score_trace(
        request.trace_id,
        name="user_feedback",
        value=value,
        data_type="BOOLEAN",
        comment=request.comment,
        score_id=f"{request.trace_id}-user_feedback",
    )
    logger.info("user_feedback | trace=%s sentiment=%s", request.trace_id, request.sentiment)
    return FeedbackResponse(ok=True)


@router.post("/api/admin/dataset", response_model=DatasetResponse)
async def add_to_dataset(request: DatasetRequest) -> DatasetResponse:
    """Add a trace as a dataset item in Langfuse for offline evaluation.

    Creates the dataset if it does not already exist.
    The item stores the original question as input (and optionally an expected
    answer), linked to the source trace for full traceability.
    """
    dataset_name = request.dataset_name or settings.langfuse_dataset_name
    item_id: str | None = None

    try:
        import base64

        auth = base64.b64encode(
            f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}".encode()
        ).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
        }
        base = settings.langfuse_internal_host

        # Ensure dataset exists — the API is idempotent on name conflict.
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{base}/api/public/datasets",
                headers=headers,
                json={"name": dataset_name},
            )

            # Create dataset item linked to the source trace
            payload: dict = {
                "datasetName": dataset_name,
                "input": {"question": request.input},
                "sourceTraceId": request.trace_id,
            }
            if request.expected_output:
                payload["expectedOutput"] = {"answer": request.expected_output}

            resp = await client.post(
                f"{base}/api/public/dataset-items",
                headers=headers,
                json=payload,
            )
            if resp.status_code < 300:
                item_id = resp.json().get("id")
                logger.info(
                    "dataset_item_created | dataset=%s trace=%s item=%s",
                    dataset_name,
                    request.trace_id,
                    item_id,
                )
            else:
                logger.warning(
                    "dataset_item_error | status=%d body=%s",
                    resp.status_code,
                    resp.text[:200],
                )
    except Exception:
        logger.warning("dataset_add_error", exc_info=True)

    return DatasetResponse(ok=True, dataset_name=dataset_name, item_id=item_id)
