"""Comprehensive unit and integration test suite for the JARVIS Universal Desktop Automation Engine."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.models import ManagedApp
from app.db.session import Base, get_db
from app.main import create_app
from app.services.automation.automation_errors import (
    OperationPermissionDeniedError,
    WindowNotFoundError,
)
from app.services.automation.automation_models import ActionStep, OperationStatus
from app.services.automation.automation_permissions import AutomationPermissionGuard
from app.services.automation.automation_service import AutomationService
from app.services.automation.filesystem_service import FilesystemService
from app.services.automation.keyboard_input_service import KeyboardInputService
from app.services.automation.operation_executor import OperationExecutor
from app.services.automation.operation_planner import OperationPlanner
from app.services.automation.ui_automation_adapter import UIAutomationAdapter
from app.services.automation.window_manager import WindowManager


@pytest.fixture
def automation_test_env(tmp_path: Path):
    """Set up isolated in-memory test database, sandbox directory, and FastAPI client."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    sandbox = tmp_path / "sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        app_name="JARVIS-TEST",
        app_env="test",
        host="127.0.0.1",
        port=8000,
        openai_api_key="",
        database_url="sqlite:///:memory:",
        jarvis_allowed_dirs=str(sandbox.resolve()),
        log_level="DEBUG",
    )

    test_app = create_app(settings=settings)
    test_app.dependency_overrides[get_db] = override_get_db

    session = TestingSessionLocal()

    # Seed managed applications
    app1 = ManagedApp(
        id="app-notepad-01",
        name="Notepad",
        target_path="C:\\Windows\\System32\\notepad.exe",
        target_type="executable",
        category="Utilities",
        is_enabled=True,
        is_available=True,
    )
    app2 = ManagedApp(
        id="app-calc-02",
        name="Calculator",
        target_path="C:\\Windows\\System32\\calc.exe",
        target_type="executable",
        category="Utilities",
        is_enabled=False,  # Disabled
        is_available=True,
    )
    session.add_all([app1, app2])
    session.commit()

    with TestClient(test_app) as client:
        yield client, session, settings, sandbox

    session.close()
    test_app.dependency_overrides.clear()


class TestWindowManager:
    """Tests for WindowManager discovery and activation."""

    def test_find_windows_mock(self, automation_test_env):
        _, _, settings, _ = automation_test_env
        wm = WindowManager(settings=settings)
        windows = wm.find_windows(app_name="notepad")
        assert len(windows) >= 1
        assert "Notepad" in windows[0].title
        assert windows[0].is_active is True

    def test_window_not_found(self, automation_test_env):
        _, _, settings, _ = automation_test_env
        wm = WindowManager(settings=settings)
        with pytest.raises(WindowNotFoundError):
            wm.get_application_window("ghost_nonexistent_app", timeout_seconds=0.5)

    def test_activate_window(self, automation_test_env):
        _, _, settings, _ = automation_test_env
        wm = WindowManager(settings=settings)
        windows = wm.find_windows(app_name="notepad")
        assert wm.activate_window(windows[0]) is True


class TestUIAutomationAdapter:
    """Tests for UIAutomationAdapter control discovery and interaction."""

    def test_find_controls_mock(self, automation_test_env):
        _, _, settings, _ = automation_test_env
        uia = UIAutomationAdapter(settings=settings)
        controls = uia.find_controls(hwnd=1001)
        assert len(controls) >= 1
        assert any(c.name == "Text Editor" for c in controls)

    def test_set_and_get_text(self, automation_test_env):
        _, _, settings, _ = automation_test_env
        uia = UIAutomationAdapter(settings=settings)
        assert uia.set_text(hwnd=1001, text="Hello from JARVIS") is True
        text = uia.get_text(hwnd=1001)
        assert "Hello from JARVIS" in text


class TestKeyboardAndMouseServices:
    """Tests for safe keyboard typing, shortcut validation, and bounded pointer clicks."""

    def test_allowed_shortcuts(self, automation_test_env):
        _, _, settings, _ = automation_test_env
        wm = WindowManager(settings=settings)
        win = wm.find_windows(app_name="notepad")[0]
        kb = KeyboardInputService(settings=settings)

        assert kb.send_shortcut(win, "^s") is True
        assert kb.send_shortcut(win, "{ENTER}") is True

    def test_blocked_dangerous_shortcut(self, automation_test_env):
        _, _, settings, _ = automation_test_env
        wm = WindowManager(settings=settings)
        win = wm.find_windows(app_name="notepad")[0]
        kb = KeyboardInputService(settings=settings)

        with pytest.raises(OperationPermissionDeniedError):
            kb.send_shortcut(win, "%{F4}")  # Alt+F4 blocked!


class TestAutomationPermissions:
    """Tests for operation-level permission guard."""

    def test_check_enabled_application(self, automation_test_env):
        _, session, _, _ = automation_test_env
        app = AutomationPermissionGuard.check_application_permission(session, "Notepad")
        assert app.is_enabled is True

    def test_check_disabled_application_denied(self, automation_test_env):
        _, session, _, _ = automation_test_env
        with pytest.raises(OperationPermissionDeniedError) as exc_info:
            AutomationPermissionGuard.check_application_permission(session, "Calculator")
        assert "disabled" in str(exc_info.value).lower()

    def test_check_unmanaged_application_denied(self, automation_test_env):
        _, session, _, _ = automation_test_env
        with pytest.raises(OperationPermissionDeniedError) as exc_info:
            AutomationPermissionGuard.check_application_permission(session, "MaliciousSoftware")
        assert "not in the managed catalog" in str(exc_info.value).lower()


