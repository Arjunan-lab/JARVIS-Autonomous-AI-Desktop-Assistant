"""Application manager service for JARVIS.

Manages catalog persistence, permission policy enforcement, safe execution,
and immutable audit logging.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import AuditEvent, ManagedApp, utc_now
from app.services.app_discovery_service import DiscoveredApp, validate_launch_target

logger = logging.getLogger("jarvis.app_manager")


class AppManagerService:
    """Service handling application catalog permissions, updates, and secure launches."""

    @staticmethod
    def sync_discovery(db: Session, discovered_apps: list[DiscoveredApp]) -> tuple[int, int, int]:
        """Synchronize discovered applications into the persistent database.

        Preserves existing permissions (`is_enabled`) for previously discovered apps.
        Defaults newly discovered applications to disabled (`is_enabled = False`).
        Updates availability status.
        Returns (added_count, updated_count, total_count).
        """
        existing_apps = {app.id: app for app in db.scalars(select(ManagedApp)).all()}
        discovered_ids = set()

        added_count = 0
        updated_count = 0

        for disc in discovered_apps:
            discovered_ids.add(disc.id)
            if disc.id in existing_apps:
                # Existing application: preserve is_enabled!
                existing = existing_apps[disc.id]
                existing.name = disc.name
                existing.target_path = disc.target_path
                existing.target_type = disc.target_type
                existing.category = disc.category
                existing.icon_path = disc.icon_path or existing.icon_path
                existing.is_available = disc.is_available
                existing.updated_at = utc_now()
                updated_count += 1
            else:
                # Newly discovered application: default-deny (is_enabled = False)
                new_app = ManagedApp(
                    id=disc.id,
                    name=disc.name,
                    target_path=disc.target_path,
                    target_type=disc.target_type,
                    category=disc.category,
                    icon_path=disc.icon_path,
                    is_enabled=False,  # Strict default-deny policy
                    is_available=disc.is_available,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                db.add(new_app)
                added_count += 1

        # Mark applications in DB not found in current scan as unavailable (preserve permissions)
        for app_id, existing in existing_apps.items():
            if app_id not in discovered_ids and existing.is_available:
                existing.is_available = False
                existing.updated_at = utc_now()
                updated_count += 1

        db.commit()
        total_count = db.scalar(select(func.count(ManagedApp.id))) or 0
        logger.info(
            "Application catalog synchronized: %d added, %d updated, %d total.",
            added_count,
            updated_count,
            total_count,
        )
        return added_count, updated_count, total_count

    @staticmethod
    def list_apps(
        db: Session,
        search: str | None = None,
        category: str | None = None,
        enabled_only: bool = False,
    ) -> tuple[list[ManagedApp], int, int, int, list[str]]:
        """List applications with optional search and category filters, plus summary metrics."""
        query = select(ManagedApp)

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.where(
                func.lower(ManagedApp.name).like(term)
                | func.lower(ManagedApp.category).like(term)
            )

        if category and category.strip() and category.strip().lower() != "all":
            query = query.where(func.lower(ManagedApp.category) == category.strip().lower())

        if enabled_only:
            query = query.where(ManagedApp.is_enabled.is_(True))

        query = query.order_by(ManagedApp.name.asc())
        applications = list(db.scalars(query).all())

        # Aggregate metrics across the entire catalog
        total_count = db.scalar(select(func.count(ManagedApp.id))) or 0
        enabled_count = (
            db.scalar(select(func.count(ManagedApp.id)).where(ManagedApp.is_enabled.is_(True)))
            or 0
        )
        disabled_count = (
            db.scalar(select(func.count(ManagedApp.id)).where(ManagedApp.is_enabled.is_(False)))
            or 0
        )

        categories_raw = db.scalars(
            select(ManagedApp.category).distinct().order_by(ManagedApp.category.asc())
        ).all()
        categories = sorted({c for c in categories_raw if c})

        return applications, total_count, enabled_count, disabled_count, categories

    @staticmethod
    def get_app_by_id(db: Session, app_id: str) -> ManagedApp | None:
        """Retrieve an application from the trusted catalog by its stable ID."""
        return db.scalar(select(ManagedApp).where(ManagedApp.id == app_id))

    @staticmethod
    def update_permission(db: Session, app_id: str, is_enabled: bool) -> ManagedApp:
        """Update an application's execution permission toggle and log the audit event."""
        app = AppManagerService.get_app_by_id(db, app_id)
        if not app:
            raise KeyError(f"Application with ID '{app_id}' not found in catalog")

        old_val = app.is_enabled
        app.is_enabled = is_enabled
        app.updated_at = utc_now()

        # Audit log permission change
        audit_event = AuditEvent(
            action_type="update_app_permission",
            outcome="success",
            details_json=json.dumps({
                "app_id": app.id,
                "name": app.name,
                "previous_state": old_val,
                "new_state": is_enabled,
            }),
            timestamp=utc_now(),
        )
        db.add(audit_event)
        db.commit()
        db.refresh(app)
        logger.info("Application '%s' (%s) permission updated: %s -> %s", app.name, app.id, old_val, is_enabled)
        return app

    @staticmethod
    def launch_app(db: Session, app_id: str, settings: Settings) -> dict[str, Any]:
        """Launch an authorized application with independent server-side enforcement.

        Enforces:
        - Must exist in catalog.
        - Must have `is_enabled == True`.
        - Must have `is_available == True`.
        - Target path must satisfy strict security validation.
        - Never trust model-provided executable paths or frontend state.
        - Avoid shell=True.
        - Record allowed, denied, failed, and successful launch attempts in audit log.
        """
        app = AppManagerService.get_app_by_id(db, app_id)

        # 1. Existence check
        if not app:
            audit_event = AuditEvent(
                action_type="launch_application",
                outcome="denied",
                details_json=json.dumps({
                    "app_id": app_id,
                    "reason": "Application not in trusted catalog",
                }),
                timestamp=utc_now(),
            )
            db.add(audit_event)
            db.commit()
            logger.warning("Launch attempt for unknown app_id: '%s'", app_id)
            raise KeyError(f"Application '{app_id}' is not in the trusted catalog")

        # 2. Permission check (Independent server-side enforcement)
        if not app.is_enabled:
            audit_event = AuditEvent(
                action_type="launch_application",
                outcome="denied",
                details_json=json.dumps({
                    "app_id": app.id,
                    "name": app.name,
                    "reason": "Application access disabled by policy",
                }),
                timestamp=utc_now(),
            )
            db.add(audit_event)
            db.commit()
            logger.warning("Launch denied for disabled application '%s' (%s)", app.name, app.id)
            raise PermissionError(
                f"Access denied: Execution for '{app.name}' is disabled in App Access Manager"
            )

        # 3. Availability check
        if not app.is_available:
            audit_event = AuditEvent(
                action_type="launch_application",
                outcome="failed",
                details_json=json.dumps({
                    "app_id": app.id,
                    "name": app.name,
                    "reason": "Target executable unavailable on disk",
                }),
                timestamp=utc_now(),
            )
            db.add(audit_event)
            db.commit()
            logger.warning("Launch failed: target for '%s' is unavailable on disk", app.name)
            raise FileNotFoundError(
                f"Application '{app.name}' is unavailable on disk"
            )

        # 4. Target security validation
        is_valid, reason = validate_launch_target(app.target_path, app.target_type)
        if not is_valid:
            audit_event = AuditEvent(
                action_type="launch_application",
                outcome="failed",
                details_json=json.dumps({
                    "app_id": app.id,
                    "name": app.name,
                    "reason": reason,
                }),
                timestamp=utc_now(),
            )
            db.add(audit_event)
            db.commit()
            logger.error("Launch security validation failed for '%s': %s", app.name, reason)
            raise ValueError(f"Application target failed security validation: {reason}")

        # 5. Process execution without shell=True
        # In test / staging environments, avoid opening real windows
        if settings.app_env in {"test", "staging"}:
            app.last_launched_at = utc_now()
            audit_event = AuditEvent(
                action_type="launch_application",
                outcome="success",
                details_json=json.dumps({
                    "app_id": app.id,
                    "name": app.name,
                    "mode": "simulated",
                }),
                timestamp=utc_now(),
            )
            db.add(audit_event)
            db.commit()
            logger.info("Simulated launch for '%s' (test mode)", app.name)
            return {
                "launched": True,
                "app_id": app.id,
                "name": app.name,
                "mode": "simulated",
            }

        try:
            clean_name = app.name.lower().strip()
            # Standard Windows execution aliases for core tools
            if clean_name == "notepad" or "notepad.exe" in app.target_path.lower():
                subprocess.Popen(["notepad.exe"], shell=False)
            elif clean_name in {"calculator", "calc"} or "calc.exe" in app.target_path.lower():
                if app.target_type == "packaged_app":
                    subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app.target_path}"], shell=False)
                else:
                    subprocess.Popen(["calc.exe"], shell=False)
            elif app.target_type == "packaged_app":
                # Launch packaged UWP app via explorer.exe shell:AppsFolder without shell=True
                subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app.target_path}"], shell=False)
            else:
                # Direct executable launch without shell=True
                resolved_target = str(Path(app.target_path).resolve())
                try:
                    subprocess.Popen([resolved_target], shell=False)
                except OSError as launch_err:
                    logger.debug("Direct launch failed, attempting alias '%s.exe': %s", clean_name, launch_err)
                    # Fallback to execution alias if available
                    subprocess.Popen([f"{clean_name}.exe"], shell=False)

            app.last_launched_at = utc_now()
            audit_event = AuditEvent(
                action_type="launch_application",
                outcome="success",
                details_json=json.dumps({
                    "app_id": app.id,
                    "name": app.name,
                    "target": app.target_path,
                }),
                timestamp=utc_now(),
            )
            db.add(audit_event)
            db.commit()
            logger.info("Successfully launched application '%s' (%s)", app.name, app.id)
            return {
                "launched": True,
                "app_id": app.id,
                "name": app.name,
            }
        except Exception as exc:
            audit_event = AuditEvent(
                action_type="launch_application",
                outcome="failed",
                details_json=json.dumps({
                    "app_id": app.id,
                    "name": app.name,
                    "error": str(exc),
                }),
                timestamp=utc_now(),
            )
            db.add(audit_event)
            db.commit()
            logger.error("Failed launching process for '%s': %s", app.name, exc)
            raise RuntimeError(f"Failed to launch application process '{app.name}': {exc}") from exc
