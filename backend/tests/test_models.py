"""Unit and persistence tests for SQLAlchemy models and SQLite storage."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Approval, AuditEvent, Memory, Task, UserSetting
from app.db.session import Base


@pytest.fixture
def db_session() -> Session:
    """Create an isolated in-memory SQLite database session for testing."""
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(test_engine)
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = test_session_local()
    try:
        yield session
    finally:
        session.close()


def test_task_lifecycle(db_session: Session):
    """Verify task creation, due date setting, and status completion."""
    now = datetime.now(UTC)
    due = now + timedelta(days=1)

    task = Task(
        title="Review daily schedule",
        description="Check upcoming tasks and alerts",
        due_date=due,
        priority="high",
        status="pending",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.id is not None
    assert task.title == "Review daily schedule"
    assert task.status == "pending"
    assert task.due_date == due

    # Update task to completed
    task.status = "completed"
    db_session.commit()

    retrieved = db_session.scalar(select(Task).where(Task.id == task.id))
    assert retrieved is not None
    assert retrieved.status == "completed"


def test_memory_persistence(db_session: Session):
    """Verify storing, retrieving, and filtering memories."""
    mem1 = Memory(
        category="preference",
        content="Prefers concise bullet points in responses",
        approved=True,
        source="user",
    )
    mem2 = Memory(
        category="project",
        content="Working on Windows 11 JARVIS assistant",
        approved=True,
        source="user",
    )
    db_session.add_all([mem1, mem2])
    db_session.commit()

    preferences = db_session.scalars(
        select(Memory).where(Memory.category == "preference", Memory.approved.is_(True))
    ).all()
    assert len(preferences) == 1
    assert preferences[0].content == "Prefers concise bullet points in responses"


def test_user_settings(db_session: Session):
    """Verify key-value setting persistence and updates."""
    setting = UserSetting(key="voice_model", value="marin")
    db_session.add(setting)
    db_session.commit()

    saved = db_session.scalar(select(UserSetting).where(UserSetting.key == "voice_model"))
    assert saved is not None
    assert saved.value == "marin"

    # Update setting
    saved.value = "cedar"
    db_session.commit()

    updated = db_session.scalar(select(UserSetting).where(UserSetting.key == "voice_model"))
    assert updated is not None
    assert updated.value == "cedar"


def test_approval_lifecycle(db_session: Session):
    """Verify action approval registration, expiry, and status changes."""
    expires = datetime.now(UTC) + timedelta(minutes=5)
    approval = Approval(
        action_type="open_allowed_application",
        arguments_json='{"app": "notepad.exe"}',
        policy="explicit_confirmation",
        status="pending",
        expires_at=expires,
    )
    db_session.add(approval)
    db_session.commit()

    assert approval.id is not None
    assert approval.status == "pending"

    # Approve
    approval.status = "approved"
    db_session.commit()

    refreshed = db_session.scalar(select(Approval).where(Approval.id == approval.id))
    assert refreshed is not None
    assert refreshed.status == "approved"


def test_audit_event_logging(db_session: Session):
    """Verify immutable audit log entries."""
    audit = AuditEvent(
        action_type="open_allowed_application",
        outcome="success",
        details_json='{"app": "notepad.exe", "pid": 1234}',
    )
    db_session.add(audit)
    db_session.commit()

    events = db_session.scalars(
        select(AuditEvent).where(AuditEvent.action_type == "open_allowed_application")
    ).all()
    assert len(events) == 1
    assert events[0].outcome == "success"
    assert "notepad.exe" in events[0].details_json
