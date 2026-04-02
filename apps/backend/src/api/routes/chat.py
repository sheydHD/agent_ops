"""Chat API route — POST /api/chat."""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from src.agents.rag_agent import ask
from src.config.logging_config import conversation_id_ctx
from src.config.settings import settings
from src.services.evaluation import evaluate_faithfulness
from src.services.telemetry import annotate_phoenix_trace, score_trace

logger = logging.getLogger("agentops.api.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: str | None = None
    user_id: str | None = None
    prompt_name: str | None = None


class ChatResponse(BaseModel):
    message: str
    conversation_id: str
    metadata: dict
    timestamp: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks) -> ChatResponse:
    """Send a message and receive a RAG-augmented response."""
    conversation_id = request.conversation_id or str(uuid.uuid4())
    user_id = request.user_id or "anonymous"

    # Set conversation_id in context so all downstream logs include it
    token = conversation_id_ctx.set(conversation_id)

    try:
        logger.info(
            "chat_request | conv=%s user=%s msg_len=%d",
            conversation_id,
            user_id,
            len(request.message),
        )

        result = await ask(
            request.message,
            session_id=conversation_id,
            user_id=user_id,
            prompt_name=request.prompt_name,
        )

        logger.info(
            "chat_response | conv=%s answer_len=%d sources=%d latency=%.0fms",
            conversation_id,
            len(result["answer"]),
            len(result["source_documents"]),
            result["metrics"]["latency_ms"],
        )

        # --- Score the trace in Langfuse + annotate in Phoenix -------
        trace_id = result.get("trace_id")
        route_type = result.get("route_type", "general")

        if trace_id:
            retrieval_docs = result["metrics"].get("retrieval_docs", 0)
            answer_len = len(result["answer"])

            if route_type == "rag":
                # RAG path: score retrieval quality (0-1 based on docs found)
                retrieval_score = min(retrieval_docs / 4.0, 1.0)
                await score_trace(
                    trace_id,
                    name="retrieval_quality",
                    value=retrieval_score,
                    comment=f"Retrieved {retrieval_docs} documents (target: 4)",
                    score_id=f"{trace_id}-retrieval_quality",
                )
            else:
                # General path: no retrieval expected — score routing confidence
                relevance = result["metrics"].get("max_relevance", 0.0)
                routing_score = 1.0 - relevance  # higher = better routing decision
                await score_trace(
                    trace_id,
                    name="routing_confidence",
                    value=round(routing_score, 3),
                    comment=f"General query correctly routed (max_relevance={relevance:.3f})",
                    score_id=f"{trace_id}-routing_confidence",
                )

            # Response completeness — route-aware thresholds
            if answer_len > 50:
                completeness = 1.0
            elif answer_len > 20:
                completeness = 0.5
            else:
                completeness = 0.0

            await score_trace(
                trace_id,
                name="response_completeness",
                value=completeness,
                comment=f"Answer length: {answer_len} chars (route: {route_type})",
                score_id=f"{trace_id}-response_completeness",
            )

            # Phoenix annotation — route-aware quality label
            if route_type == "rag":
                rag_score = min(retrieval_docs / 4.0, 1.0)
                phoenix_label = "good" if rag_score > 0.5 else "needs_improvement"
                phoenix_score = rag_score
                phoenix_explanation = (
                    f"RAG retrieval: {retrieval_docs}/4 docs, answer: {answer_len} chars"
                )
            else:
                phoenix_label = "good" if answer_len > 20 else "needs_improvement"
                phoenix_score = completeness
                phoenix_explanation = f"General query, answer: {answer_len} chars"

            await annotate_phoenix_trace(
                trace_id,
                name="auto_quality",
                label=phoenix_label,
                score=phoenix_score,
                explanation=phoenix_explanation,
            )

            # Faithfulness evaluation — background LLM-as-judge (RAG only)
            if route_type == "rag" and settings.faithfulness_eval_enabled:
                background_tasks.add_task(
                    evaluate_faithfulness,
                    trace_id=trace_id,
                    question=request.message,
                    answer=result["answer"],
                    context=result.get("context", ""),
                )

        return ChatResponse(
            message=result["answer"],
            conversation_id=conversation_id,
            metadata={
                **result["metrics"],
                "trace_id": result.get("trace_id"),
                "route_type": result.get("route_type"),
                "doc_scores": result.get("doc_scores", []),
                "source_documents": result["source_documents"],
                "trace_url": result["trace_url"],
                "phoenix_url": result["phoenix_url"],
            },
            timestamp=datetime.now(UTC).isoformat(),
        )
    except Exception:
        logger.exception("chat_error | conv=%s", conversation_id)
        raise
    finally:
        conversation_id_ctx.reset(token)
