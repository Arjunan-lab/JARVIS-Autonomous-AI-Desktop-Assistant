"""Unified Automation Service facade coordinating planning, execution, and verification."""

import logging

from app.services.automation.filesystem_service import FilesystemService
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.services.automation.application_adapter_registry import ApplicationAdapterRegistry
from app.services.automation.automation_models import OperationExecutionResult
from app.services.automation.keyboard_input_service import KeyboardInputService
from app.services.automation.operation_executor import OperationExecutor
from app.services.automation.operation_planner import OperationPlanner
from app.services.automation.operation_verifier import OperationVerifier
from app.services.automation.ui_automation_adapter import UIAutomationAdapter
from app.services.automation.window_manager import WindowManager

logger = logging.getLogger(__name__)


class AutomationService:
    """Primary service coordinating all desktop automation capabilities in JARVIS."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.window_manager = WindowManager(settings=self.settings)
        self.ui_adapter = UIAutomationAdapter(settings=self.settings)
        self.keyboard = KeyboardInputService(settings=self.settings)
        self.verifier = OperationVerifier(window_manager=self.window_manager, settings=self.settings)
        self.filesystem = FilesystemService(settings=self.settings)
        self.planner = OperationPlanner(settings=self.settings)
        self.executor = OperationExecutor(settings=self.settings)
        self.adapter_registry = ApplicationAdapterRegistry(settings=self.settings)

    def execute_command(self, db: Session, user_prompt: str) -> OperationExecutionResult:
        """Decompose a natural language command into an automation plan and execute it."""
        logger.info("AutomationService received command: %s", user_prompt)
        steps = self.planner.plan_operation(user_prompt)
        return self.executor.execute_plan(db=db, intent=user_prompt, steps=steps)

    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel an ongoing operation."""
        return self.executor.cancel_operation(operation_id)
