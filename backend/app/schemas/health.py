"""Health endpoint schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health status response payload."""

    status: str = Field(default="ok", description="Health status string")
    service: str = Field(default="jarvis", description="Service name")
    version: str = Field(default="0.1.0", description="Service semantic version")
