"""Pydantic schemas for voice session requests and responses."""


from pydantic import BaseModel, Field


class VoiceSessionRequest(BaseModel):
    """Optional configuration overrides when initiating a voice session."""

    model: str | None = Field(default=None, description="Override Realtime model")
    voice: str | None = Field(default=None, description="Override voice persona")
    instructions: str | None = Field(
        default=None, description="Optional custom session system instructions"
    )


class VoiceSessionResponse(BaseModel):
    """Short-lived client session credentials returned to the frontend.

    Security Guarantee: Never contains permanent server API keys.
    """

    provider: str = Field(default="openai", description="Voice provider (openai or gemini)")
    client_secret: str = Field(default="", description="Short-lived client secret (ek_...)")
    ws_url: str | None = Field(default=None, description="WebSocket URL for streaming bridge")
    expires_at: int = Field(..., description="Credential expiration unix timestamp")
    session_id: str = Field(..., description="Session identifier")
    model: str = Field(..., description="Selected model")
    voice: str = Field(..., description="Selected voice persona")
    switched_to_fallback: bool = Field(default=False, description="Whether fallback provider was activated")
    fallback_reason: str | None = Field(default=None, description="Reason for provider failover")


class VoiceSynthesisRequest(BaseModel):
    """Payload for neural text-to-speech audio synthesis."""

    text: str = Field(..., min_length=1, max_length=4000, description="Text to vocalize")
    voice: str = Field(
        default="en-GB-RyanNeural",
        description="Neural voice name (defaults to fluent British JARVIS voice en-GB-RyanNeural)",
    )
    rate: str = Field(default="-3%", description="Speaking rate modification (e.g. -3% for fluent cadence)")
    pitch: str = Field(default="-2Hz", description="Voice pitch modification (e.g. -2Hz for bold baritone)")
