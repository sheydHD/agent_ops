"""Tests for configuration and settings."""

from src.config.settings import Settings


class TestSettings:
    def test_default_values(self):
        s = Settings(
            _env_file=None,
            langfuse_public_key="",
            langfuse_secret_key="",
        )
        assert s.api_title == "AgentOps Demo API"
        assert s.api_version == "0.2.0"
        assert s.llm_model == "qwen2.5:14b"
        assert s.embedding_model == "nomic-embed-text"
        assert s.llm_temperature == 0.7
        assert s.chunk_size == 1000
        assert s.chunk_overlap == 200
        assert s.relevance_threshold == 0.7

    def test_cors_origins_default(self):
        s = Settings(
            _env_file=None,
            langfuse_public_key="",
            langfuse_secret_key="",
        )
        assert "http://localhost:3501" in s.cors_origins
        assert "http://localhost:4000" in s.cors_origins

    def test_custom_values_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "llama3:8b")
        monkeypatch.setenv("LLM_TEMPERATURE", "0.3")
        monkeypatch.setenv("RELEVANCE_THRESHOLD", "0.5")

        s = Settings(_env_file=None)
        assert s.llm_model == "llama3:8b"
        assert s.llm_temperature == 0.3
        assert s.relevance_threshold == 0.5
