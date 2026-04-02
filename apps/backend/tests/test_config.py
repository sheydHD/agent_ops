"""Smoke tests for configuration loading."""

from src.config.settings import Settings


def test_settings_defaults() -> None:
    """Settings can be instantiated with all defaults."""
    s = Settings()
    assert s.api_title == "AgentOps Demo API"
    assert s.llm_model == "qwen2.5:14b"
    assert s.embedding_model == "nomic-embed-text"
    assert s.chunk_size > 0
    assert s.chunk_overlap >= 0
    assert s.relevance_threshold > 0
