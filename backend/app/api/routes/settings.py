"""Application settings and API budget safeguards API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.budget import (
    BudgetStatusResponse,
    RecordUsagePayload,
    SettingsResponse,
    UpdateSettingsPayload,
)
from app.services.budget_service import BudgetService

router = APIRouter(tags=["settings"])


def get_current_settings(request: Request) -> Settings:
    """Dependency providing current application settings."""
    return getattr(request.app.state, "settings", None) or get_settings()


@router.get("/api/budget", response_model=BudgetStatusResponse, summary="Get current day API budget and usage status")
def get_budget_status(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> BudgetStatusResponse:
    """Query current daily API budget limits, estimated spend, and session counts."""
    return BudgetService.get_budget_status(db, settings)


@router.post("/api/budget/record-usage", summary="Record session duration and usage estimates")
def record_session_usage(
    payload: RecordUsagePayload,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    """Record completed voice session duration and calculate estimated audio costs."""
    return BudgetService.record_session_end(
        db=db,
        duration_seconds=payload.duration_seconds,
        estimated_cost=payload.estimated_cost,
    )


@router.post("/api/budget/reset", summary="Reset daily usage counter")
def reset_daily_budget(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    """Reset the daily budget usage counter."""
    return BudgetService.reset_daily_budget(db)


@router.get("/api/settings", response_model=SettingsResponse, summary="Get application configuration")
def get_settings_summary(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> SettingsResponse:
    """Retrieve application settings, active model, allowed folders, and budget safeguards."""
    effective_limit = BudgetService.get_effective_limit(db, settings)
    raw_dirs = [d.strip() for d in settings.jarvis_allowed_dirs.split(",") if d.strip()]

    return SettingsResponse(
        app_name=settings.app_name,
        app_env=settings.app_env,
        ai_provider=settings.ai_provider,
        openai_model=settings.openai_realtime_model,
        openai_voice=settings.openai_realtime_voice,
        gemini_model=settings.gemini_model,
        gemini_voice=settings.gemini_voice,
        has_api_key=settings.has_valid_api_key(),
        allowed_dirs=raw_dirs,
        max_daily_budget_usd=effective_limit,
    )


@router.patch("/api/settings", response_model=SettingsResponse, summary="Update application settings")
def update_settings(
    payload: UpdateSettingsPayload,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> SettingsResponse:
    """Update user-configurable budget limits and preferences."""
    if payload.max_daily_budget_usd is not None:
        try:
            BudgetService.set_custom_limit(db, payload.max_daily_budget_usd)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            ) from e

    return get_settings_summary(db=db, settings=settings)
