"""Pydantic schemas for approvals, typed tool action execution, and audit logging."""

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ApprovalStatus = Literal["pending", "approved", "rejected", "expired"]
ActionExecutionStatus = Literal["executed", "requires_approval", "denied", "failed"]


class ApprovalResponse(BaseModel):
    """Serialized schema for an action approval record."""

    id: str
    action_type: str
    arguments: dict[str, Any]
    policy: str
    status: ApprovalStatus
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, approval: Any) -> "ApprovalResponse":
        """Convert SQLAlchemy Approval model to ApprovalResponse with parsed JSON arguments."""
        args = {}
        if hasattr(approval, "arguments_json") and approval.arguments_json:
            try:
                args = json.loads(approval.arguments_json)
            except (json.JSONDecodeError, TypeError):
                args = {"raw": approval.arguments_json}

        return cls(
            id=approval.id,
            action_type=approval.action_type,
            arguments=args,
            policy=approval.policy,
            status=approval.status,
            expires_at=approval.expires_at,
            created_at=approval.created_at,
            updated_at=approval.updated_at,
        )


class ApprovalListResponse(BaseModel):
    """Schema for listing approvals with pending counter."""

    approvals: list[ApprovalResponse]
    total: int
    pending_count: int


class ActionRequest(BaseModel):
    """Schema for requesting a tool action from the assistant or user."""

    action_type: str = Field(..., min_length=1, max_length=128, description="Tool name / action identifier")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Typed arguments for the action")


class ActionExecutionResponse(BaseModel):
    """Response returned upon submitting an action request."""

    action_id: str | None = None
    action_type: str
    status: ActionExecutionStatus
    result: Any | None = None
    approval_id: str | None = None
    message: str | None = None


class AuditEventResponse(BaseModel):
    """Serialized schema for an immutable audit event."""

    id: str
    action_id: str | None
    action_type: str
    outcome: str
    details: dict[str, Any]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, event: Any) -> "AuditEventResponse":
        """Convert SQLAlchemy AuditEvent model to AuditEventResponse with parsed JSON details."""
        details = {}
        if hasattr(event, "details_json") and event.details_json:
            try:
                details = json.loads(event.details_json)
            except (json.JSONDecodeError, TypeError):
                details = {"raw": event.details_json}

        return cls(
            id=event.id,
            action_id=event.action_id,
            action_type=event.action_type,
            outcome=event.outcome,
            details=details,
            timestamp=event.timestamp,
        )


class AuditListResponse(BaseModel):
    """List of audit events."""

    events: list[AuditEventResponse]
    total: int
