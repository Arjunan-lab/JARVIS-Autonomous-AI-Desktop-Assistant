"""Service for managing OpenAI Realtime API voice sessions and temporary client tokens."""

import logging
from typing import Any

import httpx
from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError, ConfigurationError
from app.schemas.voice import VoiceSessionRequest, VoiceSessionResponse
from app.services.budget_service import BudgetService
from app.tools.registry import default_tool_registry

logger = logging.getLogger(__name__)

OPENAI_REALTIME_SESSIONS_URL = "https://api.openai.com/v1/realtime/sessions"

DEFAULT_JARVIS_INSTRUCTIONS = (
    "You are JARVIS, a personal AI desktop assistant engineered for Windows 11. "
    "You communicate with clarity, precision, and respectful confidence. "
    "Keep responses concise and conversational since your speech will be transmitted in real-time. "
    "Never attempt destructive system actions without user approval."
)


class RealtimeVoiceService:
    """Handles communication with OpenAI Realtime API to generate ephemeral client secrets."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def create_voice_session(
        self,
        req: VoiceSessionRequest | None = None,
        db: Session | None = None,
    ) -> VoiceSessionResponse:
        """Create a temporary client credential for a WebRTC session."""
        if db is not None:
            can_start, reason = BudgetService.can_start_session(db, self.settings)
            if not can_start:
                raise AppError(
                    message=reason or "Daily API budget safeguard reached",
                    code="BUDGET_EXCEEDED",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        if not self.settings.has_valid_api_key():
            raise ConfigurationError(
                message="OpenAI API key is missing or not configured. Set OPENAI_API_KEY in .env.",
                details=[{"field": "OPENAI_API_KEY", "issue": "Missing or placeholder value"}],
            )

        model = (req and req.model) or self.settings.openai_realtime_model
        voice = (req and req.voice) or self.settings.openai_realtime_voice
        instructions = (req and req.instructions) or DEFAULT_JARVIS_INSTRUCTIONS
        tools = default_tool_registry.get_realtime_tools()

        payload: dict[str, Any] = {
            "model": model,
            "voice": voice,
            "modalities": ["audio", "text"],
            "instructions": instructions,
            "tools": tools,
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500,
            },
        }

        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    OPENAI_REALTIME_SESSIONS_URL,
                    json=payload,
                    headers=headers,
                )

                if response.status_code != 200:
                    err_msg = f"OpenAI Realtime API error (HTTP {response.status_code})"
                    try:
                        err_json = response.json()
                        if "error" in err_json and "message" in err_json["error"]:
                            err_msg = err_json["error"]["message"]
                    except (ValueError, KeyError):
                        logger.debug("Could not parse upstream error response as JSON")

                    logger.error("Failed to create voice session: %s", err_msg)
                    raise AppError(
                        message=err_msg,
                        code="REALTIME_SESSION_FAILED",
                        status_code=response.status_code
                        if response.status_code < 500
                        else status.HTTP_502_BAD_GATEWAY,
                    )

                data = response.json()
                client_secret_data = data.get("client_secret", {})
                client_secret_value = client_secret_data.get("value")
                expires_at = client_secret_data.get("expires_at", 0)
                session_id = data.get("id", "")

                if not client_secret_value:
                    raise AppError(
                        message="OpenAI Realtime response did not contain a client_secret value.",
                        code="INVALID_REALTIME_RESPONSE",
                        status_code=status.HTTP_502_BAD_GATEWAY,
                    )

                if db is not None:
                    BudgetService.record_session_start(db, self.settings)

                return VoiceSessionResponse(
                    client_secret=client_secret_value,
                    expires_at=expires_at,
                    session_id=session_id,
                    model=model,
                    voice=voice,
                )

        except httpx.RequestError as exc:
            logger.error("Network error communicating with OpenAI Realtime API: %s", exc)
            raise AppError(
                message=f"Unable to reach OpenAI Realtime API: {exc!s}",
                code="UPSTREAM_UNAVAILABLE",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
