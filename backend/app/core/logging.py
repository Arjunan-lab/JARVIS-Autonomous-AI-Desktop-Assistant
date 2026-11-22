"""Structured logging configuration with secret masking."""

import logging
import re
import sys

# Pattern for OpenAI API keys, Google Gemini keys, and standard authorization tokens
SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"AIzaSy[a-zA-Z0-9_\-]{33}", re.IGNORECASE),
    re.compile(r"Bearer\s+([a-zA-Z0-9_\-\.]+)", re.IGNORECASE),
    re.compile(r"api[_\-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]+)['\"]?", re.IGNORECASE),
]


class SecretMaskingFilter(logging.Filter):
    """Logging filter that scrubs sensitive keys and tokens from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._sanitize(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._sanitize_val(v) for k, v in record.args.items()}
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(self._sanitize_val(a) for a in record.args)
        return True

    def _sanitize_val(self, val: object) -> object:
        if isinstance(val, str):
            return self._sanitize(val)
        return val

    def _sanitize(self, text: str) -> str:
        sanitized = text
        for pattern in SECRET_PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
        return sanitized


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with formatting and secret masking filter."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Format: Timestamp | Level | Logger | Message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    handler.addFilter(SecretMaskingFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers on reloads
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Silence excessive debug noise from third-party libraries if any
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
