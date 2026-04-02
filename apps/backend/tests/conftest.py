"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    """Create a test client with telemetry and external services disabled."""
    # Disable Phoenix to avoid port conflicts in tests
    monkeypatch.setenv("PHOENIX_ENABLED", "false")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    # Reimport settings to pick up patched env
    from src.config.settings import Settings

    test_settings = Settings()
    monkeypatch.setattr("src.config.settings.settings", test_settings)

    from main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
