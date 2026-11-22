"""Tests for voice session creation and OpenAI Realtime credentials handling."""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.session import Base, get_db
from app.main import create_app


@pytest.fixture
def test_setup():
    """Create isolated in-memory SQLite database for voice tests."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    return override_get_db


def test_voice_session_without_api_key(test_setup):
    """Verify endpoint rejects requests cleanly when OPENAI_API_KEY is not configured."""
    settings = Settings(ai_provider="openai", openai_api_key="", app_env="test")
    app = create_app(settings=settings)
    app.dependency_overrides[get_db] = test_setup
    client = TestClient(app)

    response = client.post("/api/voice/session", json={})
    assert response.status_code == 500

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "CONFIG_ERROR"
    assert "OPENAI_API_KEY" in data["error"]["message"]


def test_voice_session_success_mocked(monkeypatch, test_setup):
    """Verify endpoint returns ephemeral credentials and excludes the permanent API key."""
    secret_permanent_key = "sk-live-permanent-secret-key-1234567890"
    settings = Settings(
        ai_provider="openai",
        openai_api_key=secret_permanent_key,
        openai_realtime_model="gpt-realtime-mini",
        openai_realtime_voice="marin",
        app_env="test",
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_db] = test_setup
    client = TestClient(app)

    mock_openai_payload = {
        "id": "sess_test_12345",
        "object": "realtime.session",
        "model": "gpt-realtime-mini",
        "voice": "marin",
        "client_secret": {
            "value": "ek_temporary_client_secret_token_99999",
            "expires_at": 1799999999,
        },
    }

    class MockResponse:
        status_code = 200

        def json(self):
            return mock_openai_payload

    async def mock_post(*args, **kwargs):
        # Verify Authorization header contains the permanent key server-side
        headers = kwargs.get("headers", {})
        assert f"Bearer {secret_permanent_key}" in headers.get("Authorization", "")
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    response = client.post(
        "/api/voice/session",
        json={"model": "gpt-realtime-mini", "voice": "marin"},
    )
    assert response.status_code == 201

    data = response.json()
    assert data["client_secret"] == "ek_temporary_client_secret_token_99999"
    assert data["session_id"] == "sess_test_12345"
    assert data["model"] == "gpt-realtime-mini"
    assert data["voice"] == "marin"
    assert data["expires_at"] == 1799999999

    # CRITICAL SECURITY VERIFICATION:
    # Ensure permanent key is NEVER present in the client payload
    assert secret_permanent_key not in response.text


def test_voice_session_upstream_error_handled(monkeypatch, test_setup):
    """Verify graceful handling when OpenAI Realtime API returns an upstream error."""
    settings = Settings(
        ai_provider="openai",
        openai_api_key="sk-test-valid-key-sufficient-length",
        app_env="test",
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_db] = test_setup
    client = TestClient(app)

    class MockErrorResponse:
        status_code = 401

        def json(self):
            return {
                "error": {
                    "message": "Invalid authentication credentials",
                    "type": "auth_error",
                }
            }

    async def mock_post(*args, **kwargs):
        return MockErrorResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    response = client.post("/api/voice/session", json={})
    assert response.status_code == 401

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "REALTIME_SESSION_FAILED"
    assert "Invalid authentication credentials" in data["error"]["message"]


def test_gemini_voice_session_success(test_setup):
    """Verify Gemini voice session returns ws_url and excludes permanent GEMINI_API_KEY."""
    gemini_key = "AIzaSyTestValidLengthKey1234567890ABCDE"
    settings = Settings(
        ai_provider="gemini",
        gemini_api_key=gemini_key,
        gemini_model="gemini-2.0-flash",
        gemini_voice="Puck",
        app_env="test",
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_db] = test_setup
    client = TestClient(app)

    response = client.post("/api/voice/session", json={})
    assert response.status_code == 201

    data = response.json()
    assert data["provider"] == "gemini"
    assert data["ws_url"] == "/api/voice/gemini-live"
    assert data["model"] == "gemini-2.0-flash"
    assert data["voice"] == "Puck"
    assert data["session_id"].startswith("gemini-")

    # CRITICAL: Verify permanent key is NOT in response
    assert gemini_key not in response.text


def test_gemini_voice_session_missing_key(test_setup):
    """Verify clean error when AI_PROVIDER=gemini but GEMINI_API_KEY is not set."""
    settings = Settings(
        ai_provider="gemini",
        gemini_api_key="",
        app_env="test",
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_db] = test_setup
    client = TestClient(app)

    response = client.post("/api/voice/session", json={})
    assert response.status_code == 500

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "CONFIG_ERROR"
    assert "GEMINI_API_KEY" in data["error"]["message"]


def test_voice_session_smart_switch_to_gemini_on_rate_limit(monkeypatch, test_setup):
    """Verify smart failover to Google Gemini Live when OpenAI returns HTTP 429 rate limit."""
    gemini_key = "AIzaSyTestValidLengthKey1234567890ABCDE"
    settings = Settings(
        ai_provider="openai",
        openai_api_key="sk-test-valid-key-sufficient-length",
        gemini_api_key=gemini_key,
        gemini_model="gemini-2.0-flash",
        gemini_voice="Puck",
        app_env="test",
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_db] = test_setup
    client = TestClient(app)

    class Mock429ErrorResponse:
        status_code = 429

        def json(self):
            return {
                "error": {
                    "message": "Rate limit reached for requests. Please slow down.",
                    "type": "requests",
                    "code": "rate_limit_exceeded",
                }
            }

    async def mock_post(*args, **kwargs):
        return Mock429ErrorResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    response = client.post("/api/voice/session", json={})
    assert response.status_code == 201

    data = response.json()
    # Verified: It smart-switched to Gemini!
    assert data["provider"] == "gemini"
    assert data["ws_url"] == "/api/voice/gemini-live"
    assert data["model"] == "gemini-2.0-flash"
    assert data["voice"] == "Puck"
    assert data["switched_to_fallback"] is True
    assert "rate limit" in data["fallback_reason"].lower()


def test_synthesize_speech_endpoint(test_setup):
    """Verify /api/voice/synthesize endpoint returns audio in test environment."""
    settings = Settings(ai_provider="openai", openai_api_key="", app_env="test")
    app = create_app(settings=settings)
    app.dependency_overrides[get_db] = test_setup
    client = TestClient(app)

    response = client.post(
        "/api/voice/synthesize",
        json={
            "text": "Hello boss. Hope you are doing well. How can I help you today?",
            "voice": "en-GB-RyanNeural",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert len(response.content) > 0
