"""Secure filesystem operation layer enforcing sandboxing, canonicalization, and overwrite protection."""

import logging
import os
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.services.automation.automation_errors import (
    OperationPermissionDeniedError,
    VerificationFailedError,
)
from app.services.automation.automation_models import OperationType
from app.services.automation.automation_permissions import AutomationPermissionGuard

logger = logging.getLogger(__name__)

# Sensitive files that should never be read or overwritten by automation
BLOCKED_SENSITIVE_FILES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "sam",
    "system",
    "security",
    "credentials",
    "master.key",
    "passwords.txt",
}

MAX_FILE_READ_BYTES = 5 * 1024 * 1024  # 5 MB


class FilesystemService:
    """Provides secure, validated filesystem operations for JARVIS."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def list_directory(self, directory_path: str, max_items: int = 100) -> dict[str, Any]:
        """List files and subdirectories in an authorized directory."""
        target_dir = AutomationPermissionGuard.check_filesystem_permission(
            directory_path, self.settings, operation=OperationType.FILESYSTEM_READ
        )

        if not target_dir.exists():
            raise FileNotFoundError(f"Directory '{target_dir}' does not exist.")
        if not target_dir.is_dir():
            raise NotADirectoryError(f"Path '{target_dir}' is not a directory.")

        entries: list[dict[str, Any]] = []
        try:
            for entry in list(target_dir.iterdir())[:max_items]:
                entries.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size_bytes": entry.stat().st_size if entry.is_file() else 0,
                    "modified_at": entry.stat().st_mtime,
                })
        except PermissionError as e:
            raise OperationPermissionDeniedError(f"Access denied reading directory '{target_dir}': {e}") from e

        return {
            "directory": str(target_dir),
            "total_items": len(entries),
            "items": entries,
        }

    def search_files(self, query: str, directory_path: str | None = None, max_results: int = 25) -> list[dict[str, Any]]:
        """Search filenames and text content for matching keywords in authorized directories."""
        base_dir_str = directory_path or self.settings.jarvis_allowed_dirs or str(Path.home() / "Desktop")
        target_dir = AutomationPermissionGuard.check_filesystem_permission(
            base_dir_str, self.settings, operation=OperationType.FILESYSTEM_READ
        )

        matches: list[dict[str, Any]] = []
        clean_q = query.lower().strip()

        for root, _dirs, files in os.walk(target_dir):
            for f in files:
                if clean_q in f.lower():
                    full_p = Path(root) / f
                    matches.append({
                        "filename": f,
                        "path": str(full_p),
                        "size_bytes": full_p.stat().st_size,
                    })
                    if len(matches) >= max_results:
                        return matches

        return matches

    def read_text_file(self, file_path: str, max_bytes: int = MAX_FILE_READ_BYTES) -> str:
        """Read text from an authorized file with sensitive file protection."""
        target_file = AutomationPermissionGuard.check_filesystem_permission(
            file_path, self.settings, operation=OperationType.FILESYSTEM_READ
        )

        if target_file.name.lower() in BLOCKED_SENSITIVE_FILES:
            raise OperationPermissionDeniedError(
                f"Access denied: reading sensitive credential file '{target_file.name}' is strictly blocked."
            )

        if not target_file.exists():
            raise FileNotFoundError(f"File '{target_file}' does not exist.")
        if not target_file.is_file():
            raise ValueError(f"Path '{target_file}' is not a regular file.")

        size = target_file.stat().st_size
        if size > max_bytes:
            raise ValueError(f"File size ({size} bytes) exceeds safety limit ({max_bytes} bytes).")

        try:
            return target_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise OSError(f"Failed to read file '{target_file}': {e}") from e

    def create_directory(self, directory_path: str) -> dict[str, Any]:
        """Create a new directory within authorized boundaries."""
        target_dir = AutomationPermissionGuard.check_filesystem_permission(
            directory_path, self.settings, operation=OperationType.FILESYSTEM_WRITE
        )

        target_dir.mkdir(parents=True, exist_ok=True)
        return {
            "created": True,
            "path": str(target_dir),
        }

    def write_text_file(
        self,
        file_path: str,
        content: str,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Write text to an authorized file destination with overwrite protection."""
        target_file = AutomationPermissionGuard.check_filesystem_permission(
            file_path, self.settings, operation=OperationType.FILESYSTEM_WRITE, allow_overwrite=overwrite
        )

        if target_file.name.lower() in BLOCKED_SENSITIVE_FILES:
            raise OperationPermissionDeniedError(
                f"Access denied: writing to sensitive file '{target_file.name}' is strictly blocked."
            )

        # Create parent directories if needed
        target_file.parent.mkdir(parents=True, exist_ok=True)

        target_file.write_text(content, encoding="utf-8")
        size = target_file.stat().st_size

        return {
            "written": True,
            "path": str(target_file),
            "size_bytes": size,
            "verified": target_file.exists() and size > 0,
        }

    def verify_file(self, file_path: str, expected_content: str | None = None) -> dict[str, Any]:
        """Verify that a file exists on disk and optionally matches expected content."""
        target_file = AutomationPermissionGuard.check_filesystem_permission(
            file_path, self.settings, operation=OperationType.FILESYSTEM_READ
        )

        if not target_file.exists():
            raise VerificationFailedError(f"Verification failed: file '{target_file}' does not exist.")

        content = target_file.read_text(encoding="utf-8", errors="replace")
        if expected_content and expected_content.strip() not in content:
            raise VerificationFailedError(
                f"Verification failed: expected content was not found in '{target_file}'.",
                details={"expected": expected_content, "snippet": content[:150]},
            )

        return {
            "verified": True,
            "path": str(target_file),
            "size_bytes": target_file.stat().st_size,
            "content_matched": bool(expected_content),
        }
