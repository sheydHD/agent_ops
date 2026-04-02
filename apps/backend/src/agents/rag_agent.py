"""RAG Agent — Retrieval-Augmented Generation with LCEL (LangChain Expression Language).

Combines:
  - Orchestrator (semantic routing via relevance scores)
  - ChromaDB retriever (local vector store)
  - ChatOllama LLM (local inference via Ollama)
  - Dual-export OTel tracing (Langfuse + Phoenix via shared TracerProvider)

The orchestrator classifies each query as "rag" or "general":
  - RAG: query is relevant to the knowledge base → inject retrieved context
  - General: query is unrelated → answer with the base LLM only

Uses pure LCEL pipe operators (LangChain 1.x — no legacy chains).
Per-request OTel attributes (session_id, user_id, tags) propagate to both backends.
"""

import logging

from langchain_core.prompts import ChatPromptTemplate

from src.agents.orchestrator import RouteType, classify_query
from src.services.langfuse_prompt_service import get_prompt_text
from src.services.llm_service import get_llm
from src.services.telemetry import (
    LatencyTracker,
    build_metrics,
    get_current_trace_id,
    get_phoenix_url,
    get_trace_url,
    get_tracer,
)

logger = logging.getLogger("agentops.agent.rag")

# ---------------------------------------------------------------------------
# Prompts (ChatPromptTemplate — modern LangChain standard)
# ---------------------------------------------------------------------------
RAG_SYSTEM_PROMPT = """\
Use the following context to answer the question. If the context does not \
contain enough information, say so honestly — do not make up facts.

Context:
{context}"""

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", RAG_SYSTEM_PROMPT),
        ("human", "{input}"),
    ]
)

CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant. Answer the following question concisely."),
        ("human", "{input}"),
    ]
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _build_prompt(prompt_name: str | None) -> tuple[ChatPromptTemplate, ChatPromptTemplate]:
    """Return (rag_prompt, chat_prompt) — either default or Langfuse-managed."""
    if not prompt_name:
        return RAG_PROMPT, CHAT_PROMPT

    custom_text = get_prompt_text(prompt_name)
    if not custom_text:
        logger.warning("langfuse_prompt_not_found | name=%s falling_back=default", prompt_name)
        return RAG_PROMPT, CHAT_PROMPT

    logger.info("langfuse_prompt_applied | name=%s", prompt_name)

    # Build a RAG variant that prepends the custom system prompt + context
    custom_rag_system = (
        custom_text + "\n\nUse the following context to answer the question. "
        "If the context does not contain enough information, say so honestly "
        "— do not make up facts.\n\nContext:\n{context}"
    )
    rag_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", custom_rag_system),
            ("human", "{input}"),
        ]
    )

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", custom_text),
            ("human", "{input}"),
        ]
    )

    return rag_prompt, chat_prompt


