"""Query Orchestrator — semantic routing for incoming queries.

Determines whether a user question requires domain-specific context from the
knowledge base (RAG path) or can be answered by the general-purpose LLM
directly (general path).

Routing strategy:
  1. Perform similarity search against ChromaDB with the incoming query.
  2. If the top-k results exceed a configurable relevance threshold,
     route to RAG with the pre-fetched documents.
  3. Otherwise, route to the general LLM path.

Pre-fetching avoids a redundant retrieval call downstream — the orchestrator
hands off already-scored documents to the RAG chain.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import StrEnum

from langchain_core.documents import Document

from src.config.settings import settings
from src.services.rag_service import get_collection_count, search_with_relevance

logger = logging.getLogger("agentops.orchestrator")


class RouteType(StrEnum):
    """Query routing destination."""

    RAG = "rag"
    GENERAL = "general"


@dataclass
class RouteDecision:
    """Result of query classification."""

    route: RouteType
    documents: list[Document] = field(default_factory=list)
    max_relevance: float = 0.0
    reason: str = ""


def _classify_query_sync(
    question: str,
    k: int,
    threshold: float,
) -> RouteDecision:
    """Synchronous classification logic — runs in a thread."""
    doc_count = get_collection_count()
    if doc_count == 0:
        logger.info("route_decision | route=general reason=empty_vectorstore")
        return RouteDecision(route=RouteType.GENERAL, reason="empty_vectorstore")

    results = search_with_relevance(question, k=k)

    if not results:
        logger.info("route_decision | route=general reason=no_results")
        return RouteDecision(route=RouteType.GENERAL, reason="no_results")

    max_score = max(score for _, score in results)
    relevant_docs = [doc for doc, score in results if score >= threshold]

    if relevant_docs:
        logger.info(
            "route_decision | route=rag relevant_docs=%d max_score=%.3f threshold=%.3f",
            len(relevant_docs),
            max_score,
            threshold,
        )
        return RouteDecision(
            route=RouteType.RAG,
            documents=relevant_docs,
            max_relevance=max_score,
            reason=f"found_{len(relevant_docs)}_relevant_docs",
        )

    logger.info(
        "route_decision | route=general max_score=%.3f threshold=%.3f",
        max_score,
        threshold,
    )
    return RouteDecision(
        route=RouteType.GENERAL,
        max_relevance=max_score,
        reason=f"below_threshold_{max_score:.3f}<{threshold}",
    )


async def classify_query(
    question: str,
    *,
    k: int = 4,
    relevance_threshold: float | None = None,
) -> RouteDecision:
    """Classify an incoming query and determine the routing path.

    Performs a single similarity search against ChromaDB with relevance scores.
    If any result exceeds the threshold, the query is routed to the RAG
    pipeline and the matching documents are returned to avoid a second lookup.

    Offloads synchronous ChromaDB I/O to a thread so the async event loop
    is never blocked.

    Returns a RouteDecision with the chosen route and pre-fetched documents.
    """
    threshold = relevance_threshold if relevance_threshold is not None else settings.relevance_threshold
    return await asyncio.to_thread(_classify_query_sync, question, k, threshold)
