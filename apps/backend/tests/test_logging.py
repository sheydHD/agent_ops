"""Tests for logging configuration."""

import logging

from src.config.logging_config import setup_logging, request_id_ctx, conversation_id_ctx


class TestSetupLogging:
    def test_text_format(self):
        setup_logging(level="DEBUG", log_format="text")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1

    def test_json_format(self):
        setup_logging(level="INFO", log_format="json")
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_noisy_loggers_suppressed(self):
        setup_logging(level="DEBUG", log_format="text")
        assert logging.getLogger("chromadb").level == logging.WARNING
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("langfuse").level == logging.WARNING


class TestContextVars:
    def test_request_id_default(self):
        assert request_id_ctx.get("-") == "-"

    def test_request_id_set_reset(self):
        token = request_id_ctx.set("test-123")
        assert request_id_ctx.get() == "test-123"
        request_id_ctx.reset(token)
        assert request_id_ctx.get("-") == "-"

    def test_conversation_id_default(self):
        assert conversation_id_ctx.get("-") == "-"
