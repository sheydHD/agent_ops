"""Async faithfulness evaluator — LLM-as-judge for RAG responses.

Runs as a FastAPI BackgroundTask after every RAG-mode response.
Judges whether the answer is faithful to the retrieved context and posts
the result as both a Langfuse score and a Phoenix annotation.

Labels: "faithful" | "partially_faithful" | "unfaithful"
Score:  1.0       | 0.5                   | 0.0
"""

import logging
import re

from langchain_core.messages import HumanMessage

from src.services.llm_service import get_llm
from src.services.telemetry import annotate_phoenix_trace, score_trace

logger = logging.getLogger("agentops.service.evaluation")

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_FAITHFULNESS_PROMPT = """\
You are a strict AI evaluator. Your task is to decide whether an assistant's \
answer is faithful to the provided context.

CONTEXT (from retrieval):
{context}

QUESTION: {question}

ANSWER: {answer}

INSTRUCTIONS:
- "faithful"           — every claim in the answer can be traced to the context.
- "partially_faithful" — most claims are in the context but 1-2 minor details are not.
- "unfaithful"         — the answer contains significant information absent from the context \
or contradicts it.

Respond with EXACTLY this format (one line):
LABEL: <faithful|partially_faithful|unfaithful>
REASON: <one concise sentence explaining your judgment>"""

_LABEL_TO_SCORE = {
    "faithful": 1.0,
    "partially_faithful": 0.5,
    "unfaithful": 0.0,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def evaluate_faithfulness(
    trace_id: str,
    question: str,
    answer: str,
    context: str,
) -> None:
    """Judge faithfulness and persist results to Langfuse + Phoenix.

    Designed to run as a background task — errors are logged, not raised.
    """
    if not context.strip():
        logger.debug("faithfulness_skip | trace=%s reason=no_context", trace_id)
        return

    try:
        prompt_text = _FAITHFULNESS_PROMPT.format(
            context=context[:4000],  # guard against huge contexts
            question=question,
            answer=answer,
        )
        llm = get_llm()
        llm_msg = await llm.ainvoke([HumanMessage(content=prompt_text)])
        raw = llm_msg.content.strip()

        label, reason = _parse_response(raw)
        score_value = _LABEL_TO_SCORE.get(label, 0.5)

        logger.info(
            "faithfulness_eval | trace=%s label=%s score=%.1f",
            trace_id,
            label,
            score_value,
        )

        # Post to Langfuse
        await score_trace(
            trace_id,
            name="faithfulness",
            value=score_value,
            comment=f"{label}: {reason}",
            score_id=f"{trace_id}-faithfulness",
        )

        # Post to Phoenix
        await annotate_phoenix_trace(
            trace_id,
            name="faithfulness",
            label=label,
            score=score_value,
            explanation=reason,
        )

    except Exception:
        logger.warning("faithfulness_eval_error | trace=%s", trace_id, exc_info=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_response(raw: str) -> tuple[str, str]:
    """Extract label and reason from LLM response.  Falls back gracefully."""
    label_match = re.search(
        r"LABEL:\s*(faithful|partially_faithful|unfaithful)", raw, re.IGNORECASE
    )
    reason_match = re.search(r"REASON:\s*(.+)", raw, re.IGNORECASE)

    label = label_match.group(1).lower() if label_match else "partially_faithful"
    reason = reason_match.group(1).strip() if reason_match else raw[:200]
    return label, reason
