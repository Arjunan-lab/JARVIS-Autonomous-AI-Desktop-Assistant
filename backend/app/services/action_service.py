"""Action orchestration service enforcing approval policies and execution safeguards."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Approval
from app.schemas.approval import ActionExecutionResponse
from app.services.audit_service import AuditService
from app.tools.policies import ToolPolicy
from app.tools.registry import default_tool_registry


class ActionService:
    """Service governing tool policy evaluation, approval lifecycles, and action execution."""

    @staticmethod
    def request_action(
        db: Session,
        action_type: str,
        arguments: dict[str, Any],
        settings: Settings,
    ) -> ActionExecutionResponse:
        """Process an action request through policy checks and approval gating."""
        tool = default_tool_registry.get(action_type)
        if not tool or tool.policy == ToolPolicy.BLOCKED:
            AuditService.log_event(
                db=db,
                action_type=action_type,
                outcome="denied",
                details={"arguments": arguments, "reason": "Tool not allowlisted or blocked"},
            )
            raise PermissionError(
                f"Action '{action_type}' is blocked or not in the allowlist"
            )

        # Validate arguments schema
        is_valid, err_msg = default_tool_registry.validate_tool_call(action_type, arguments)
        if not is_valid:
            AuditService.log_event(
                db=db,
                action_type=action_type,
                outcome="validation_failed",
                details={"arguments": arguments, "error": err_msg},
            )
            raise ValueError(err_msg or "Invalid tool arguments")

        # Automatic policy: Execute immediately
        if tool.policy == ToolPolicy.AUTOMATIC:
            try:
                result = tool.handler(db, arguments, settings)
                AuditService.log_event(
                    db=db,
                    action_type=action_type,
                    outcome="success",
                    details={"arguments": arguments, "result": result},
                )
                return ActionExecutionResponse(
                    action_type=action_type,
                    status="executed",
                    result=result,
                    message="Action executed successfully under automatic policy",
                )
            except Exception as e:
                AuditService.log_event(
                    db=db,
                    action_type=action_type,
                    outcome="failure",
                    details={"arguments": arguments, "error": str(e)},
                )
                raise

        # Explicit confirmation policy: Queue approval
        now = datetime.now(UTC)
        args_json = json.dumps(arguments, sort_keys=True)

        # Check for duplicate active pending approval
        existing_stmt = select(Approval).where(
            Approval.action_type == action_type,
            Approval.arguments_json == args_json,
            Approval.status == "pending",
            Approval.expires_at > now,
        )
        existing = db.scalars(existing_stmt).first()
        if existing:
            return ActionExecutionResponse(
                action_id=existing.id,
                action_type=action_type,
                status="requires_approval",
                approval_id=existing.id,
                message="Identical action is already pending user approval",
            )

        # Create new Approval
        approval = Approval(
            action_type=action_type,
            arguments_json=args_json,
            policy=tool.policy.value,
            status="pending",
            expires_at=now + timedelta(minutes=5),
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        AuditService.log_event(
            db=db,
            action_id=approval.id,
            action_type=action_type,
            outcome="pending_approval",
            details={"arguments": arguments, "policy": tool.policy.value},
        )

        return ActionExecutionResponse(
            action_id=approval.id,
            action_type=action_type,
            status="requires_approval",
            approval_id=approval.id,
            message="Consequential action queued for explicit user approval",
        )

    @staticmethod
    def get_approval(db: Session, approval_id: str) -> Approval | None:
        """Fetch approval record by ID and evaluate freshness."""
        stmt: Select[tuple[Approval]] = select(Approval).where(Approval.id == approval_id)
        approval = db.scalars(stmt).first()
        if not approval:
            return None

        # Check if expired
        now = datetime.now(UTC)
        if approval.status == "pending" and approval.expires_at <= now:
            approval.status = "expired"
            db.commit()
            db.refresh(approval)

        return approval

    @staticmethod
    def list_approvals(db: Session, status: str | None = None) -> tuple[list[Approval], int, int]:
        """List approvals with lazy expiration checks and return (list, total, pending_count)."""
        now = datetime.now(UTC)

        # Mark expired pending records
        expired_stmt = select(Approval).where(
            Approval.status == "pending",
            Approval.expires_at <= now,
        )
        for expired in db.scalars(expired_stmt).all():
            expired.status = "expired"
        db.commit()

        stmt = select(Approval).order_by(Approval.created_at.desc())
        if status:
            stmt = stmt.where(Approval.status == status)

        approvals = list(db.scalars(stmt).all())

        total = db.scalar(select(func.count(Approval.id))) or 0
        pending = db.scalar(
            select(func.count(Approval.id)).where(Approval.status == "pending")
        ) or 0

        return approvals, total, pending

    @staticmethod
    def approve_action(
        db: Session,
        approval_id: str,
        settings: Settings,
    ) -> dict[str, Any]:
        """Approve a pending action, revalidate policies and execute handler."""
        approval = ActionService.get_approval(db, approval_id)
        if not approval:
            raise ValueError(f"Approval with ID '{approval_id}' not found")

        if approval.status == "expired":
            AuditService.log_event(
                db=db,
                action_id=approval_id,
                action_type=approval.action_type,
                outcome="expired",
                details={"reason": "Attempted to approve expired token"},
            )
            raise ValueError("Approval request has expired")

        if approval.status != "pending":
            raise ValueError(f"Approval is already resolved with status '{approval.status}'")

        tool = default_tool_registry.get(approval.action_type)
        if not tool or tool.policy == ToolPolicy.BLOCKED:
            approval.status = "rejected"
            db.commit()
            AuditService.log_event(
                db=db,
                action_id=approval_id,
                action_type=approval.action_type,
                outcome="denied",
                details={"reason": "Tool policy was revoked or blocked"},
            )
            raise PermissionError("Tool is no longer authorized for execution")

        try:
            args = json.loads(approval.arguments_json)
        except json.JSONDecodeError as e:
            raise ValueError("Corrupted approval arguments") from e

        # Re-validate tool arguments immediately before execution
        is_valid, err_msg = default_tool_registry.validate_tool_call(approval.action_type, args)
        if not is_valid:
            raise ValueError(err_msg or "Invalid tool arguments on revalidation")

        # Execute handler
        try:
            result = tool.handler(db, args, settings)
            approval.status = "approved"
            db.commit()

            AuditService.log_event(
                db=db,
                action_id=approval_id,
                action_type=approval.action_type,
                outcome="success",
                details={"arguments": args, "result": result},
            )
            return {
                "approval_id": approval_id,
                "action_type": approval.action_type,
                "status": "executed",
                "result": result,
            }
        except Exception as e:
            AuditService.log_event(
                db=db,
                action_id=approval_id,
                action_type=approval.action_type,
                outcome="failure",
                details={"arguments": args, "error": str(e)},
            )
            raise

    @staticmethod
    def reject_action(db: Session, approval_id: str) -> dict[str, Any]:
        """Reject a pending action request."""
        approval = ActionService.get_approval(db, approval_id)
        if not approval:
            raise ValueError(f"Approval with ID '{approval_id}' not found")

        if approval.status != "pending":
            raise ValueError(f"Approval is already resolved with status '{approval.status}'")

        approval.status = "rejected"
        db.commit()

        AuditService.log_event(
            db=db,
            action_id=approval_id,
            action_type=approval.action_type,
            outcome="rejected",
            details={"action_type": approval.action_type},
        )
        return {
            "approval_id": approval_id,
            "status": "rejected",
        }
