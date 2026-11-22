"""Test fixtures for JARVIS backend test suite."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture(autouse=True)
def clean_test_env(monkeypatch: pytest.MonkeyPatch):
    """Ensure developer keys from local environment do not leak into test runs."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.fixture
def test_settings() -> Settings:
    """Provide isolated test settings."""
    return Settings(
        app_name="JARVIS-TEST",
        app_env="test",
        host="127.0.0.1",
        port=8000,
        openai_api_key="",
        openai_realtime_model="gpt-realtime-mini",
        openai_realtime_voice="marin",
        database_url="sqlite:///:memory:",
        jarvis_max_daily_api_budget_usd=1.00,
        frontend_origin="http://localhost:5173",
        log_level="DEBUG",
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    """Create a FastAPI test client using test configuration."""
    test_app = create_app(settings=test_settings)
    return TestClient(test_app)
