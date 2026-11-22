"""Service for Google Gemini Voice & Live Assistant Integration.

Provides real-time conversation streaming with tool calling and multimodal voice interaction.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any

import httpx
from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError, ConfigurationError
from app.schemas.voice import VoiceSessionRequest, VoiceSessionResponse
from app.services.action_service import ActionService
from app.services.budget_service import BudgetService
from app.tools.registry import default_tool_registry

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

DEFAULT_JARVIS_INSTRUCTIONS = (
    "You are JARVIS, an advanced personal AI desktop assistant engineered for Windows 11. "
    "You communicate with clarity, precision, and respectful confidence. "
    "Keep responses concise and conversational since your speech will be transmitted in real-time. "
    "Never attempt destructive system actions without user approval."
)


class GeminiService:
    """Manages Google Gemini Live sessions, function schemas, and real-time streaming."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def get_gemini_tools(self) -> list[dict[str, Any]]:
        """Convert ToolRegistry schemas into Gemini functionDeclarations format."""
        openai_tools = default_tool_registry.get_realtime_tools()
        declarations = []

        for t in openai_tools:
            fn_name = t.get("name", "")
            fn_desc = t.get("description", "")
            fn_params = t.get("parameters", {"type": "object", "properties": {}})

            declarations.append({
                "name": fn_name,
                "description": fn_desc,
                "parameters": fn_params,
            })

        return declarations

    def create_session(
        self,
        req: VoiceSessionRequest | None = None,
        db: Session | None = None,
    ) -> VoiceSessionResponse:
        """Initialize a Gemini voice session descriptor for client connection."""
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
                message="Google Gemini API key is missing or not configured. Set GEMINI_API_KEY in .env.",
                details=[{"field": "GEMINI_API_KEY", "issue": "Missing or placeholder value"}],
            )

        model = (req and req.model) or self.settings.gemini_model
        voice = (req and req.voice) or self.settings.gemini_voice

        session_id = f"gemini-{uuid.uuid4().hex[:12]}"
        expires_at = int(time.time()) + 3600

        if db is not None:
            BudgetService.record_session_start(db, self.settings)

        return VoiceSessionResponse(
            provider="gemini",
            client_secret="",
            ws_url="/api/voice/gemini-live",
            expires_at=expires_at,
            session_id=session_id,
            model=model,
            voice=voice,
        )

    async def bridge_live_session(self, client_ws: WebSocket, db: Session | None = None) -> None:
        """Manage a live two-way conversational voice bridge for the desktop client."""
        await client_ws.accept()

        if not self.settings.has_valid_api_key():
            await client_ws.send_json({
                "type": "error",
                "error": {
                    "message": "Gemini API key is not configured. Set GEMINI_API_KEY in backend/.env"
                },
            })
            await client_ws.close(code=1008)
            return

        session_start_time = time.time()
        conversation_history: list[dict[str, Any]] = []
        tools = [{"functionDeclarations": self.get_gemini_tools()}]

        # Confirm session established to desktop client
        await client_ws.send_json({
            "type": "session.created",
            "session": {
                "provider": "gemini",
                "model": self.settings.gemini_model,
                "voice": self.settings.gemini_voice,
            },
        })

        async def process_user_turn(user_parts: list[dict[str, Any]]) -> None:
            """Stream response from Gemini with automatic tool execution and model failover."""
            conversation_history.append({"role": "user", "parts": user_parts})
            full_response_text = ""

            payload = {
                "contents": conversation_history,
                "systemInstruction": {"parts": [{"text": DEFAULT_JARVIS_INSTRUCTIONS}]},
                "tools": tools,
            }

            candidate_models = []
            for m in [self.settings.gemini_model, "gemini-3-flash-preview", "gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"]:
                if m and m not in candidate_models:
                    candidate_models.append(m)

            stream_succeeded = False
            last_err_status = 500
            active_model = candidate_models[0]

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    for model_name in candidate_models:
                        stream_url = (
                            f"{GEMINI_API_BASE}/models/{model_name}:streamGenerateContent"
                            f"?alt=sse&key={self.settings.gemini_api_key}"
                        )
                        try:
                            async with client.stream("POST", stream_url, json=payload) as resp:
                                if resp.status_code == 200:
                                    stream_succeeded = True
                                    active_model = model_name
                                    async for line in resp.aiter_lines():
                                        line = line.strip()
                                        if not line.startswith("data: "):
                                            continue

                                        data_str = line[6:]
                                        try:
                                            chunk = json.loads(data_str)
                                        except json.JSONDecodeError:
                                            continue

                                        candidates = chunk.get("candidates", [])
                                        if not candidates:
                                            continue

                                        content = candidates[0].get("content", {})
                                        parts = content.get("parts", [])

                                        for part in parts:
                                            # 1. Stream text
                                            if "text" in part:
                                                delta = part["text"]
                                                full_response_text += delta
                                                await client_ws.send_json({
                                                    "type": "response.audio_transcript.delta",
                                                    "delta": delta,
                                                })

                                            # 2. Handle function calling
                                            elif "functionCall" in part and db is not None:
                                                call_info = part["functionCall"]
                                                fn_name = call_info.get("name", "")
                                                fn_args = call_info.get("args", {})

                                                logger.info("Executing tool: %s (%s)", fn_name, fn_args)
                                                await client_ws.send_json({
                                                    "type": "response.function_call_arguments.done",
                                                    "name": fn_name,
                                                    "arguments": json.dumps(fn_args),
                                                })

                                                action_res = ActionService.request_action(
                                                    db=db,
                                                    action_type=fn_name,
                                                    arguments=fn_args,
                                                    settings=self.settings,
                                                )

                                                tool_output = {
                                                    "status": str(action_res.status),
                                                    "message": action_res.message,
                                                    "result": action_res.result,
                                                }

                                                # Feed tool execution result back to Gemini
                                                tool_turn = {
                                                    "role": "model",
                                                    "parts": [{"functionCall": call_info}],
                                                }
                                                tool_resp_turn = {
                                                    "role": "function",
                                                    "parts": [
                                                        {
                                                            "functionResponse": {
                                                                "name": fn_name,
                                                                "response": {"output": tool_output},
                                                            }
                                                        }
                                                    ],
                                                }

                                                followup_payload = {
                                                    "contents": [*conversation_history, tool_turn, tool_resp_turn],
                                                    "systemInstruction": {
                                                        "parts": [{"text": DEFAULT_JARVIS_INSTRUCTIONS}]
                                                    },
                                                }

                                                async with httpx.AsyncClient(timeout=15.0) as followup_client:
                                                    followup_resp = await followup_client.post(
                                                        f"{GEMINI_API_BASE}/models/{active_model}:generateContent?key={self.settings.gemini_api_key}",
                                                        json=followup_payload,
                                                    )

                                                if followup_resp.status_code == 200:
                                                    f_data = followup_resp.json()
                                                    for f_part in f_data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                                                        if "text" in f_part:
                                                            f_text = f_part["text"]
                                                            full_response_text += f_text
                                                            await client_ws.send_json({
                                                                "type": "response.audio_transcript.delta",
                                                                "delta": f_text,
                                                            })
                                    break
                                else:
                                    last_err_status = resp.status_code
                                    err_body = await resp.aread()
                                    logger.warning(
                                        "Model %s failed with HTTP %d (%s). Trying next fallback candidate...",
                                        model_name,
                                        resp.status_code,
                                        err_body.decode(errors="ignore")[:100],
                                    )
                        except Exception as req_err:  # noqa: BLE001
                            logger.warning("Error contacting model %s: %s", model_name, req_err)
                            continue

                    if not stream_succeeded:
                        await client_ws.send_json({
                            "type": "error",
                            "error": {"message": f"Gemini API returned HTTP {last_err_status}"},
                        })
                        return

                # Mark turn as complete
                if full_response_text:
                    conversation_history.append({
                        "role": "model",
                        "parts": [{"text": full_response_text}],
                    })

                await client_ws.send_json({
                    "type": "response.done",
                    "text": full_response_text,
                })

            except Exception as exc:  # noqa: BLE001
                logger.error("Error generating Gemini voice response: %s", exc)
                await client_ws.send_json({
                    "type": "error",
                    "error": {"message": f"Inference error: {exc!s}"},
                })

        try:
            # Main receive loop
            while True:
                data_text = await client_ws.receive_text()
                try:
                    msg = json.loads(data_text)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")

                # User spoke or sent text prompt
                if msg_type == "conversation.item.create":
                    text_content = msg.get("text", "") or msg.get("item", {}).get("content", [{}])[0].get("text", "")
                    if text_content.strip():
                        # Signal client that thinking begins
                        await client_ws.send_json({"type": "input_audio_buffer.speech_stopped"})
                        await process_user_turn([{"text": text_content.strip()}])

                # Audio buffer commit with base64 recorded audio
                elif msg_type == "input_audio_buffer.commit":
                    audio_b64 = msg.get("audio", "")
                    mime = msg.get("mimeType", "audio/webm")
                    if audio_b64:
                        await client_ws.send_json({"type": "input_audio_buffer.speech_stopped"})
                        await process_user_turn([
                            {"inlineData": {"mimeType": mime, "data": audio_b64}},
                            {"text": "Transcribe the audio command and respond respectfully as JARVIS."},
                        ])

                # Speech start detection
                elif msg_type == "input_audio_buffer.speech_started":
                    await client_ws.send_json({"type": "input_audio_buffer.speech_started"})

        except (WebSocketDisconnect, asyncio.CancelledError):
            logger.info("Client voice WebSocket disconnected")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Voice bridge session ended: %s", exc)
        finally:
            if db is not None:
                try:
                    elapsed = max(0, int(time.time() - session_start_time))
                    BudgetService.record_session_end(db, duration_seconds=elapsed)
                except Exception as b_err:  # noqa: BLE001
                    logger.debug("Failed recording session end: %s", b_err)
