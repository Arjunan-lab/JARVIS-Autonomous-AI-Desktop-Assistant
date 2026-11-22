"""Integration tests for Task API endpoints and reminder queries."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.session import Base, get_db
from app.main import create_app


@pytest.fixture
def client():
    """Create test client with isolated in-memory SQLite database."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    settings = Settings(app_env="test")
    app = create_app(settings=settings)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_create_task(client: TestClient):
    """Verify creating a valid task returns 201 with default pending status."""
    due = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    payload = {
        "title": "Configure firewall rules",
        "description": "Ensure only port 8000 is open locally",
        "priority": "high",
        "due_date": due,
    }

    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] is not None
    assert data["title"] == "Configure firewall rules"
    assert data["priority"] == "high"
    assert data["status"] == "pending"


def test_create_task_validation_rejection(client: TestClient):
    """Verify empty title is rejected with 422."""
    response = client.post("/api/tasks", json={"title": ""})
    assert response.status_code == 422

    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_list_and_filter_tasks(client: TestClient):
    """Verify task listing and filtering by status and priority."""
    client.post("/api/tasks", json={"title": "Task A", "priority": "low"})
    client.post("/api/tasks", json={"title": "Task B", "priority": "high"})
    t3 = client.post("/api/tasks", json={"title": "Task C", "priority": "medium"}).json()

    # Mark Task C completed
    client.patch(f"/api/tasks/{t3['id']}", json={"status": "completed"})

    # List all
    res = client.get("/api/tasks")
    assert res.status_code == 200
    all_data = res.json()
    assert all_data["total"] == 3
    assert all_data["pending_count"] == 2
    assert all_data["completed_count"] == 1

    # Filter pending
    pending_res = client.get("/api/tasks?status=pending")
    assert len(pending_res.json()["tasks"]) == 2

    # Filter high priority
    high_res = client.get("/api/tasks?priority=high")
    assert len(high_res.json()["tasks"]) == 1
    assert high_res.json()["tasks"][0]["title"] == "Task B"


def test_get_and_update_task(client: TestClient):
    """Verify fetching and updating task fields."""
    created = client.post("/api/tasks", json={"title": "Original Title"}).json()
    task_id = created["id"]

    # Update title and priority
    new_due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    patch_res = client.patch(
        f"/api/tasks/{task_id}",
        json={"title": "Updated Title", "priority": "high", "due_date": new_due},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["title"] == "Updated Title"
    assert updated["priority"] == "high"


def test_task_not_found(client: TestClient):
    """Verify 404 response when querying non-existent task."""
    res = client.get("/api/tasks/non-existent-id")
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "NOT_FOUND"


def test_delete_task(client: TestClient):
    """Verify task deletion and subsequent 404."""
    created = client.post("/api/tasks", json={"title": "To be deleted"}).json()
    task_id = created["id"]

    del_res = client.delete(f"/api/tasks/{task_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/api/tasks/{task_id}")
    assert get_res.status_code == 404


def test_due_reminders_endpoint(client: TestClient):
    """Verify reminders endpoint returns overdue and due-today pending tasks."""
    # 1. Overdue task
    overdue_time = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    client.post("/api/tasks", json={"title": "Overdue task", "due_date": overdue_time})

    # 2. Future task (tomorrow)
    future_time = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    client.post("/api/tasks", json={"title": "Future task", "due_date": future_time})

    # 3. Overdue but completed
    t3 = client.post("/api/tasks", json={"title": "Completed overdue", "due_date": overdue_time}).json()
    client.patch(f"/api/tasks/{t3['id']}", json={"status": "completed"})

    reminders_res = client.get("/api/tasks/reminders")
    assert reminders_res.status_code == 200
    reminders = reminders_res.json()

    assert len(reminders) == 1
    assert reminders[0]["title"] == "Overdue task"
