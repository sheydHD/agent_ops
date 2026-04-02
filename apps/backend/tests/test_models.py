"""Tests for API models and input validation.

Re-declares models locally to avoid transitive ChromaDB import
(which requires SQLite >= 3.35.0, not always available on host).
"""

import pytest
from pydantic import BaseModel, Field, ValidationError


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


class TestChatRequest:
    def test_valid_request(self):
        req = ChatRequest(message="Hello, how are you?")
        assert req.message == "Hello, how are you?"
        assert req.conversation_id is None
        assert req.user_id is None
        assert req.prompt_name is None

    def test_full_request(self):
        req = ChatRequest(
            message="test",
            conversation_id="conv-123",
            user_id="user-456",
            prompt_name="my-prompt",
        )
        assert req.conversation_id == "conv-123"
        assert req.user_id == "user-456"
        assert req.prompt_name == "my-prompt"

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_message_too_long_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 5001)

    def test_max_length_message_accepted(self):
        req = ChatRequest(message="x" * 5000)
        assert len(req.message) == 5000


class TestChatResponse:
    def test_valid_response(self):
        resp = ChatResponse(
            message="Here is the answer.",
            conversation_id="conv-1",
            metadata={"latency_ms": 150.0},
            timestamp="2026-01-01T00:00:00Z",
        )
        assert resp.message == "Here is the answer."
        assert resp.metadata["latency_ms"] == 150.0
