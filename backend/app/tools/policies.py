"""Tool authorization policies, scope checking, and command validation."""

import os
from enum import Enum
from pathlib import Path


class ToolPolicy(str, Enum):
    """Execution policy classifications for tools."""

    AUTOMATIC = "automatic"
    EXPLICIT_CONFIRMATION = "explicit_confirmation"
    BLOCKED = "blocked"


# Set of applications approved for opening on Windows
ALLOWED_APPLICATIONS = {
    "notepad": "notepad.exe",
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
}

# Blocked command terms that must never be executed
BLOCKED_SHELL_PATTERNS = {
    "powershell",
    "cmd.exe",
    "bash",
    "sh",
    "curl",
    "wget",
    "rmdir",
    "del",
    "format",
    "reg",
    "netsh",
    "shutdown",
    "takeown",
    "icacls",
}


def is_path_within_allowed_dirs(
    target_path: str | Path,
    allowed_dirs: list[str] | str | None,
) -> bool:
    """Verify that a target file or folder strictly resides inside an approved directory.

    Rejects directory traversal (e.g. '..'), symlinks outside boundaries, and arbitrary absolute paths.
    """
    raw_paths: list[str] = []
    if allowed_dirs:
        if isinstance(allowed_dirs, str):
            raw_paths = [p.strip() for p in allowed_dirs.split(",") if p.strip()]
        else:
            raw_paths = [str(p).strip() for p in allowed_dirs if str(p).strip()]

    if not raw_paths:
        try:
            from app.core.config import get_settings

            raw_paths = get_settings().get_allowed_directories()
        except (ImportError, AttributeError, ValueError, OSError):
            raw_paths = []

    valid_roots: list[Path] = []
    for p in raw_paths:
        resolved = Path(p).resolve()
        if resolved.exists() and resolved.is_dir():
            valid_roots.append(resolved)

    if not valid_roots:
        return False

    try:
        resolved_target = Path(target_path).resolve()
        return any(resolved_target.is_relative_to(root) for root in valid_roots)
    except (ValueError, OSError):
        return False


def validate_application_name(app_name: str) -> tuple[bool, str | None]:
    """Validate whether an application is in the safe Windows application allowlist."""
    normalized = app_name.strip().lower()
    # Strip .exe suffix if provided
    normalized = normalized.removesuffix(".exe")

    if normalized in ALLOWED_APPLICATIONS:
        return True, ALLOWED_APPLICATIONS[normalized]
    return False, None


def is_command_blocked(command_str: str) -> bool:
    """Check if command contains prohibited shell or administrative execution terms."""
    clean = command_str.strip().lower()
    for token in clean.split():
        base_token = os.path.basename(token)
        if base_token in BLOCKED_SHELL_PATTERNS or token in BLOCKED_SHELL_PATTERNS:
            return True
    return False
