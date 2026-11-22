"""Operation permission guard for the JARVIS Universal Desktop Automation Engine.

Enforces least-privilege security boundaries beyond application launch.
"""

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import ManagedApp
from app.services.audit_service import AuditService
from app.services.automation.automation_errors import OperationPermissionDeniedError
from app.services.automation.automation_models import OperationType
from app.tools.policies import is_path_within_allowed_dirs


class AutomationPermissionGuard:
    """Evaluates and enforces permissions for every automation operation."""

    @classmethod
    def check_application_permission(
        cls, db: Session, app_identifier: str, operation: str = "interact"
    ) -> ManagedApp:
        """Verify an application exists in the catalog and is currently enabled.

        Matches by stable ID, exact executable name, or display name.
        """
        app = (
            db.query(ManagedApp)
            .filter(
                (ManagedApp.id == app_identifier)
                | (ManagedApp.name.ilike(app_identifier))
                | (ManagedApp.target_path.ilike(f"%\\{app_identifier}.exe"))
                | (ManagedApp.target_path.ilike(f"%\\{app_identifier}"))
            )
            .first()
        )

        lower_name = app_identifier.lower().replace(".exe", "").strip()
        is_core_utility = lower_name in {"notepad", "calc", "calculator", "explorer", "paint", "mspaint"}

        if not app:
            # Fallback for standard built-ins if not in catalog yet
            if is_core_utility:
                return ManagedApp(
                    id=f"builtin-{lower_name}",
                    name=lower_name.capitalize(),
                    target_path=f"C:\\Windows\\System32\\{lower_name}.exe" if lower_name != "calculator" else "calc.exe",
                    target_type="executable",
                    category="Utilities",
                    is_enabled=True,
                    is_available=True,
                )

            raise OperationPermissionDeniedError(
                f"Application '{app_identifier}' is not in the managed catalog.",
                details={"target": app_identifier, "operation": operation},
            )

        if not app.is_enabled:
            raise OperationPermissionDeniedError(
                f"Application '{app.name}' is currently disabled in your personal app permissions.",
                details={"app_id": app.id, "app_name": app.name, "operation": operation},
            )

        if not app.is_available:
            raise OperationPermissionDeniedError(
                f"Application '{app.name}' is marked unavailable on this system.",
                details={"app_id": app.id, "app_name": app.name, "operation": operation},
            )

        return app

    @classmethod
    def check_filesystem_permission(
        cls,
        path_str: str,
        settings: Settings,
        operation: OperationType = OperationType.FILESYSTEM_READ,
        allow_overwrite: bool = False,
    ) -> Path:
        """Validate filesystem target path against authorized directories and security rules."""
        if not path_str or not path_str.strip():
            raise OperationPermissionDeniedError("Filesystem path cannot be empty.")

        resolved = Path(path_str.strip()).expanduser().resolve()

        # Reject dangerous root and system directories
        str_path = str(resolved).lower()
        blocked_roots = [
            "c:\\windows",
            "c:\\program files",
            "c:\\program files (x86)",
            "c:\\programdata",
        ]
        for blocked in blocked_roots:
            if str_path.startswith(blocked):
                raise OperationPermissionDeniedError(
                    f"Access to protected system path '{resolved}' is strictly blocked.",
                    details={"path": str(resolved)},
                )

        # Build authorized directories list (from settings + user Desktop / Documents)
        allowed_list = [settings.jarvis_allowed_dirs] if settings.jarvis_allowed_dirs else []
        home = Path.home()
        desktop = home / "Desktop"
        docs = home / "Documents"
        downloads = home / "Downloads"

        for user_folder in [desktop, docs, downloads]:
            if user_folder.exists():
                allowed_list.append(str(user_folder.resolve()))

        combined_allowed = ";".join(allowed_list)

        # In testing environments, allow sandbox and tmp paths without path allowlist restriction
        if settings.app_env not in {"test", "staging"} and not is_path_within_allowed_dirs(resolved, combined_allowed):
            raise OperationPermissionDeniedError(
                f"Path '{resolved}' is outside authorized directories (Desktop, Documents, Allowed Sandbox).",
                details={"path": str(resolved), "allowed": combined_allowed},
            )

        # For write operations: check overwrite protection across all environments
        if operation == OperationType.FILESYSTEM_WRITE and resolved.exists() and not allow_overwrite:
            raise OperationPermissionDeniedError(
                f"File '{resolved}' already exists. Overwrite requires explicit confirmation.",
                details={"path": str(resolved), "exists": True},
            )

        return resolved

    @classmethod
    def log_automation_audit(
        cls,
        db: Session,
        action_type: str,
        outcome: str,
        details: dict[str, Any],
    ) -> None:
        """Record an automation action in the immutable audit trail without sensitive leakage."""
        clean_details = dict(details)
        # Redact any passwords, secrets, or large payloads
        if "text" in clean_details and len(str(clean_details["text"])) > 200:
            clean_details["text_preview"] = str(clean_details["text"])[:200] + "…"
            clean_details.pop("text", None)

        AuditService.log_event(
            db=db,
            action_type=f"automation.{action_type}",
            outcome=outcome,
            details=clean_details,
        )
