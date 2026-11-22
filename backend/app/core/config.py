"""Application configuration module using Pydantic Settings."""

import os
import sys
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """JARVIS Backend settings validated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=None if os.getenv("APP_ENV") == "test" or "pytest" in sys.modules else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = Field(default="JARVIS", description="Application name")
    app_env: Literal["development", "test", "staging", "production"] = Field(
        default="development", description="Environment stage"
    )
    host: str = Field(default="127.0.0.1", description="Development host IP")
    port: int = Field(default=8000, ge=1, le=65535, description="Port number")

    ai_provider: Literal["openai", "gemini"] = Field(
        default="gemini", description="AI reasoning provider (openai or gemini)"
    )

    openai_api_key: str = Field(default="", description="OpenAI API key (server-side only)")
    openai_realtime_model: str = Field(
        default="gpt-realtime-mini", description="OpenAI Realtime model identifier"
    )
    openai_realtime_voice: str = Field(
        default="marin", description="Voice identifier for Realtime audio"
    )

    gemini_api_key: str = Field(default="", description="Google Gemini API key (server-side only)")
    gemini_model: str = Field(
        default="gemini-2.5-flash", description="Google Gemini model identifier"
    )
    gemini_voice: str = Field(
        default="Puck", description="Voice persona for Gemini audio (Puck, Charon, Kore, Fenrir, Aoede)"
    )

    database_url: str = Field(
        default="sqlite:///./jarvis.db", description="SQLite database connection URL"
    )
    jarvis_data_dir: str = Field(default="", description="Persistent data directory")
    jarvis_allowed_dirs: str = Field(
        default="", description="Comma-separated list of allowed local folders"
    )
    jarvis_max_daily_api_budget_usd: float = Field(
        default=1.00, gt=0.0, description="Max daily API spending safeguard in USD"
    )

    frontend_origin: str = Field(
        default="http://localhost:5173", description="Allowed CORS frontend origin"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Application logging level"
    )

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Host cannot be empty")
        return v

    def get_allowed_directories(self) -> list[str]:
        """Parse allowed directories list safely, falling back to workspace root and docs."""
        dirs: list[str] = []
        if self.jarvis_allowed_dirs:
            dirs = [
                d.strip()
                for d in self.jarvis_allowed_dirs.split(",")
                if d.strip() and os.path.exists(d.strip())
            ]
        if not dirs:
            from pathlib import Path
            workspace_root = str(Path(__file__).resolve().parents[2])
            docs_dir = str(Path(workspace_root).parent / "docs")
            for fallback in [workspace_root, docs_dir]:
                if os.path.exists(fallback) and fallback not in dirs:
                    dirs.append(fallback)
        return dirs

    @property
    def effective_ai_provider(self) -> str:
        """Determine effective AI provider based on configuration and available keys."""
        if self.gemini_api_key and not self.openai_api_key:
            return "gemini"
        if self.openai_api_key and not self.gemini_api_key:
            return "openai"
        return self.ai_provider

    def has_valid_api_key(self) -> bool:
        """Check if an active provider API key is present."""
        if self.gemini_api_key and len(self.gemini_api_key.strip()) > 10:
            return True
        return bool(self.openai_api_key and len(self.openai_api_key.strip()) > 10)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
