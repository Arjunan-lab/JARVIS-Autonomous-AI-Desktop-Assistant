"""Integration tests for Tool Registry, Action Policies, Approvals Lifecycle, and Audit Trail."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.models import Approval
from app.db.session import Base, get_db
from app.main import create_app


@pytest.fixture
def test_setup(tmp_path: Path):
    """Create test client with isolated SQLite database and dummy allowed folders."""
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

    # Allowed test folder with a sample file
    allowed_dir = tmp_path / "jarvis_sandbox"
    allowed_dir.mkdir(parents=True, exist_ok=True)
    sample_file = allowed_dir / "target_document.txt"
    sample_file.write_text("JARVIS test content", encoding="utf-8")

    settings = Settings(
        app_env="test",
        jarvis_allowed_dirs=str(allowed_dir),
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, allowed_dir, sample_file, TestingSessionLocal

    app.dependency_overrides.clear()


def test_automatic_action_execution(test_setup):
    """Verify safe automatic actions (create_task) execute immediately without approval gating."""
    client, _, _, _ = test_setup

    payload = {
        "action_type": "create_task",
        "arguments": {
            "title": "Calibrate flight sensors",
            "priority": "high",
        },
    }

    response = client.post("/api/approvals/request", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "executed"
    assert data["action_type"] == "create_task"
    assert data["result"]["title"] == "Calibrate flight sensors"
    assert data["result"]["id"] is not None

    # Verify audit event was logged
    audit_resp = client.get("/api/approvals/audit")
    assert audit_resp.status_code == 200
    events = audit_resp.json()["events"]
    assert any(e["action_type"] == "create_task" and e["outcome"] == "success" for e in events)


def test_consequential_action_queues_approval(test_setup):
    """Verify destructive actions (delete_file) require explicit approval and queue a token."""
    client, _, sample_file, _ = test_setup

    payload = {
        "action_type": "delete_file",
        "arguments": {
            "file_path": str(sample_file),
        },
    }

    response = client.post("/api/approvals/request", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "requires_approval"
    assert data["approval_id"] is not None
    approval_id = data["approval_id"]

    # Verify file is not deleted yet!
    assert sample_file.exists()

    # Verify listed in pending approvals
    list_resp = client.get("/api/approvals?status=pending")
    assert list_resp.status_code == 200
    approvals = list_resp.json()["approvals"]
    assert any(a["id"] == approval_id for a in approvals)


def test_approve_and_execute_consequential_action(test_setup):
    """Verify user approval executes the queued action, updates status, and deletes file."""
    client, _, sample_file, _ = test_setup

    # Queue approval
    req_resp = client.post(
        "/api/approvals/request",
        json={"action_type": "delete_file", "arguments": {"file_path": str(sample_file)}},
    )
    approval_id = req_resp.json()["approval_id"]

    # Approve action
    app_resp = client.post(f"/api/approvals/{approval_id}/approve")
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "executed"

    # Verify file is now deleted
    assert not sample_file.exists()

    # Verify subsequent approval returns 400 (already resolved)
    repeat_resp = client.post(f"/api/approvals/{approval_id}/approve")
    assert repeat_resp.status_code == 400


def test_reject_consequential_action(test_setup):
    """Verify user can reject an action, preventing its execution."""
    client, _, sample_file, _ = test_setup

    req_resp = client.post(
        "/api/approvals/request",
        json={"action_type": "delete_file", "arguments": {"file_path": str(sample_file)}},
    )
    approval_id = req_resp.json()["approval_id"]

    # Reject action
    rej_resp = client.post(f"/api/approvals/{approval_id}/reject")
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "rejected"

    # Verify file is preserved
    assert sample_file.exists()

    # Verify cannot approve a rejected action
    try_approve = client.post(f"/api/approvals/{approval_id}/approve")
    assert try_approve.status_code == 400


def test_blocked_action_rejected_with_audit(test_setup):
    """Verify arbitrary or blocked commands are rejected with 403 Forbidden and logged."""
    client, _, _, _ = test_setup

    payload = {
        "action_type": "powershell_raw_exec",
        "arguments": {"command": "Get-Process"},
    }

    response = client.post("/api/approvals/request", json=payload)
    assert response.status_code == 403

    # Check audit log contains denied event
    audit_resp = client.get("/api/approvals/audit")
    events = audit_resp.json()["events"]
    assert any(
        e["action_type"] == "powershell_raw_exec" and e["outcome"] == "denied"
        for e in events
    )


def test_path_traversal_denied(test_setup):
    """Verify path traversal outside allowed directories is rejected with 403."""
    client, _, _, _ = test_setup

    payload = {
        "action_type": "read_allowed_text_file",
        "arguments": {"file_path": "../../../windows/system32/drivers/etc/hosts"},
    }

    response = client.post("/api/approvals/request", json=payload)
    assert response.status_code == 403


def test_expired_approval_rejected(test_setup):
    """Verify expired approval tokens cannot be executed."""
    client, _, sample_file, TestingSessionLocal = test_setup

    # Manually create an expired approval in database
    db = TestingSessionLocal()
    expired_approval = Approval(
        action_type="delete_file",
        arguments_json=json.dumps({"file_path": str(sample_file)}),
        policy="explicit_confirmation",
        status="pending",
        expires_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    db.add(expired_approval)
    db.commit()
    expired_id = expired_approval.id
    db.close()

    # Attempt to approve expired token
    resp = client.post(f"/api/approvals/{expired_id}/approve")
    assert resp.status_code == 400
    err_msg = resp.json().get("error", {}).get("message", "").lower()
    assert "expired" in err_msg
    assert sample_file.exists()
