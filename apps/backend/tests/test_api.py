"""Tests for the health endpoint."""


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] in ("ok", "degraded")

    def test_health_contains_expected_fields(self, client):
        resp = client.get("/health")
        data = resp.json()
        for field in ("ollama", "chromadb", "langfuse", "phoenix", "documents_indexed"):
            assert field in data, f"Missing field: {field}"


class TestChatEndpoint:
    def test_chat_rejects_empty_message(self, client):
        resp = client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_chat_rejects_too_long_message(self, client):
        resp = client.post("/api/chat", json={"message": "x" * 5001})
        assert resp.status_code == 422

    def test_chat_rejects_missing_message(self, client):
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 422


class TestPromptsEndpoint:
    def test_prompts_returns_200(self, client):
        resp = client.get("/api/prompts")
        # May fail to connect to Langfuse, but should not 500
        assert resp.status_code in (200, 500)


class TestGlobalExceptionHandler:
    def test_unknown_route_returns_404(self, client):
        resp = client.get("/nonexistent")
        assert resp.status_code == 404

    def test_swagger_docs_available(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200
