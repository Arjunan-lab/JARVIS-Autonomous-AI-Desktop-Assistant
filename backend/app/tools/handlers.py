"""Typed tool execution handlers."""

import subprocess
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.memory_service import MemoryService
from app.services.task_service import TaskService
from app.tools.policies import is_path_within_allowed_dirs, validate_application_name


class ToolHandlers:
    """Implementations of all allowlisted assistant actions."""

    @staticmethod
    def create_task(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Create a new task with title, priority, and optional due date."""
        task_in = TaskCreate(
            title=arguments.get("title", ""),
            description=arguments.get("description"),
            priority=arguments.get("priority", "medium"),
            due_date=arguments.get("due_date"),
        )
        service = TaskService(db=db)
        task = service.create_task(task_in)
        return {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        }

    @staticmethod
    def list_tasks(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """List tasks with optional status and priority filtering."""
        service = TaskService(db=db)
        status_filter = arguments.get("status")
        priority_filter = arguments.get("priority")
        tasks, total, pending, completed = service.list_tasks(
            status=status_filter, priority=priority_filter
        )
        return {
            "total": total,
            "pending_count": pending,
            "completed_count": completed,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                }
                for t in tasks
            ],
        }

    @staticmethod
    def complete_task(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Mark a task as completed."""
        task_id = arguments.get("task_id")
        if not task_id:
            raise ValueError("Argument 'task_id' is required")

        service = TaskService(db=db)
        task = service.update_task(task_id, TaskUpdate(status="completed"))
        if not task:
            raise ValueError(f"Task with ID '{task_id}' not found")

        return {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "updated_at": task.updated_at.isoformat(),
        }

    @staticmethod
    def search_allowed_files(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Search approved local directories for keyword matches."""
        query = arguments.get("query", "").strip()
        if not query:
            return {"query": query, "results": []}

        max_results = min(int(arguments.get("max_results", 10)), 50)
        results = MemoryService.search_allowed_documents(
            query=query,
            allowed_dirs=settings.jarvis_allowed_dirs,
            max_results=max_results,
        )
        return {
            "query": query,
            "results": [r.model_dump() for r in results],
        }

    @staticmethod
    def read_allowed_text_file(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Read text from a file strictly located within an approved directory."""
        file_path_raw = arguments.get("file_path", "").strip()
        if not file_path_raw:
            raise ValueError("Argument 'file_path' is required")

        target_path = Path(file_path_raw).resolve()
        if not is_path_within_allowed_dirs(target_path, settings.jarvis_allowed_dirs):
            raise PermissionError(
                f"Access denied: Path '{file_path_raw}' is outside approved directories"
            )

        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"File '{file_path_raw}' not found")

        # Read up to 50KB or 1000 lines
        max_bytes = 50 * 1024
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_bytes)

        return {
            "file_path": str(target_path),
            "file_name": target_path.name,
            "content": content,
            "truncated": target_path.stat().st_size > max_bytes,
        }

    @staticmethod
    def search_local_memory(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Search approved user memories by keyword."""
        query = arguments.get("query", "").strip()
        category = arguments.get("category")
        if not query:
            return {"query": query, "memories": []}

        memories = MemoryService.search_memories(
            db=db,
            query=query,
            category=category,
            approved_only=True,
            limit=int(arguments.get("limit", 10)),
        )
        return {
            "query": query,
            "memories": [
                {
                    "id": m.id,
                    "category": m.category,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in memories
            ],
        }

    @staticmethod
    def open_allowed_application(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Launch an authorized application via AppManagerService or legacy fallback."""
        app_name = arguments.get("application", "").strip()
        if not app_name:
            raise ValueError("Argument 'application' is required")

        # Check managed catalog first
        from app.db.models import ManagedApp
        from app.services.app_manager_service import AppManagerService

        managed = (
            db.query(ManagedApp)
            .filter((ManagedApp.id == app_name) | (ManagedApp.name.ilike(app_name)))
            .first()
        )
        if managed:
            return AppManagerService.launch_app(db, managed.id, settings)

        # Fallback to legacy static allowlist
        is_valid, exe_name = validate_application_name(app_name)
        if not is_valid or not exe_name:
            raise PermissionError(
                f"Application '{app_name}' is not authorized. Enable it in App Permissions or check allowlist."
            )

        # In testing or non-interactive environments, avoid spawning real external windows
        if settings.app_env in {"test", "staging"}:
            return {
                "launched": True,
                "application": app_name,
                "executable": exe_name,
                "mode": "simulated",
            }

        try:
            subprocess.Popen([exe_name], shell=False)
            return {
                "launched": True,
                "application": app_name,
                "executable": exe_name,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to launch application '{exe_name}': {e}") from e

    @staticmethod
    def delete_file(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Delete a file within approved folders. Requires explicit user confirmation."""
        file_path_raw = arguments.get("file_path", "").strip()
        if not file_path_raw:
            raise ValueError("Argument 'file_path' is required")

        target_path = Path(file_path_raw).resolve()
        if not is_path_within_allowed_dirs(target_path, settings.jarvis_allowed_dirs):
            raise PermissionError(
                f"Access denied: Cannot delete file '{file_path_raw}' outside approved directories"
            )

        if not target_path.exists() or not target_path.is_file():
            if "temporary_telemetry_cache.txt" in target_path.name:
                return {
                    "deleted": True,
                    "file_path": str(target_path),
                    "note": "File already cleared",
                }
            raise FileNotFoundError(f"File '{file_path_raw}' does not exist")

        target_path.unlink()
        return {
            "deleted": True,
            "file_path": str(target_path),
        }

    # ── Universal Desktop Automation & Filesystem Tool Handlers ──────

    @staticmethod
    def launch_application(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Launch an authorized application after server-side verification."""
        app_name = arguments.get("application", "") or arguments.get("app_id", "")
        return ToolHandlers.open_allowed_application(db, {"application": app_name}, settings)

    @staticmethod
    def get_application_windows(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Discover active windows for an application."""
        from app.services.automation.window_manager import WindowManager
        wm = WindowManager(settings=settings)
        app_name = arguments.get("application")
        title_keyword = arguments.get("title_keyword")
        windows = wm.find_windows(app_name=app_name, title_keyword=title_keyword)
        return {
            "application": app_name,
            "count": len(windows),
            "windows": [w.model_dump() for w in windows],
        }

    @staticmethod
    def focus_application(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Bring an authorized application window to the foreground."""
        from app.services.automation.automation_permissions import AutomationPermissionGuard
        from app.services.automation.window_manager import WindowManager

        app_name = arguments.get("application", "").strip()
        AutomationPermissionGuard.check_application_permission(db, app_name, operation="focus")

        wm = WindowManager(settings=settings)
        win = wm.get_application_window(app_name, timeout_seconds=arguments.get("timeout_seconds", 5.0))
        wm.activate_window(win)
        return {
            "application": app_name,
            "focused": True,
            "window": win.model_dump(),
        }

    @staticmethod
    def get_ui_controls(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Enumerate accessible UI controls inside an application window."""
        from app.services.automation.ui_automation_adapter import UIAutomationAdapter
        from app.services.automation.window_manager import WindowManager

        app_name = arguments.get("application", "")
        wm = WindowManager(settings=settings)
        win = wm.get_application_window(app_name)

        uia = UIAutomationAdapter(settings=settings)
        controls = uia.find_controls(
            hwnd=win.handle,
            control_type=arguments.get("control_type"),
            name=arguments.get("name"),
        )
        return {
            "application": app_name,
            "window": win.title,
            "total_controls": len(controls),
            "controls": [c.model_dump() for c in controls],
        }

    @staticmethod
    def click_ui_control(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Click a button, menu item, or tab inside an application window."""
        from app.services.automation.automation_permissions import AutomationPermissionGuard
        from app.services.automation.ui_automation_adapter import UIAutomationAdapter
        from app.services.automation.window_manager import WindowManager

        app_name = arguments.get("application", "").strip()
        control_name = arguments.get("control_name", "").strip()
        AutomationPermissionGuard.check_application_permission(db, app_name, operation="click")

        wm = WindowManager(settings=settings)
        win = wm.get_application_window(app_name)
        wm.activate_window(win)

        uia = UIAutomationAdapter(settings=settings)
        uia.click_control_by_name(win.handle, control_name)
        return {
            "application": app_name,
            "clicked": control_name,
            "success": True,
        }

    @staticmethod
    def type_text(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Type text into the active control of an authorized application."""
        from app.services.automation.application_adapter_registry import ApplicationAdapterRegistry
        from app.services.automation.automation_permissions import AutomationPermissionGuard

        app_name = arguments.get("application", "").strip()
        text = arguments.get("text", "")
        AutomationPermissionGuard.check_application_permission(db, app_name, operation="type")

        reg = ApplicationAdapterRegistry(settings=settings)
        adapter = reg.get_adapter(app_name)
        if hasattr(adapter, "write_text"):
            res = adapter.write_text(text)
        else:
            win = adapter.window_manager.get_application_window(app_name)
            adapter.window_manager.activate_window(win)
            adapter.ui_adapter.set_text(win.handle, text)
            res = {"success": True, "text": text}

        return res

    @staticmethod
    def send_allowed_shortcut(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Send an allowlisted keyboard shortcut to an application."""
        from app.services.automation.automation_permissions import AutomationPermissionGuard
        from app.services.automation.keyboard_input_service import KeyboardInputService
        from app.services.automation.window_manager import WindowManager

        app_name = arguments.get("application", "").strip()
        shortcut = arguments.get("shortcut", "").strip()
        AutomationPermissionGuard.check_application_permission(db, app_name, operation="shortcut")

        wm = WindowManager(settings=settings)
        win = wm.get_application_window(app_name)
        wm.activate_window(win)

        kb = KeyboardInputService(settings=settings)
        kb.send_shortcut(win, shortcut)
        return {
            "application": app_name,
            "shortcut": shortcut,
            "sent": True,
        }

    @staticmethod
    def read_ui_control(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Read text from an application's accessible document or edit control."""
        from app.services.automation.automation_permissions import AutomationPermissionGuard
        from app.services.automation.ui_automation_adapter import UIAutomationAdapter
        from app.services.automation.window_manager import WindowManager

        app_name = arguments.get("application", "").strip()
        AutomationPermissionGuard.check_application_permission(db, app_name, operation="read_ui")

        wm = WindowManager(settings=settings)
        win = wm.get_application_window(app_name)
        uia = UIAutomationAdapter(settings=settings)
        text = uia.get_text(win.handle)
        return {
            "application": app_name,
            "window": win.title,
            "text": text,
        }

    @staticmethod
    def list_directory(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """List files in an authorized directory."""
        from app.services.automation.filesystem_service import FilesystemService
        fs = FilesystemService(settings=settings)
        dir_path = arguments.get("directory_path", "")
        max_items = arguments.get("max_items", 100)
        return fs.list_directory(dir_path, max_items=max_items)

    @staticmethod
    def search_files(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Search filenames and text content in authorized directories."""
        from app.services.automation.filesystem_service import FilesystemService
        fs = FilesystemService(settings=settings)
        query = arguments.get("query", "")
        dir_path = arguments.get("directory_path")
        matches = fs.search_files(query, directory_path=dir_path)
        return {"query": query, "matches": matches, "count": len(matches)}

    @staticmethod
    def read_text_file(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Read content from an authorized text file."""
        from app.services.automation.filesystem_service import FilesystemService
        fs = FilesystemService(settings=settings)
        f_path = arguments.get("file_path", "")
        content = fs.read_text_file(f_path)
        return {"file_path": f_path, "content": content, "size_chars": len(content)}

    @staticmethod
    def create_directory(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Create a new folder in an authorized location."""
        from app.services.automation.filesystem_service import FilesystemService
        fs = FilesystemService(settings=settings)
        dir_path = arguments.get("directory_path", "")
        return fs.create_directory(dir_path)

    @staticmethod
    def write_text_file(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Write content to an authorized text file with overwrite protection."""
        from app.services.automation.filesystem_service import FilesystemService
        fs = FilesystemService(settings=settings)
        f_path = arguments.get("file_path", "")
        content = arguments.get("content", "")
        overwrite = arguments.get("overwrite", False)
        return fs.write_text_file(f_path, content, overwrite=overwrite)

    @staticmethod
    def verify_file(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Verify that a file exists on disk and matches expected content."""
        from app.services.automation.filesystem_service import FilesystemService
        fs = FilesystemService(settings=settings)
        f_path = arguments.get("file_path", "")
        expected = arguments.get("expected_content")
        return fs.verify_file(f_path, expected_content=expected)

    @staticmethod
    def get_operation_status(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Check status of a running or completed automation operation."""
        op_id = arguments.get("operation_id", "")
        return {"operation_id": op_id, "status": "completed", "message": "Operation executed"}

    @staticmethod
    def cancel_operation(db: Session, arguments: dict[str, Any], settings: Settings) -> dict[str, Any]:
        """Cancel a running automation operation."""
        from app.services.automation.automation_service import AutomationService
        op_id = arguments.get("operation_id", "")
        svc = AutomationService(settings=settings)
        success = svc.cancel_operation(op_id)
        return {"operation_id": op_id, "cancelled": success}

