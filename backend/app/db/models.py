"""SQLAlchemy models for JARVIS persistence.

Covers:
- Tasks and reminders
- Approved memories
- User settings
- Consequential action approvals
- Audit logs
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class UTCDateTime(TypeDecorator):
    """DateTime type that ensures UTC timezone awareness in SQLite."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            else:
                value = value.astimezone(UTC)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


def utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(UTC)


def generate_uuid() -> str:
    """Generate a clean UUID string."""
    return uuid.uuid4().hex


class Task(Base):
    """Task model for managing user reminders and to-do items."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)  # pending, completed, cancelled
    priority: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)  # low, medium, high
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_due_date", "due_date"),
    )


class Memory(Base):
    """Persistent structured memories for preferences, project context, and knowledge."""

    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    category: Mapped[str] = mapped_column(
        String(64), default="preference", nullable=False
    )  # preference, project, knowledge
    content: Mapped[str] = mapped_column(Text, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[str | None] = mapped_column(String(64), default="user", nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("idx_memories_category", "category"),
        Index("idx_memories_approved", "approved"),
    )


class UserSetting(Base):
    """Key-value application and assistant settings."""

    __tablename__ = "user_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


class Approval(Base):
    """Pending or resolved authorization for consequential actions."""

    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    action_type: Mapped[str] = mapped_column(String(128), nullable=False)
    arguments_json: Mapped[str] = mapped_column(Text, nullable=False)
    policy: Mapped[str] = mapped_column(String(64), default="explicit_confirmation", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
    )  # pending, approved, rejected, expired
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("idx_approvals_status", "status"),
        Index("idx_approvals_expires_at", "expires_at"),
    )


class AuditEvent(Base):
    """Immutable audit trail for all tool executions, decisions, and outcomes."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    action_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action_type: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)  # success, failure, denied, expired
    details_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_audit_action_type", "action_type"),
        Index("idx_audit_timestamp", "timestamp"),
    )


class ManagedApp(Base):
    """Catalog of discovered Windows applications with explicit per-app permissions."""

    __tablename__ = "managed_apps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_path: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(
        String(32), default="executable", nullable=False
    )  # executable, packaged_app
    category: Mapped[str] = mapped_column(String(64), default="General", nullable=False)
    icon_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # default: disabled / default-deny
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_launched_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("idx_managed_apps_enabled", "is_enabled"),
        Index("idx_managed_apps_name", "name"),
        Index("idx_managed_apps_category", "category"),
    )

