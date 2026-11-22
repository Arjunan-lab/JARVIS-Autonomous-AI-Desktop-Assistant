"""API routes for natural language command interpretation and desktop automation workflows."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services.automation.automation_models import OperationExecutionResult
from app.services.automation.automation_service import AutomationService

router = APIRouter(prefix="/api/commands", tags=["commands"])


class CommandExecuteRequest(BaseModel):
    """Payload for executing a natural language command."""

    command: str = Field(..., description="User instruction to execute", min_length=1)


class CancelOperationResponse(BaseModel):
    """Result of operation cancellation."""

    operation_id: str
    cancelled: bool
    message: str


def get_current_settings(request: Request) -> Settings:
    """Dependency providing current application settings."""
    return getattr(request.app.state, "settings", None) or get_settings()


@router.post(
    "/execute",
    response_model=OperationExecutionResult,
    status_code=status.HTTP_200_OK,
    summary="Interpret command and execute multi-step automation workflow",
)
def execute_command(
    req: CommandExecuteRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> OperationExecutionResult:
    """Parse user command into an automation plan, verify permissions, execute steps, and verify outcomes."""
    service = AutomationService(settings=settings)
    try:
        return service.execute_command(db=db, user_prompt=req.command)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/operations/{operation_id}/cancel",
    response_model=CancelOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel an active automation operation",
)
def cancel_operation(
    operation_id: str,
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> CancelOperationResponse:
    """Signal cancellation for a running workflow."""
    service = AutomationService(settings=settings)
    success = service.cancel_operation(operation_id)
    return CancelOperationResponse(
        operation_id=operation_id,
        cancelled=success,
        message="Cancellation signal recorded" if success else "Operation not found or already finished",
    )
