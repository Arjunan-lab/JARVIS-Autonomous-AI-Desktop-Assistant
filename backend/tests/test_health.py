"""Integration tests for the health check endpoint."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Verify GET /api/health returns 200 with ok status and jarvis service name."""
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "jarvis"
    assert "version" in data
