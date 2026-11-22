"""Pydantic schemas for JARVIS personal application access manager."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ManagedAppResponse(BaseModel):
    """Schema representing an application in the authorized access catalog."""

    id: str = Field(..., description="Stable 16-character identifier of the application")
    name: str = Field(..., description="Display name of the application")
    target_path: str = Field(..., description="Executable path or packaged app AUMID")
    target_type: str = Field(..., description="executable or packaged_app")
    category: str = Field(..., description="Application category")
    icon_path: str | None = Field(None, description="Path to icon if extracted")
    is_enabled: bool = Field(..., description="Whether user has enabled execution permissions")
    is_available: bool = Field(..., description="Whether application target exists on disk")
    last_launched_at: datetime | None = Field(None, description="Timestamp of most recent launch")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppPermissionUpdate(BaseModel):
    """Request payload for updating an individual application's permission."""

    is_enabled: bool = Field(..., description="True to allow launches, False to disable")


class AppListResponse(BaseModel):
    """Catalog listing response with status summaries and categories."""

    applications: list[ManagedAppResponse]
    total_count: int
    enabled_count: int
    disabled_count: int
    categories: list[str]


class AppLaunchResponse(BaseModel):
    """Response returned upon launching an authorized application."""

    launched: bool
    app_id: str
    name: str
    mode: str | None = None
    message: str | None = None
