"""Tests for error handlers and structured responses."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import AppError, register_error_handlers


def test_structured_app_error():
    """Verify AppError produces standard structured JSON error envelope."""
    test_app = FastAPI()
    register_error_handlers(test_app)

    @test_app.get("/trigger-error")
    def trigger():
        raise AppError(
            message="Test operation failed",
            code="TEST_ERROR",
            status_code=400,
            details=[{"item": "field1", "issue": "bad"}],
        )

    client = TestClient(test_app)
    response = client.get("/trigger-error")
    assert response.status_code == 400

    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "TEST_ERROR"
    assert body["error"]["message"] == "Test operation failed"
    assert len(body["error"]["details"]) == 1


def test_validation_error_structure():
    """Verify Pydantic request validation error returns 422 with structured details."""
    test_app = FastAPI()
    register_error_handlers(test_app)

    @test_app.get("/items/{item_id}")
    def get_item(item_id: int):
        return {"id": item_id}

    client = TestClient(test_app)
    response = client.get("/items/not-an-integer")
    assert response.status_code == 422

    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert len(body["error"]["details"]) > 0