async def ask(
    question: str,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
    prompt_name: str | None = None,
) -> dict:
    """Ask a question — orchestrator decides RAG vs general path.

    The orchestrator performs a single similarity search with relevance scores.
    If relevant documents are found above the threshold, the RAG pipeline is
    used with those pre-fetched docs (no redundant retrieval). Otherwise the
    query goes directly to the general-purpose LLM.

    Returns:
        {
            "answer": str,
            "source_documents": list[str],
            "route_type": "rag" | "general",
            "metrics": RequestMetrics dict,
            "trace_url": str | None,
            "phoenix_url": str | None,
            "trace_id": str | None,
        }
    """
    # --- Orchestrator: classify query and pre-fetch relevant docs ----------
    decision = await classify_query(question)
    mode = decision.route.value

    logger.info(
        "ask_start | mode=%s reason=%s max_relevance=%.3f question_len=%d prompt=%s",
        mode,
        decision.reason,
        decision.max_relevance,
        len(question),
        prompt_name or "default",
    )

    rag_prompt, chat_prompt = _build_prompt(prompt_name)

    tracer = get_tracer()

    with tracer.start_as_current_span("rag-pipeline") as span:
        # --- Set OTel attributes for Langfuse ---
        span.set_attribute("langfuse.trace.name", f"Query ({mode})")
        span.set_attribute("langfuse.trace.input", question)
        if session_id:
            span.set_attribute("langfuse.session.id", session_id)
        if user_id:
            span.set_attribute("langfuse.user.id", user_id)
        span.set_attribute("langfuse.trace.tags", ["demo", mode])
        span.set_attribute("langfuse.trace.metadata.mode", mode)
        span.set_attribute("langfuse.trace.metadata.route_reason", decision.reason)
        span.set_attribute("langfuse.trace.metadata.max_relevance", f"{decision.max_relevance:.3f}")
        span.set_attribute("langfuse.trace.metadata.question_length", str(len(question)))

        # --- Set OTel attributes for Phoenix (OpenInference convention) ---
        if session_id:
            span.set_attribute("session.id", session_id)
        if user_id:
            span.set_attribute("user.id", user_id)
        span.set_attribute("openinference.span.kind", "CHAIN")

        # --- Get trace_id from OTel context ---
        trace_id = get_current_trace_id()

        with LatencyTracker() as timer:
            if decision.route == RouteType.RAG:
                # RAG path — use pre-fetched documents from orchestrator
                docs = decision.documents
                retrieval_count = len(docs)
                logger.debug("ask_retrieval | docs_returned=%d", retrieval_count)

                context = "\n\n".join(doc.page_content for doc in docs)
                source_docs = [doc.page_content[:200] for doc in docs]

                # Invoke without StrOutputParser so we can read usage_metadata
                llm_chain = rag_prompt | get_llm()
                llm_msg = await llm_chain.ainvoke(
                    {"context": context, "input": question},
                )
                answer = llm_msg.content
            else:
                # General path — plain LLM chat via LCEL pipe
                logger.info("ask_general | reason=%s", decision.reason)
                llm_chain = chat_prompt | get_llm()
                llm_msg = await llm_chain.ainvoke({"input": question})
                answer = llm_msg.content
                source_docs = []
                retrieval_count = 0
                context = ""

        # --- Token counts — real values from LLM response -----------------
        usage = getattr(llm_msg, "usage_metadata", None) or {}
        input_tokens = usage.get("input_tokens") or (len(question.split()) + retrieval_count * 200)
        output_tokens = usage.get("output_tokens") or len(answer.split())

        metrics = build_metrics(
            latency_ms=timer.elapsed_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            retrieval_docs=retrieval_count,
            max_relevance=decision.max_relevance,
        )

        # --- Set output attributes on span ---------------------------------
        span.set_attribute("langfuse.trace.output", answer)
        span.set_attribute("langfuse.trace.metadata.latency_ms", str(round(timer.elapsed_ms)))
        span.set_attribute("langfuse.trace.metadata.retrieval_docs", str(retrieval_count))
        if decision.doc_scores:
            span.set_attribute(
                "langfuse.trace.metadata.doc_scores",
                ",".join(str(s) for s in decision.doc_scores),
            )

        logger.info(
            "ask_complete | mode=%s latency=%.0fms tokens_in=%d tokens_out=%d "
            "efficiency=%.3f docs=%d answer_len=%d trace_id=%s",
            mode,
            metrics.latency_ms,
            metrics.input_tokens,
            metrics.output_tokens,
            metrics.token_efficiency,
            metrics.retrieval_docs,
            len(answer),
            trace_id,
        )

    # --- Trace URLs (after span closes) ------------------------------------
    trace_url = get_trace_url(trace_id)
    phoenix_url = get_phoenix_url()

    if trace_url:
        logger.debug("trace_url | langfuse=%s", trace_url)
    if phoenix_url:
        logger.debug("trace_url | phoenix=%s", phoenix_url)

    return {
        "answer": answer,
        "source_documents": source_docs,
        "context": context,
        "doc_scores": decision.doc_scores,
        "route_type": mode,
        "metrics": metrics.to_dict(),
        "trace_url": trace_url,
        "phoenix_url": phoenix_url,
        "trace_id": trace_id,
    }
