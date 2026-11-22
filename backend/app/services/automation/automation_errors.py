"""Structured exceptions for the JARVIS Desktop Automation Engine."""

from typing import Any


class AutomationError(Exception):
    """Base class for all automation-related exceptions."""

    def __init__(self, message: str, code: str = "AUTOMATION_ERROR", details: Any = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class WindowNotFoundError(AutomationError):
    """Raised when an application window cannot be found."""

    def __init__(self, message: str = "Target application window not found", details: Any = None):
        super().__init__(message, code="WINDOW_NOT_FOUND", details=details)


class WindowNotActiveError(AutomationError):
    """Raised when an application window fails to receive foreground focus."""

    def __init__(self, message: str = "Window failed to acquire foreground focus", details: Any = None):
        super().__init__(message, code="WINDOW_NOT_ACTIVE", details=details)


class TargetAmbiguousError(AutomationError):
    """Raised when multiple matching windows exist and cannot be confidently resolved."""

    def __init__(self, message: str = "Multiple matching windows found; target is ambiguous", details: Any = None):
        super().__init__(message, code="TARGET_AMBIGUOUS", details=details)


class ControlNotFoundError(AutomationError):
    """Raised when an accessible control (button, edit box, menu) cannot be found."""

    def __init__(self, message: str = "Required UI control not found", details: Any = None):
        super().__init__(message, code="CONTROL_NOT_FOUND", details=details)


class ControlInteractionError(AutomationError):
    """Raised when a control exists but cannot be clicked, typed into, or read."""

    def __init__(self, message: str = "Failed to interact with UI control", details: Any = None):
        super().__init__(message, code="CONTROL_INTERACTION_FAILED", details=details)


class VerificationFailedError(AutomationError):
    """Raised when an action executes but post-execution verification fails."""

    def __init__(self, message: str = "Action completed but verification failed", details: Any = None):
        super().__init__(message, code="VERIFICATION_FAILED", details=details)


class OperationTimeoutError(AutomationError):
    """Raised when an action or window wait exceeds its bounded timeout."""

    def __init__(self, message: str = "Operation exceeded timeout limit", details: Any = None):
        super().__init__(message, code="OPERATION_TIMEOUT", details=details)


class OperationPermissionDeniedError(AutomationError):
    """Raised when an operation violates permission boundaries or security policies."""

    def __init__(self, message: str = "Permission denied for requested automation action", details: Any = None):
        super().__init__(message, code="OPERATION_PERMISSION_DENIED", details=details)
