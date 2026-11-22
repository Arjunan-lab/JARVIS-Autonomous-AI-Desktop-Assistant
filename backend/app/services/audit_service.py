"""Immutable audit logging service for tracking all assistant tool actions and outcomes."""

import json
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent


class AuditService:
    """Service managing write-only append and query operations on the audit log."""

    @staticmethod
    def log_event(
        db: Session,
        action_type: str,
        outcome: str,
        action_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Create and persist an immutable audit trail entry."""
        details_str = json.dumps(details or {})
        event = AuditEvent(
            action_id=action_id,
            action_type=action_type,
            outcome=outcome,
            details_json=details_str,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def list_events(
        db: Session,
        limit: int = 50,
        outcome: str | None = None,
        action_type: str | None = None,
    ) -> list[AuditEvent]:
        """Query audit log entries ordered chronologically descending."""
        stmt: Select[tuple[AuditEvent]] = select(AuditEvent).order_by(AuditEvent.timestamp.desc())

        if outcome:
            stmt = stmt.where(AuditEvent.outcome == outcome)
        if action_type:
            stmt = stmt.where(AuditEvent.action_type == action_type)

        stmt = stmt.limit(limit)
        return list(db.scalars(stmt).all())
