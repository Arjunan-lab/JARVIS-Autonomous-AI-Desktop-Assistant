"""Domain models and data structures for the JARVIS Universal Desktop Automation Engine."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OperationStatus(str, Enum):
    """Lifecycle status of a desktop automation operation."""

    PLANNED = "planned"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OperationType(str, Enum):
    """Categorization of desktop actions."""

    LAUNCH = "launch"
    WINDOW_FOCUS = "window_focus"
    UI_INTERACTION = "ui_interaction"
    KEYBOARD_INPUT = "keyboard_input"
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    COMMAND_EXECUTION = "command_execution"
    DESTRUCTIVE = "destructive"


class WindowInfo(BaseModel):
    """Information about an identified application window."""

    handle: int
    title: str
    process_id: int
    executable_name: str
    is_active: bool = False
    is_minimized: bool = False
    is_visible: bool = True
    class_name: str = ""
    rect: dict[str, int] = Field(default_factory=lambda: {"left": 0, "top": 0, "right": 0, "bottom": 0})


class UIControlInfo(BaseModel):
    """Representation of an accessible UI element."""

    name: str
    control_type: str
    automation_id: str = ""
    class_name: str = ""
    is_enabled: bool = True
    is_visible: bool = True
    rect: dict[str, int] = Field(default_factory=lambda: {"left": 0, "top": 0, "right": 0, "bottom": 0})
    current_value: str | None = None


class ActionStep(BaseModel):
    """A single atomic action in an automation plan."""

    step_id: str
    action_type: str
    description: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    target_app_id: str | None = None
    requires_approval: bool = False
    timeout_seconds: float = 10.0


class StepExecutionResult(BaseModel):
    """Result of executing a single action step."""

    step_id: str
    action_type: str
    status: OperationStatus
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    error_code: str | None = None


class OperationExecutionResult(BaseModel):
    """Overall outcome of a multi-step automation workflow."""

    operation_id: str
    intent: str
    target_app_id: str | None = None
    target_app_name: str | None = None
    status: OperationStatus
    steps_planned: int = 0
    steps_completed: int = 0
    step_results: list[StepExecutionResult] = Field(default_factory=list)
    verification_evidence: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    requires_approval: bool = False
    approval_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
