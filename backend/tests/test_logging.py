"""Tests for log scrubbing and security masking."""

import logging

from app.core.logging import SecretMaskingFilter


def test_secret_masking_filter():
    """Verify SecretMaskingFilter scrubs OpenAI keys and Bearer tokens."""
    scrubber = SecretMaskingFilter()

    # Test OpenAI API key scrubbing
    record1 = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Connecting using key sk-abcdef12345678901234567890 securely",
        args=(),
        exc_info=None,
    )
    scrubber.filter(record1)
    assert "sk-abcdef12345678901234567890" not in record1.msg
    assert "[REDACTED_SECRET]" in record1.msg

    # Test Bearer token scrubbing
    record2 = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Authorization: Bearer secret_token_xyz_12345",
        args=(),
        exc_info=None,
    )
    scrubber.filter(record2)
    assert "secret_token_xyz_12345" not in record2.msg
    assert "[REDACTED_SECRET]" in record2.msg
