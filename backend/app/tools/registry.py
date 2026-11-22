"""Typed tool registry and schema definition for assistant actions."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.tools.handlers import ToolHandlers
from app.tools.policies import ToolPolicy


@dataclass
class ToolDefinition:
    """Specification of an assistant tool including parameters schema and policy."""

    name: str
    description: str
    parameters: dict[str, Any]
    policy: ToolPolicy
    handler: Callable[[Session, dict[str, Any], Settings], dict[str, Any]]


class ToolRegistry:
    """Central registry of all allowlisted JARVIS tools and action policies."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def register(self, tool: ToolDefinition) -> None:
        """Register a new tool definition."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        """Retrieve a tool definition by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_realtime_tools(self) -> list[dict[str, Any]]:
        """Return tool schemas formatted for OpenAI Realtime session configuration."""
        return [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
            if tool.policy != ToolPolicy.BLOCKED
        ]

    def validate_tool_call(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """Validate whether a requested tool exists and satisfies required parameter types."""
        tool = self.get(tool_name)
        if not tool:
            return False, f"Tool '{tool_name}' is not in the allowlist"

        required_props = tool.parameters.get("required", [])
        for req in required_props:
            if req not in arguments:
                return False, f"Missing required parameter '{req}' for tool '{tool_name}'"

        return True, None

    def _register_default_tools(self) -> None:
        """Register the baseline set of blueprint-specified tools."""
        self.register(
            ToolDefinition(
                name="create_task",
                description="Create a new task or reminder for the user.",
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Title of the task"},
                        "description": {"type": "string", "description": "Optional details"},
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Task priority",
                        },
                        "due_date": {
                            "type": "string",
                            "description": "ISO 8601 formatted due date timestamp",
                        },
                    },
                    "required": ["title"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.create_task,
            )
        )

        self.register(
            ToolDefinition(
                name="list_tasks",
                description="List the user's current tasks and to-do items.",
                parameters={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pending", "completed", "cancelled"],
                            "description": "Filter by task status",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Filter by priority",
                        },
                    },
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.list_tasks,
            )
        )

        self.register(
            ToolDefinition(
                name="complete_task",
                description="Mark a specific task as completed.",
                parameters={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "The unique ID of the task to complete"},
                    },
                    "required": ["task_id"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.complete_task,
            )
        )

        self.register(
            ToolDefinition(
                name="search_allowed_files",
                description="Search authorized local folders for matching keywords and text snippets.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keyword to search for"},
                        "max_results": {"type": "integer", "description": "Maximum snippets to return"},
                    },
                    "required": ["query"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.search_allowed_files,
            )
        )

        self.register(
            ToolDefinition(
                name="read_allowed_text_file",
                description="Read content from an approved text file in the user's allowed folders.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Absolute or relative file path to read"},
                    },
                    "required": ["file_path"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.read_allowed_text_file,
            )
        )

        self.register(
            ToolDefinition(
                name="search_local_memory",
                description="Search explicitly approved memories and user preferences.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keyword query to search for"},
                        "category": {
                            "type": "string",
                            "enum": ["preference", "project", "knowledge", "task_history"],
                            "description": "Optional category filter",
                        },
                    },
                    "required": ["query"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.search_local_memory,
            )
        )

        self.register(
            ToolDefinition(
                name="open_allowed_application",
                description="Open an allowlisted Windows desktop utility (notepad, calc, explorer).",
                parameters={
                    "type": "object",
                    "properties": {
                        "application": {
                            "type": "string",
                            "enum": ["notepad", "calc", "explorer"],
                            "description": "Name of the application to open",
                        },
                    },
                    "required": ["application"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.open_allowed_application,
            )
        )

        self.register(
            ToolDefinition(
                name="delete_file",
                description="Delete a file within approved folders. Requires explicit user confirmation.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path of file to delete"},
                    },
                    "required": ["file_path"],
                },
                policy=ToolPolicy.EXPLICIT_CONFIRMATION,
                handler=ToolHandlers.delete_file,
            )
        )

        self.register(
            ToolDefinition(
                name="launch_application",
                description="Launch an authorized application after server-side verification.",
                parameters={
                    "type": "object",
                    "properties": {
                        "application": {"type": "string", "description": "Name or ID of application to launch"},
                    },
                    "required": ["application"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.launch_application,
            )
        )

        self.register(
            ToolDefinition(
                name="get_application_windows",
                description="Discover active windows for an application.",
                parameters={
                    "type": "object",
                    "properties": {
                        "application": {"type": "string", "description": "Name of application (e.g. notepad)"},
                        "title_keyword": {"type": "string", "description": "Optional title keyword filter"},
                    },
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.get_application_windows,
            )
        )

        self.register(
            ToolDefinition(
                name="focus_application",
                description="Bring an authorized application window to the foreground.",
                parameters={
                    "type": "object",
                    "properties": {
                        "application": {"type": "string", "description": "Name of application to activate"},
                        "timeout_seconds": {"type": "number", "description": "Wait timeout in seconds"},
                    },
                    "required": ["application"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.focus_application,
            )
        )

        self.register(
            ToolDefinition(
                name="get_ui_controls",
                description="Enumerate accessible UI controls inside an application window.",
                parameters={
                    "type": "object",
                    "properties": {
                        "application": {"type": "string", "description": "Name of application"},
                        "control_type": {"type": "string", "description": "Optional control type filter (Edit, Button, etc.)"},
                        "name": {"type": "string", "description": "Optional control name filter"},
                    },
                    "required": ["application"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.get_ui_controls,
            )
        )

        self.register(
            ToolDefinition(
                name="click_ui_control",
                description="Click a button, menu item, or tab inside an application window.",
                parameters={
                    "type": "object",
                    "properties": {
                        "application": {"type": "string", "description": "Name of application"},
                        "control_name": {"type": "string", "description": "Name of control to click"},
                    },
                    "required": ["application", "control_name"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.click_ui_control,
            )
        )

        self.register(
            ToolDefinition(
                name="type_text",
                description="Type text into the active control of an authorized application.",
                parameters={
                    "type": "object",
                    "properties": {
                        "application": {"type": "string", "description": "Name of application"},
                        "text": {"type": "string", "description": "Text content to enter"},
                    },
                    "required": ["application", "text"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.type_text,
            )
        )

        self.register(
            ToolDefinition(
                name="send_allowed_shortcut",
                description="Send an allowlisted keyboard shortcut to an application (e.g. ^s, ^a, ^c, ^v, {F5}, {ENTER}).",
                parameters={
                    "type": "object",
                    "properties": {
                        "application": {"type": "string", "description": "Name of application"},
                        "shortcut": {"type": "string", "description": "Allowed shortcut key combination"},
                    },
                    "required": ["application", "shortcut"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.send_allowed_shortcut,
            )
        )

        self.register(
            ToolDefinition(
                name="read_ui_control",
                description="Read text from an application's accessible document or edit control.",
                parameters={
                    "type": "object",
                    "properties": {
                        "application": {"type": "string", "description": "Name of application"},
                    },
                    "required": ["application"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.read_ui_control,
            )
        )

        self.register(
            ToolDefinition(
                name="list_directory",
                description="List files and folders in an authorized directory.",
                parameters={
                    "type": "object",
                    "properties": {
                        "directory_path": {"type": "string", "description": "Path to directory"},
                        "max_items": {"type": "integer", "description": "Maximum items to return"},
                    },
                    "required": ["directory_path"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.list_directory,
            )
        )

        self.register(
            ToolDefinition(
                name="search_files",
                description="Search filenames and text content in authorized directories.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keyword to search for"},
                        "directory_path": {"type": "string", "description": "Optional search root"},
                    },
                    "required": ["query"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.search_files,
            )
        )

        self.register(
            ToolDefinition(
                name="read_text_file",
                description="Read content from an authorized text file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file to read"},
                    },
                    "required": ["file_path"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.read_text_file,
            )
        )

        self.register(
            ToolDefinition(
                name="create_directory",
                description="Create a new folder in an authorized location.",
                parameters={
                    "type": "object",
                    "properties": {
                        "directory_path": {"type": "string", "description": "Path of directory to create"},
                    },
                    "required": ["directory_path"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.create_directory,
            )
        )

        self.register(
            ToolDefinition(
                name="write_text_file",
                description="Write content to an authorized text file with overwrite protection.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Destination file path"},
                        "content": {"type": "string", "description": "Text content to write"},
                        "overwrite": {"type": "boolean", "description": "Allow overwrite if file exists"},
                    },
                    "required": ["file_path", "content"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.write_text_file,
            )
        )

        self.register(
            ToolDefinition(
                name="verify_file",
                description="Verify that a file exists on disk and matches expected content.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "File path to verify"},
                        "expected_content": {"type": "string", "description": "Optional expected content snippet"},
                    },
                    "required": ["file_path"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.verify_file,
            )
        )

        self.register(
            ToolDefinition(
                name="get_operation_status",
                description="Check status of a running or completed automation operation.",
                parameters={
                    "type": "object",
                    "properties": {
                        "operation_id": {"type": "string", "description": "ID of operation to query"},
                    },
                    "required": ["operation_id"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.get_operation_status,
            )
        )

        self.register(
            ToolDefinition(
                name="cancel_operation",
                description="Cancel a running automation operation.",
                parameters={
                    "type": "object",
                    "properties": {
                        "operation_id": {"type": "string", "description": "ID of operation to cancel"},
                    },
                    "required": ["operation_id"],
                },
                policy=ToolPolicy.AUTOMATIC,
                handler=ToolHandlers.cancel_operation,
            )
        )


# Global singleton tool registry
default_tool_registry = ToolRegistry()
