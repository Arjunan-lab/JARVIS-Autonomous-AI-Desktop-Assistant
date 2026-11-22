"""Integration tests for Daily API Budget Safeguards, Usage Telemetry, and Settings."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.session import Base, get_db
from app.main import create_app
from app.services.budget_service import BudgetService


@pytest.fixture
def test_setup(tmp_path: Path):
    """Create test client with isolated SQLite database."""
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

    settings = Settings(
        app_env="test",
        ai_provider="openai",
        openai_api_key="sk-test-mock-key-for-budget",
        jarvis_max_daily_api_budget_usd=1.00,
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal

    app.dependency_overrides.clear()


def test_get_budget_status_default(test_setup):
    """Verify initial budget status reflects the configured default limit."""
    client, _ = test_setup

    response = client.get("/api/budget")
    assert response.status_code == 200

    data = response.json()
    assert data["limit_usd"] == 1.00
    assert data["spent_usd"] == 0.0
    assert data["remaining_usd"] == 1.00
    assert data["is_budget_exceeded"] is False
    assert data["sessions_today"] == 0


def test_record_session_usage(test_setup):
    """Verify recording session duration and cost updates daily spend and duration."""
    client, _ = test_setup

    payload = {"duration_seconds": 45, "estimated_cost": 0.05}
    response = client.post("/api/budget/record-usage", json=payload)
    assert response.status_code == 200

    # Query status
    status_resp = client.get("/api/budget")
    status_data = status_resp.json()
    assert status_data["spent_usd"] == 0.05
    assert status_data["duration_seconds_today"] == 45
    assert status_data["remaining_usd"] == 0.95
    assert status_data["is_budget_exceeded"] is False


def test_budget_safeguard_blocks_new_voice_session(test_setup):
    """Verify reaching the daily budget threshold blocks new voice session creation with 429."""
    client, TestingSessionLocal = test_setup

    # Manually set spent_usd to exceed $1.00 limit
    db = TestingSessionLocal()
    BudgetService._set_setting(db, BudgetService.KEY_SPENT, "1.05")
    db.close()

    # Verify status is exceeded
    status_resp = client.get("/api/budget")
    assert status_resp.json()["is_budget_exceeded"] is True

    # Attempt to create voice session -> must be blocked
    session_resp = client.post("/api/voice/session")
    assert session_resp.status_code == 429

    err_data = session_resp.json()
    err_msg = err_data.get("error", {}).get("message", "").lower()
    assert "budget safeguard" in err_msg
    assert "blocked" in err_msg


def test_reset_daily_budget(test_setup, monkeypatch):
    """Verify resetting the daily budget clears spent counter and re-enables session creation."""
    client, TestingSessionLocal = test_setup

    # Exceed budget
    db = TestingSessionLocal()
    BudgetService._set_setting(db, BudgetService.KEY_SPENT, "2.50")
    db.close()

    assert client.get("/api/budget").json()["is_budget_exceeded"] is True

    # Reset budget
    reset_resp = client.post("/api/budget/reset")
    assert reset_resp.status_code == 200

    # Verify cleared
    status = client.get("/api/budget").json()
    assert status["spent_usd"] == 0.0
    assert status["is_budget_exceeded"] is False

    # Mock OpenAI API call to verify session creation now passes budget gate
    mock_upstream_response = {
        "id": "sess_123",
        "client_secret": {"value": "ek_test_after_reset", "expires_at": 1700000000},
        "model": "gpt-realtime-mini",
        "voice": "marin",
    }

    class MockResponse:
        status_code = 200

        def json(self):
            return mock_upstream_response

    async def mock_post(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    resp = client.post("/api/voice/session")
    assert resp.status_code == 201
    assert resp.json()["client_secret"] == "ek_test_after_reset"


def test_settings_summary_and_update(test_setup):
    """Verify retrieving settings summary and adjusting custom daily budget limit."""
    client, _ = test_setup

    # Get settings
    get_resp = client.get("/api/settings")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["openai_model"] == "gpt-realtime-mini"
    assert data["max_daily_budget_usd"] == 1.00
    assert data["has_api_key"] is True

    # Update daily budget limit to $3.50
    patch_resp = client.patch("/api/settings", json={"max_daily_budget_usd": 3.50})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["max_daily_budget_usd"] == 3.50

    # Verify reflected in /api/budget
    budget_resp = client.get("/api/budget")
    assert budget_resp.json()["limit_usd"] == 3.50
