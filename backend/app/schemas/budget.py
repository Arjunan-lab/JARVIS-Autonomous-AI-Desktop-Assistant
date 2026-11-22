"""Pydantic schemas for API budget safeguards, session usage, and application settings."""

from pydantic import BaseModel, ConfigDict, Field


class BudgetStatusResponse(BaseModel):
    """Current day API usage and spending safeguard metrics."""

    date: str
    limit_usd: float
    spent_usd: float
    remaining_usd: float
    is_budget_exceeded: bool
    sessions_today: int
    duration_seconds_today: int
    active_sessions: int

    model_config = ConfigDict(from_attributes=True)


class RecordUsagePayload(BaseModel):
    """Payload sent by client upon ending or heartbeat of a WebRTC voice session."""

    duration_seconds: int = Field(default=0, ge=0, description="Active session duration in seconds")
    estimated_cost: float | None = Field(default=None, ge=0.0, description="Optional client-estimated cost")


class SettingsResponse(BaseModel):
    """Application settings summary for configuration and status views."""

    app_name: str
    app_env: str
    ai_provider: str = Field(default="gemini", description="Active AI provider")
    openai_model: str
    openai_voice: str
    gemini_model: str = Field(default="gemini-2.0-flash", description="Gemini model")
    gemini_voice: str = Field(default="Puck", description="Gemini voice persona")
    has_api_key: bool
    allowed_dirs: list[str]
    max_daily_budget_usd: float


class UpdateSettingsPayload(BaseModel):
    """Payload for updating user settings and budget safeguards."""

    max_daily_budget_usd: float | None = Field(
        default=None, gt=0.0, le=100.0, description="Maximum daily API spending in USD"
    )
    allowed_dirs: str | None = Field(
        default=None, description="Comma-separated allowed local directory paths"
    )