class TestFilesystemService:
    """Tests for sandboxed, secure filesystem operations."""

    def test_write_read_and_verify_file(self, automation_test_env):
        _, _, settings, sandbox = automation_test_env
        fs = FilesystemService(settings=settings)
        target = sandbox / "test_doc.txt"

        # Write
        write_res = fs.write_text_file(str(target), "Alpha telemetry data")
        assert write_res["written"] is True
        assert target.exists()

        # Read
        content = fs.read_text_file(str(target))
        assert content == "Alpha telemetry data"

        # Verify
        verify_res = fs.verify_file(str(target), expected_content="Alpha telemetry")
        assert verify_res["verified"] is True

    def test_overwrite_protection(self, automation_test_env):
        _, _, settings, sandbox = automation_test_env
        fs = FilesystemService(settings=settings)
        target = sandbox / "existing.txt"
        target.write_text("existing data", encoding="utf-8")

        # Overwrite=False must fail
        with pytest.raises(OperationPermissionDeniedError) as exc_info:
            fs.write_text_file(str(target), "new data", overwrite=False)
        assert "already exists" in str(exc_info.value).lower()

        # Overwrite=True succeeds
        res = fs.write_text_file(str(target), "new data", overwrite=True)
        assert res["written"] is True
        assert target.read_text(encoding="utf-8") == "new data"

    def test_blocked_credential_file(self, automation_test_env):
        _, _, settings, sandbox = automation_test_env
        fs = FilesystemService(settings=settings)
        env_file = sandbox / ".env"
        env_file.write_text("SECRET=12345", encoding="utf-8")

        with pytest.raises(OperationPermissionDeniedError):
            fs.read_text_file(str(env_file))


class TestOperationPlannerAndExecutor:
    """End-to-end multi-step plan generation and verified execution tests."""

    def test_plan_notepad_write_and_save(self, automation_test_env):
        _, _, settings, _ = automation_test_env
        planner = OperationPlanner(settings=settings)
        steps = planner.plan_operation("JARVIS, open Notepad and write Hello from JARVIS and save it as test.txt on my Desktop")

        action_types = [s.action_type for s in steps]
        assert "launch_or_focus" in action_types
        assert "type_text" in action_types
        assert "verify_ui_text" in action_types
        assert "save_file" in action_types
        assert "verify_file" in action_types

    def test_execute_notepad_plan(self, automation_test_env):
        _, session, settings, _sandbox = automation_test_env
        svc = AutomationService(settings=settings)
        result = svc.execute_command(session, "open Notepad and write Hello from JARVIS")

        assert result.status == OperationStatus.COMPLETED
        assert result.steps_completed >= 3
        assert result.error_message is None

    def test_plan_and_execute_milestone2_workflow(self, automation_test_env):
        """Milestone 2 core workflow: open Notepad, write test text, save to Desktop as JARVIS_Test.txt, verify."""
        _, session, settings, sandbox = automation_test_env
        # Point Desktop directory to sandbox for isolated testing
        planner = OperationPlanner(settings=settings)
        prompt = (
            "JARVIS, open Notepad, write 'My JARVIS automation test is successful', "
            "and save it to my Desktop as JARVIS_Test.txt."
        )
        steps = planner.plan_operation(prompt)

        assert len(steps) == 5
        assert steps[0].action_type == "launch_or_focus"
        assert steps[1].action_type == "type_text"
        assert steps[1].arguments["text"] == "My JARVIS automation test is successful"
        assert steps[2].action_type == "verify_ui_text"
        assert steps[3].action_type == "save_file"
        assert "JARVIS_Test.txt" in steps[3].arguments["file_path"]
        assert steps[4].action_type == "verify_file"
        assert steps[4].arguments["expected_content"] == "My JARVIS automation test is successful"

        # Execute full workflow in test sandbox
        target_file = sandbox / "JARVIS_Test.txt"
        steps[3].arguments["file_path"] = str(target_file)
        steps[4].arguments["file_path"] = str(target_file)

        executor = OperationExecutor(settings=settings)
        res = executor.execute_plan(session, prompt, steps)
        assert res.status == OperationStatus.COMPLETED
        assert res.steps_completed == 5
        assert target_file.exists()
        assert "My JARVIS automation test is successful" in target_file.read_text(encoding="utf-8")

    def test_execute_plan_cancellation(self, automation_test_env):
        _, session, settings, _ = automation_test_env
        executor = OperationExecutor(settings=settings)
        op_id = "test-cancel-op"

        steps = [
            ActionStep(step_id="1", action_type="launch_or_focus", description="Step 1", arguments={"application": "notepad"}),
            ActionStep(step_id="2", action_type="type_text", description="Step 2", arguments={"application": "notepad", "text": "sample"}),
        ]

        # Trigger cancellation before execution
        executor.cancel_operation(op_id)
        res = executor.execute_plan(session, "Write sample", steps, operation_id=op_id)
        assert res.status == OperationStatus.CANCELLED


class TestCommandAPIEndpoints:
    """Integration tests for POST /api/commands/execute and cancellation."""

    def test_api_execute_notepad_command(self, automation_test_env):
        client, _, _, _ = automation_test_env
        response = client.post("/api/commands/execute", json={"command": "JARVIS, open Notepad and write Hello from JARVIS"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["steps_completed"] >= 3
        assert len(data["step_results"]) >= 3

    def test_api_execute_folder_command(self, automation_test_env):
        client, _, _, _ = automation_test_env
        response = client.post("/api/commands/execute", json={"command": "Open my JARVIS project folder in File Explorer"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["steps_completed"] == 1

    def test_api_cancel_operation(self, automation_test_env):
        client, _, _, _ = automation_test_env
        response = client.post("/api/commands/operations/nonexistent-op/cancel")
        assert response.status_code == 200
        assert "message" in response.json()
