"""API routes for consequential action approvals, tool execution, and audit trail."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.approval import (
    ActionExecutionResponse,
    ActionRequest,
    ApprovalListResponse,
    ApprovalResponse,
    AuditEventResponse,
    AuditListResponse,
)
from app.services.action_service import ActionService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def get_current_settings(request: Request) -> Settings:
    """Dependency providing current application settings."""
    return getattr(request.app.state, "settings", None) or get_settings()


@router.get("", response_model=ApprovalListResponse, summary="List approval requests")
def list_approvals(
    db: Annotated[Session, Depends(get_db)],
    approval_status: str | None = Query(
        default=None, alias="status", description="Filter by status (pending, approved, rejected, expired)"
    ),
) -> ApprovalListResponse:
    """Retrieve pending or past action approvals with summary counts."""
    approvals, total, pending = ActionService.list_approvals(db, status=approval_status)
    return ApprovalListResponse(
        approvals=[ApprovalResponse.from_model(a) for a in approvals],
        total=total,
        pending_count=pending,
    )


@router.post(
    "/request",
    response_model=ActionExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a tool action execution",
)
def request_action(
    action_in: ActionRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> ActionExecutionResponse:
    """Submit a tool action for policy evaluation, auto-execution, or approval queuing."""
    try:
        return ActionService.request_action(
            db=db,
            action_type=action_in.action_type,
            arguments=action_in.arguments,
            settings=settings,
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution error: {e}",
        ) from e


@router.post(
    "/{approval_id}/approve",
    response_model=dict[str, object],
    summary="Approve and execute a pending action",
)
def approve_action(
    approval_id: str,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> dict[str, object]:
    """Approve a pending action and immediately execute its validated handler."""
    try:
        return ActionService.approve_action(db=db, approval_id=approval_id, settings=settings)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed upon approval: {e}",
        ) from e


@router.post(
    "/{approval_id}/reject",
    response_model=dict[str, object],
    summary="Reject a pending action",
)
def reject_action(
    approval_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    """Reject a pending action request."""
    try:
        return ActionService.reject_action(db=db, approval_id=approval_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/audit", response_model=AuditListResponse, summary="Query audit trail")
def list_audit_events(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200, description="Max events to return"),
    outcome: str | None = Query(default=None, description="Filter by outcome"),
    action_type: str | None = Query(default=None, description="Filter by action type"),
) -> AuditListResponse:
    """Retrieve immutable audit events for complete transparency and compliance."""
    events = AuditService.list_events(
        db=db, limit=limit, outcome=outcome, action_type=action_type
    )
    return AuditListResponse(
        events=[AuditEventResponse.from_model(e) for e in events],
        total=len(events),
    )
