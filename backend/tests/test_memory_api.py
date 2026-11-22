"""Integration tests for Memory API endpoints, structured persistence, and document retrieval."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.session import Base, get_db
from app.main import create_app


@pytest.fixture
def test_setup(tmp_path: Path):
    """Create test client with isolated in-memory SQLite database and test document folder."""
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

    # Create dummy local documents for search testing
    docs_dir = tmp_path / "approved_docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "flight_manual.md").write_text(
        "# Flight Telemetry Manual\nLine 2: Navigation calibrate arc reactor.\nLine 3: Standby mode.",
        encoding="utf-8",
    )
    (docs_dir / "protocols.json").write_text(
        '{\n  "protocol": "Mark 85",\n  "status": "quantum lock engaged"\n}',
        encoding="utf-8",
    )

    settings = Settings(
        app_env="test",
        jarvis_allowed_dirs=str(docs_dir),
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, docs_dir

    app.dependency_overrides.clear()


def test_create_memory(test_setup):
    """Verify creating a valid explicit memory returns 201 with persisted fields."""
    client, _ = test_setup
    payload = {
        "category": "preference",
        "content": "Prefers concise, engineering-focused voice answers",
        "approved": True,
        "source": "user",
    }

    response = client.post("/api/memory", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] is not None
    assert (
        data["content"] == "Prefers concise, engineering-focused voice answers"
    )
    assert data["category"] == "preference"
    assert data["approved"] is True
    assert data["source"] == "user"
    assert data["created_at"] is not None


def test_create_memory_validation_rejection(test_setup):
    """Verify empty content and invalid categories are rejected with 422."""
    client, _ = test_setup

    # Whitespace only content
    resp1 = client.post(
        "/api/memory", json={"content": "   ", "category": "preference"}
    )
    assert resp1.status_code == 422

    # Invalid category
    resp2 = client.post(
        "/api/memory",
        json={"content": "Valid text", "category": "invalid_category"},
    )
    assert resp2.status_code == 422


def test_list_and_filter_memories(test_setup):
    """Verify listing memories and filtering by category, approval, and search query."""
    client, _ = test_setup

    client.post(
        "/api/memory",
        json={
            "category": "preference",
            "content": "Prefers dark mode UI",
            "approved": True,
        },
    )
    client.post(
        "/api/memory",
        json={
            "category": "project",
            "content": "JARVIS assistant architecture design",
            "approved": True,
        },
    )
    client.post(
        "/api/memory",
        json={
            "category": "knowledge",
            "content": "Experimental arc reactor formula",
            "approved": False,
        },
    )

    # List all
    all_resp = client.get("/api/memory")
    assert all_resp.status_code == 200
    all_data = all_resp.json()
    assert all_data["total"] == 3
    assert all_data["preference_count"] == 1
    assert all_data["project_count"] == 1
    assert all_data["knowledge_count"] == 1

    # Filter by category
    proj_resp = client.get("/api/memory?category=project")
    assert proj_resp.status_code == 200
    assert len(proj_resp.json()["memories"]) == 1
    assert proj_resp.json()["memories"][0]["category"] == "project"

    # Filter approved only
    app_resp = client.get("/api/memory?approved_only=true")
    assert app_resp.status_code == 200
    assert len(app_resp.json()["memories"]) == 2

    # Keyword search
    search_resp = client.get("/api/memory?search=reactor")
    assert search_resp.status_code == 200
    assert len(search_resp.json()["memories"]) == 1
    assert "arc reactor" in search_resp.json()["memories"][0]["content"]


def test_get_and_update_memory(test_setup):
    """Verify getting single memory and updating content, category, or approval status."""
    client, _ = test_setup

    create_resp = client.post(
        "/api/memory",
        json={
            "category": "project",
            "content": "Initial notes on propulsion system",
            "approved": True,
        },
    )
    memory_id = create_resp.json()["id"]

    # Get by ID
    get_resp = client.get(f"/api/memory/{memory_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == memory_id

    # Update content and category
    patch_resp = client.patch(
        f"/api/memory/{memory_id}",
        json={
            "content": "Refined notes on repulsor propulsion system",
            "approved": False,
        },
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert (
        updated["content"] == "Refined notes on repulsor propulsion system"
    )
    assert updated["approved"] is False


def test_memory_not_found(test_setup):
    """Verify 404 responses for non-existent memory operations."""
    client, _ = test_setup

    assert client.get("/api/memory/fake-id-123").status_code == 404
    assert (
        client.patch(
            "/api/memory/fake-id-123", json={"content": "New text"}
        ).status_code
        == 404
    )
    assert client.delete("/api/memory/fake-id-123").status_code == 404


def test_delete_memory(test_setup):
    """Verify deleting a memory removes it from database."""
    client, _ = test_setup

    create_resp = client.post(
        "/api/memory",
        json={"category": "preference", "content": "Temporary preference"},
    )
    memory_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/memory/{memory_id}")
    assert del_resp.status_code == 200
    assert del_resp.json() == {"deleted": True, "id": memory_id}

    # Verify subsequent lookup is 404
    assert client.get(f"/api/memory/{memory_id}").status_code == 404


def test_search_memories_and_documents(test_setup):
    """Verify unified search querying both database memories and allowed document files."""
    client, _ = test_setup

    client.post(
        "/api/memory",
        json={
            "category": "project",
            "content": "Flight control telemetry recalibration",
            "approved": True,
        },
    )

    # Search for telemetry - should match memory AND local document
    search_resp = client.get("/api/memory/search?q=telemetry")
    assert search_resp.status_code == 200
    data = search_resp.json()
    assert data["query"] == "telemetry"

    # Verify memory match
    assert len(data["memories"]) == 1
    assert "telemetry" in data["memories"][0]["content"].lower()

    # Verify document match
    assert len(data["documents"]) >= 1
    doc_match = data["documents"][0]
    assert doc_match["file_name"] == "flight_manual.md"
    assert "telemetry manual" in doc_match["snippet"].lower()
    assert doc_match["line_number"] == 1
