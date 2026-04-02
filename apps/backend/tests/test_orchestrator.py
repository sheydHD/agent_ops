"""Tests for the orchestrator module.

Uses unittest.mock to avoid importing ChromaDB (requires SQLite >= 3.35.0).
"""

import sys
from unittest.mock import MagicMock

# Mock out rag_service before orchestrator imports it
_mock_rag = MagicMock()
sys.modules.setdefault("src.services.rag_service", _mock_rag)

from src.agents.orchestrator import RouteType, RouteDecision


class TestRouteType:
    def test_rag_value(self):
        assert RouteType.RAG == "rag"

    def test_general_value(self):
        assert RouteType.GENERAL == "general"


class TestRouteDecision:
    def test_default_decision(self):
        decision = RouteDecision(route=RouteType.GENERAL)
        assert decision.route == RouteType.GENERAL
        assert decision.documents == []
        assert decision.max_relevance == 0.0
        assert decision.reason == ""

    def test_rag_decision_with_docs(self):
        from langchain_core.documents import Document

        docs = [Document(page_content="test content")]
        decision = RouteDecision(
            route=RouteType.RAG,
            documents=docs,
            max_relevance=0.85,
            reason="found_1_relevant_docs",
        )
        assert decision.route == RouteType.RAG
        assert len(decision.documents) == 1
        assert decision.max_relevance == 0.85
