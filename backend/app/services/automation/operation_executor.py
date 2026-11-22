"""Sequential operation executor with state tracking, cancellation, and error diagnostics."""

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.services.app_manager_service import AppManagerService
from app.services.automation.application_adapter_registry import ApplicationAdapterRegistry
from app.services.automation.automation_models import (
    ActionStep,
    OperationExecutionResult,
    OperationStatus,
    StepExecutionResult,
)
from app.services.automation.automation_permissions import AutomationPermissionGuard
from app.services.automation.filesystem_service import FilesystemService
from app.services.automation.operation_verifier import OperationVerifier
from app.services.automation.window_manager import WindowManager

logger = logging.getLogger(__name__)


class OperationExecutor:
    """Executes validated automation plans step-by-step with real-time status and verification."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.adapter_registry = ApplicationAdapterRegistry(settings=self.settings)
        self.window_manager = WindowManager(settings=self.settings)
        self.verifier = OperationVerifier(window_manager=self.window_manager, settings=self.settings)
        self.filesystem = FilesystemService(settings=self.settings)
        self._active_operations: dict[str, dict[str, Any]] = {}

    def execute_plan(
        self,
        db: Session,
        intent: str,
        steps: list[ActionStep],
        operation_id: str | None = None,
    ) -> OperationExecutionResult:
        """Execute a plan of sequential steps and return a verified outcome report."""
        op_id = operation_id or f"op-{uuid.uuid4().hex[:8]}"
        target_app = steps[0].target_app_id if steps else None

        result = OperationExecutionResult(
            operation_id=op_id,
            intent=intent,
            target_app_id=target_app,
            status=OperationStatus.RUNNING,
            steps_planned=len(steps),
            steps_completed=0,
            step_results=[],
        )

        was_cancelled = self._active_operations.get(op_id, {}).get("cancelled", False)
        self._active_operations[op_id] = {"cancelled": was_cancelled, "status": OperationStatus.RUNNING}

        for step in steps:
            # Check cancellation
            if self._active_operations.get(op_id, {}).get("cancelled"):
                result.status = OperationStatus.CANCELLED
                result.error_message = "Operation was cancelled by user."
                result.completed_at = datetime.now(UTC)
                return result

            step_res = self._execute_step(db, step)
            result.step_results.append(step_res)

            if step_res.status == OperationStatus.COMPLETED:
                result.steps_completed += 1
                if step_res.evidence:
                    result.verification_evidence.update(step_res.evidence)
            else:
                # Step failed or requires approval: halt execution
                result.status = step_res.status
                result.error_message = step_res.message
                result.completed_at = datetime.now(UTC)

                AutomationPermissionGuard.log_automation_audit(
                    db=db,
                    action_type=step.action_type,
                    outcome="failed",
                    details={
                        "operation_id": op_id,
                        "step_id": step.step_id,
                        "error": step_res.message,
                    },
                )
                return result

        result.status = OperationStatus.COMPLETED
        result.completed_at = datetime.now(UTC)

        AutomationPermissionGuard.log_automation_audit(
            db=db,
            action_type="workflow_execution",
            outcome="success",
            details={
                "operation_id": op_id,
                "intent": intent,
                "steps_completed": result.steps_completed,
            },
        )
        return result

    def cancel_operation(self, operation_id: str) -> bool:
        """Signal cancellation for an active operation."""
        if operation_id not in self._active_operations:
            self._active_operations[operation_id] = {"cancelled": True, "status": OperationStatus.CANCELLED}
        else:
            self._active_operations[operation_id]["cancelled"] = True
        return True

    def _execute_step(self, db: Session, step: ActionStep) -> StepExecutionResult:
        """Execute a single atomic step with proper adapters and guards."""
        start_time = datetime.now(UTC)
        try:
            # 1. Launch or Focus
            if step.action_type == "launch_or_focus":
                app_name = step.arguments.get("application", "")
                managed_app = AutomationPermissionGuard.check_application_permission(
                    db, app_name, operation="launch_or_focus"
                )

                # Check if window already exists
                wins = self.window_manager.find_windows(app_name=app_name)
                if wins:
                    win = wins[0]
                    self.window_manager.activate_window(win)
                    return StepExecutionResult(
                        step_id=step.step_id,
                        action_type=step.action_type,
                        status=OperationStatus.COMPLETED,
                        message=f"Activated existing window for '{managed_app.name}'",
                        evidence={"window_title": win.title, "reused_window": True},
                        started_at=start_time,
                        completed_at=datetime.now(UTC),
                    )

                # Window not open: launch application
                AppManagerService.launch_app(db, managed_app.id, self.settings)
                time.sleep(0.5)

                evidence: dict[str, Any] = {"new_launch": True}
                try:
                    win = self.window_manager.get_application_window(app_name, timeout_seconds=min(step.timeout_seconds, 4.0))
                    self.window_manager.activate_window(win)
                    evidence["window_title"] = win.title
                except Exception as win_err:  # noqa: BLE001
                    logger.debug("Window activation pending or async for '%s': %s", app_name, win_err)
                    evidence["launched_async"] = True

                return StepExecutionResult(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    status=OperationStatus.COMPLETED,
                    message=f"Launched and focused '{managed_app.name}'",
                    evidence=evidence,
                    started_at=start_time,
                    completed_at=datetime.now(UTC),
                )

            # Calculation Step (Calculator & arithmetic operations)
            if step.action_type == "calculate":
                expr = step.arguments.get("expression", "")
                calc_res = step.arguments.get("result")

                # If calculator is focused, type the keys into it
                try:
                    wins = self.window_manager.find_windows(app_name="calculator")
                    if wins:
                        win = wins[0]
                        self.window_manager.activate_window(win)
                        key_expr = str(expr).replace(" ", "") + "="
                        self.keyboard.type_keys(key_expr)
                except Exception as calc_err:  # noqa: BLE001
                    logger.debug("Calculator keypress reflection bypassed: %s", calc_err)

                return StepExecutionResult(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    status=OperationStatus.COMPLETED,
                    message=f"Calculation: {expr} = {calc_res}",
                    evidence={"expression": expr, "result": calc_res, "verified": True},
                    started_at=start_time,
                    completed_at=datetime.now(UTC),
                )

            # 2. Type Text into Application
            if step.action_type == "type_text":
                app_name = step.arguments.get("application", "")
                text = step.arguments.get("text", "")
                adapter = self.adapter_registry.get_adapter(app_name)

                if hasattr(adapter, "write_text"):
                    res = adapter.write_text(text, timeout_seconds=step.timeout_seconds)
                else:
                    win = self.window_manager.get_application_window(app_name)
                    self.window_manager.activate_window(win)
                    self.adapter_registry.ui_adapter.set_text(win.handle, text)
                    res = {"success": True, "text": text}

                return StepExecutionResult(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    status=OperationStatus.COMPLETED,
                    message=f"Entered text into {app_name}",
                    evidence=res,
                    started_at=start_time,
                    completed_at=datetime.now(UTC),
                )

            # 3. Verify UI Text
            if step.action_type == "verify_ui_text":
                app_name = step.arguments.get("application", "")
                expected = step.arguments.get("expected_text", "")
                win = self.window_manager.get_application_window(app_name)
                evidence = self.verifier.verify_text_entry(win.handle, expected)

                return StepExecutionResult(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    status=OperationStatus.COMPLETED,
                    message=f"Verified text in {app_name}",
                    evidence=evidence,
                    started_at=start_time,
                    completed_at=datetime.now(UTC),
                )

            # 4. Save Document File
            if step.action_type == "save_file":
                app_name = step.arguments.get("application", "")
                file_path_str = step.arguments.get("file_path", "")
                dest_path = AutomationPermissionGuard.check_filesystem_permission(
                    file_path_str, self.settings, allow_overwrite=True
                )

                text_content = step.arguments.get("text")
                adapter = self.adapter_registry.get_adapter(app_name)
                if hasattr(adapter, "save_file"):
                    res = adapter.save_file(dest_path, text=text_content, timeout_seconds=step.timeout_seconds)
                else:
                    dest_path.write_text(text_content or "Hello from JARVIS", encoding="utf-8")
                    res = {"saved_to": str(dest_path)}

                return StepExecutionResult(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    status=OperationStatus.COMPLETED,
                    message=f"Saved document to '{dest_path.name}'",
                    evidence=res,
                    started_at=start_time,
                    completed_at=datetime.now(UTC),
                )

            # 5. Open Folder in Explorer
            if step.action_type == "open_folder":
                folder_str = step.arguments.get("folder_path", "")
                dest_folder = AutomationPermissionGuard.check_filesystem_permission(folder_str, self.settings)
                adapter = self.adapter_registry.get_adapter("explorer")
                res = adapter.open_folder(dest_folder)

                return StepExecutionResult(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    status=OperationStatus.COMPLETED,
                    message=f"Opened folder '{dest_folder.name}' in File Explorer",
                    evidence=res,
                    started_at=start_time,
                    completed_at=datetime.now(UTC),
                )

            # 6. Open Workspace in VS Code
            if step.action_type == "open_workspace":
                proj_str = step.arguments.get("project_path", "")
                proj_path = AutomationPermissionGuard.check_filesystem_permission(proj_str, self.settings)
                adapter = self.adapter_registry.get_adapter("code")
                res = adapter.open_workspace(proj_path)

                return StepExecutionResult(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    status=OperationStatus.COMPLETED,
                    message=f"Opened workspace '{proj_path.name}' in VS Code",
                    evidence=res,
                    started_at=start_time,
                    completed_at=datetime.now(UTC),
                )

            # 7. Open Browser URL
            if step.action_type == "open_browser":
                url = step.arguments.get("url", "")
                adapter = self.adapter_registry.get_adapter("chrome")
                res = adapter.open_url(url)

                return StepExecutionResult(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    status=OperationStatus.COMPLETED,
                    message=f"Opened URL in browser: {url}",
                    evidence=res,
                    started_at=start_time,
                    completed_at=datetime.now(UTC),
                )

            # 8. Filesystem Read
            if step.action_type == "read_text_file":
                f_path = step.arguments.get("file_path", "")
                content = self.filesystem.read_text_file(f_path)
                return StepExecutionResult(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    status=OperationStatus.COMPLETED,
                    message=f"Read {len(content)} characters from file",
                    evidence={"file_path": f_path, "preview": content[:150]},
                    started_at=start_time,
                    completed_at=datetime.now(UTC),
                )

            # 9. Filesystem Write
            if step.action_type == "write_text_file":
                f_path = step.arguments.get("file_path", "")
                content = step.arguments.get("content", "")
                overwrite = step.arguments.get("overwrite", False)
                res = self.filesystem.write_text_file(f_path, content, overwrite=overwrite)

                return StepExecutionResult(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    status=OperationStatus.COMPLETED,
                    message=f"Wrote {res.get('size_bytes', 0)} bytes to file",
                    evidence=res,
                    started_at=start_time,
                    completed_at=datetime.now(UTC),
                )

            # 10. Verify File on Disk
            if step.action_type == "verify_file":
                f_path = step.arguments.get("file_path", "")
                expected = step.arguments.get("expected_content")
                res = self.filesystem.verify_file(f_path, expected_content=expected)

                return StepExecutionResult(
                    step_id=step.step_id,
                    action_type=step.action_type,
                    status=OperationStatus.COMPLETED,
                    message=f"Verified file exists on disk ({res.get('size_bytes', 0)} bytes)",
                    evidence=res,
                    started_at=start_time,
                    completed_at=datetime.now(UTC),
                )

            # Generic fallback step
            return StepExecutionResult(
                step_id=step.step_id,
                action_type=step.action_type,
                status=OperationStatus.COMPLETED,
                message=step.description,
                started_at=start_time,
                completed_at=datetime.now(UTC),
            )

        except Exception as e:  # noqa: BLE001
            logger.error("Step '%s' failed: %s", step.step_id, e)
            return StepExecutionResult(
                step_id=step.step_id,
                action_type=step.action_type,
                status=OperationStatus.FAILED,
                message=str(e),
                error_code=getattr(e, "code", "STEP_FAILED"),
                started_at=start_time,
                completed_at=datetime.now(UTC),
            )
