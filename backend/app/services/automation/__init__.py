"""JARVIS Universal Desktop Automation Engine package."""

from app.services.automation.filesystem_service import FilesystemService

from app.services.automation.automation_errors import (
    AutomationError,
    ControlInteractionError,
    ControlNotFoundError,
    OperationPermissionDeniedError,
    OperationTimeoutError,
    TargetAmbiguousError,
    VerificationFailedError,
    WindowNotActiveError,
    WindowNotFoundError,
)
from app.services.automation.automation_models import (
    ActionStep,
    OperationExecutionResult,
    OperationStatus,
    OperationType,
    StepExecutionResult,
    UIControlInfo,
    WindowInfo,
)
from app.services.automation.automation_permissions import AutomationPermissionGuard
from app.services.automation.automation_service import AutomationService
from app.services.automation.keyboard_input_service import KeyboardInputService
from app.services.automation.mouse_input_service import MouseInputService
from app.services.automation.operation_executor import OperationExecutor
from app.services.automation.operation_planner import OperationPlanner
from app.services.automation.operation_verifier import OperationVerifier
from app.services.automation.ui_automation_adapter import UIAutomationAdapter
from app.services.automation.window_manager import WindowManager

__all__ = [
    "ActionStep",
    "AutomationError",
    "AutomationPermissionGuard",
    "AutomationService",
    "ControlInteractionError",
    "ControlNotFoundError",
    "FilesystemService",
    "KeyboardInputService",
    "MouseInputService",
    "OperationExecutionResult",
    "OperationExecutor",
    "OperationPermissionDeniedError",
    "OperationPlanner",
    "OperationStatus",
    "OperationTimeoutError",
    "OperationType",
    "OperationVerifier",
    "StepExecutionResult",
    "TargetAmbiguousError",
    "UIAutomationAdapter",
    "UIControlInfo",
    "VerificationFailedError",
    "WindowInfo",
    "WindowManager",
    "WindowNotActiveError",
    "WindowNotFoundError",
]
