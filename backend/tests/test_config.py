"""Unit tests for configuration loading and validation."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_settings():
    """Verify default configuration loads with expected defaults."""
    settings = Settings(openai_api_key="sk-testkey12345678901234567890")
    assert settings.app_name == "JARVIS"
    assert settings.app_env in ["development", "test"]
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.has_valid_api_key() is True


def test_invalid_port_rejected():
    """Verify out-of-range ports are rejected cleanly by Pydantic."""
    with pytest.raises(ValidationError):
        Settings(port=-1)

    with pytest.raises(ValidationError):
        Settings(port=70000)


def test_invalid_budget_rejected():
    """Verify non-positive budget safeguard is rejected."""
    with pytest.raises(ValidationError):
        Settings(jarvis_max_daily_api_budget_usd=0.0)

    with pytest.raises(ValidationError):
        Settings(jarvis_max_daily_api_budget_usd=-5.0)


def test_invalid_env_rejected():
    """Verify unsupported app_env is rejected."""
    with pytest.raises(ValidationError):
        Settings(app_env="invalid_environment")  # type: ignore[arg-type]


def test_api_key_status_check():
    """Verify has_valid_api_key handles empty or short placeholder keys."""
    assert Settings(openai_api_key="", gemini_api_key="").has_valid_api_key() is False
    assert Settings(openai_api_key="short", gemini_api_key="short").has_valid_api_key() is False
    assert Settings(openai_api_key="sk-valid-key-with-sufficient-length").has_valid_api_key() is True
    assert Settings(gemini_api_key="AIzaSyValidKeyWithSufficientLength12345").has_valid_api_key() is True
