"""Tests for the request logging & security middleware."""

import uuid


class TestRequestLoggingMiddleware:
    def test_request_id_generated(self, client):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers
        rid = resp.headers["x-request-id"]
        assert len(rid) > 0

    def test_request_id_passthrough(self, client):
        custom_id = uuid.uuid4().hex[:16]
        resp = client.get("/health", headers={"x-request-id": custom_id})
        assert resp.headers["x-request-id"] == custom_id

    def test_malicious_request_id_rejected(self, client):
        """Request ID with newlines or special chars should be replaced."""
        resp = client.get("/health", headers={"x-request-id": "evil\ninjection"})
        rid = resp.headers["x-request-id"]
        # Should NOT contain the injected value
        assert "\n" not in rid
        assert "evil" not in rid

    def test_long_request_id_truncated(self, client):
        long_id = "a" * 200
        resp = client.get("/health", headers={"x-request-id": long_id})
        rid = resp.headers["x-request-id"]
        assert len(rid) <= 64


class TestSecurityHeadersMiddleware:
    def test_security_headers_present(self, client):
        resp = client.get("/health")
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in resp.headers["permissions-policy"]
        assert resp.headers["x-permitted-cross-domain-policies"] == "none"
