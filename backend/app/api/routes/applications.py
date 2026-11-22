"""API routes for JARVIS personal application access manager."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.application import (
    AppLaunchResponse,
    AppListResponse,
    AppPermissionUpdate,
    ManagedAppResponse,
)
from app.services.app_discovery_service import AppDiscoveryService
from app.services.app_manager_service import AppManagerService

router = APIRouter(prefix="/api/apps", tags=["applications"])


def get_current_settings(request: Request) -> Settings:
    """Dependency providing current application settings."""
    return getattr(request.app.state, "settings", None) or get_settings()


@router.get("", response_model=AppListResponse, summary="List discovered applications and permissions")
def list_applications(
    db: Annotated[Session, Depends(get_db)],
    search: str | None = Query(default=None, description="Search applications by name or category"),
    category: str | None = Query(default=None, description="Filter by category (Browsers, Development, etc.)"),
    enabled_only: bool = Query(default=False, description="Filter only enabled applications"),
) -> AppListResponse:
    """Retrieve catalog of applications with filtering and permission summary metrics."""
    apps, total, enabled, disabled, categories = AppManagerService.list_apps(
        db, search=search, category=category, enabled_only=enabled_only
    )
    return AppListResponse(
        applications=[ManagedAppResponse.model_validate(a) for a in apps],
        total_count=total,
        enabled_count=enabled,
        disabled_count=disabled,
        categories=categories,
    )


@router.post("/refresh", response_model=AppListResponse, summary="Refresh application discovery")
def refresh_applications(
    db: Annotated[Session, Depends(get_db)],
) -> AppListResponse:
    """Scan authorized Windows locations for applications and update catalog while preserving permissions."""
    discovery_service = AppDiscoveryService()
    discovered = discovery_service.discover_all()
    AppManagerService.sync_discovery(db, discovered)

    apps, total, enabled, disabled, categories = AppManagerService.list_apps(db)
    return AppListResponse(
        applications=[ManagedAppResponse.model_validate(a) for a in apps],
        total_count=total,
        enabled_count=enabled,
        disabled_count=disabled,
        categories=categories,
    )


@router.patch(
    "/{app_id}/permission",
    response_model=ManagedAppResponse,
    summary="Update application permission toggle",
)
def update_app_permission(
    app_id: str,
    update_in: AppPermissionUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> ManagedAppResponse:
    """Enable or disable launch permission for an individual application."""
    try:
        app = AppManagerService.update_permission(db, app_id, update_in.is_enabled)
        return ManagedAppResponse.model_validate(app)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{app_id}' not found in catalog",
        ) from exc


@router.post(
    "/{app_id}/launch",
    response_model=AppLaunchResponse,
    status_code=status.HTTP_200_OK,
    summary="Launch an authorized application by ID",
)
def launch_application(
    app_id: str,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_current_settings)],
) -> AppLaunchResponse:
    """Launch an application after independent server-side permission and target verification."""
    try:
        result = AppManagerService.launch_app(db, app_id, settings)
        return AppLaunchResponse(
            launched=result.get("launched", True),
            app_id=result.get("app_id", app_id),
            name=result.get("name", "Application"),
            mode=result.get("mode"),
            message="Application launched successfully",
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{app_id}' not found in catalog",
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
