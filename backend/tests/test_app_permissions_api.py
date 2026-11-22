"""Integration tests for JARVIS Personal App Access Manager API endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.models import AuditEvent, ManagedApp
from app.db.session import Base, get_db
from app.main import create_app
from app.services.app_discovery_service import DiscoveredApp
from app.services.app_manager_service import AppManagerService


@pytest.fixture
def app_test_env():
    """Create test client with isolated SQLite database and overridden get_db dependency."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    settings = Settings(
        app_name="JARVIS-TEST",
        app_env="test",
        host="127.0.0.1",
        port=8000,
        openai_api_key="",
        openai_realtime_model="gpt-realtime-mini",
        openai_realtime_voice="marin",
        database_url="sqlite:///:memory:",
        jarvis_max_daily_api_budget_usd=1.00,
        frontend_origin="http://localhost:5173",
        log_level="DEBUG",
    )
    test_app = create_app(settings=settings)
    test_app.dependency_overrides[get_db] = override_get_db

    session = TestingSessionLocal()
    with TestClient(test_app) as client:
        yield client, session

    session.close()
    test_app.dependency_overrides.clear()


@pytest.fixture
def client(app_test_env) -> TestClient:
    return app_test_env[0]


@pytest.fixture
def db_session(app_test_env) -> Session:
    return app_test_env[1]


@pytest.fixture
def seed_managed_apps(db_session: Session, tmp_path: Path) -> list[ManagedApp]:
    """Seed test application entries in the database."""
    # Create real dummy executable file
    calc_exe = tmp_path / "test_calc.exe"
    calc_exe.write_text("dummy binary")

    chrome_exe = tmp_path / "test_chrome.exe"
    chrome_exe.write_text("dummy binary")

    app1 = ManagedApp(
        id="app-calc-001",
        name="Calculator",
        target_path=str(calc_exe.resolve()),
        target_type="executable",
        category="Productivity",
        is_enabled=False,  # Default deny
        is_available=True,
    )
    app2 = ManagedApp(
        id="app-chrome-002",
        name="Google Chrome",
        target_path=str(chrome_exe.resolve()),
        target_type="executable",
        category="Browsers",
        is_enabled=True,  # User explicitly enabled
        is_available=True,
    )
    app3 = ManagedApp(
        id="app-ghost-003",
        name="Uninstalled App",
        target_path=r"C:\Ghost\deleted.exe",
        target_type="executable",
        category="Utilities",
        is_enabled=True,
        is_available=False,  # Unavailable on disk
    )
    db_session.add_all([app1, app2, app3])
    db_session.commit()
    return [app1, app2, app3]


class TestListApplicationsAPI:
    """Tests for GET /api/apps."""

    def test_list_applications_empty(self, client: TestClient):
        response = client.get("/api/apps")
        assert response.status_code == 200
        data = response.json()
        assert "applications" in data
        assert data["total_count"] == 0
        assert data["enabled_count"] == 0

    def test_list_applications_with_data(self, client: TestClient, seed_managed_apps: list[ManagedApp]):
        response = client.get("/api/apps")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert data["enabled_count"] == 2
        assert data["disabled_count"] == 1
        assert "Browsers" in data["categories"]
        assert "Productivity" in data["categories"]

    def test_search_applications(self, client: TestClient, seed_managed_apps: list[ManagedApp]):
        response = client.get("/api/apps", params={"search": "chrome"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["applications"]) == 1
        assert data["applications"][0]["name"] == "Google Chrome"

    def test_filter_by_category(self, client: TestClient, seed_managed_apps: list[ManagedApp]):
        response = client.get("/api/apps", params={"category": "Browsers"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["applications"]) == 1
        assert data["applications"][0]["category"] == "Browsers"

    def test_filter_enabled_only(self, client: TestClient, seed_managed_apps: list[ManagedApp]):
        response = client.get("/api/apps", params={"enabled_only": True})
        assert response.status_code == 200
        data = response.json()
        assert len(data["applications"]) == 2
        assert all(a["is_enabled"] for a in data["applications"])


class TestPermissionUpdateAPI:
    """Tests for PATCH /api/apps/{app_id}/permission."""

    def test_toggle_permission_on(self, client: TestClient, db_session: Session, seed_managed_apps: list[ManagedApp]):
        app_id = "app-calc-001"
        response = client.patch(f"/api/apps/{app_id}/permission", json={"is_enabled": True})
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is True

        # Verify audit record created
        audit = db_session.query(AuditEvent).filter(AuditEvent.action_type == "update_app_permission").first()
        assert audit is not None
        assert audit.outcome == "success"
        assert app_id in audit.details_json

    def test_toggle_permission_off(self, client: TestClient, seed_managed_apps: list[ManagedApp]):
        app_id = "app-chrome-002"
        response = client.patch(f"/api/apps/{app_id}/permission", json={"is_enabled": False})
        assert response.status_code == 200
        assert response.json()["is_enabled"] is False

    def test_update_permission_nonexistent_app(self, client: TestClient):
        response = client.patch("/api/apps/unknown-app-id/permission", json={"is_enabled": True})
        assert response.status_code == 404
        assert "not found" in response.json()["error"]["message"].lower()


class TestApplicationLaunchAPI:
    """Tests for POST /api/apps/{app_id}/launch."""

    def test_launch_enabled_app_success(self, client: TestClient, db_session: Session, seed_managed_apps: list[ManagedApp]):
        # Chrome is enabled in seed
        app_id = "app-chrome-002"
        response = client.post(f"/api/apps/{app_id}/launch")
        assert response.status_code == 200
        data = response.json()
        assert data["launched"] is True
        assert data["app_id"] == app_id
        assert data["name"] == "Google Chrome"

        # Verify audit record created with outcome success
        audit = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.action_type == "launch_application", AuditEvent.outcome == "success")
            .first()
        )
        assert audit is not None
        assert app_id in audit.details_json

    def test_launch_disabled_app_blocked(self, client: TestClient, db_session: Session, seed_managed_apps: list[ManagedApp]):
        # Calc is disabled by default
        app_id = "app-calc-001"
        response = client.post(f"/api/apps/{app_id}/launch")
        assert response.status_code == 403
        assert "disabled" in response.json()["error"]["message"].lower()

        # Verify audit record created with outcome denied
        audit = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.action_type == "launch_application", AuditEvent.outcome == "denied")
            .first()
        )
        assert audit is not None
        assert "disabled" in audit.details_json.lower()

    def test_launch_nonexistent_app_denied(self, client: TestClient, db_session: Session):
        response = client.post("/api/apps/fake-id-999/launch")
        assert response.status_code == 404

        audit = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.action_type == "launch_application", AuditEvent.outcome == "denied")
            .first()
        )
        assert audit is not None
        assert "fake-id-999" in audit.details_json

    def test_launch_unavailable_app_failed(self, client: TestClient, db_session: Session, seed_managed_apps: list[ManagedApp]):
        # Ghost app is unavailable
        app_id = "app-ghost-003"
        response = client.post(f"/api/apps/{app_id}/launch")
        assert response.status_code == 400
        assert "unavailable" in response.json()["error"]["message"].lower()

        audit = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.action_type == "launch_application", AuditEvent.outcome == "failed")
            .first()
        )
        assert audit is not None
        assert "unavailable" in audit.details_json.lower()


class TestRefreshDiscoveryAPI:
    """Tests for POST /api/apps/refresh and permission persistence."""

    def test_refresh_preserves_existing_permissions(self, client: TestClient, db_session: Session, tmp_path: Path):
        # 1. Seed an application and enable it
        exe_file = tmp_path / "editor.exe"
        exe_file.write_text("binary")

        app_id = "editor-stable-id"
        initial_app = ManagedApp(
            id=app_id,
            name="My Editor",
            target_path=str(exe_file.resolve()),
            target_type="executable",
            category="Development",
            is_enabled=True,  # Explicitly enabled by user!
            is_available=True,
        )
        db_session.add(initial_app)
        db_session.commit()

        # 2. Simulate discovery returning the same app plus a brand new app
        new_exe = tmp_path / "browser.exe"
        new_exe.write_text("binary")

        discovered_batch = [
            DiscoveredApp(
                id=app_id,
                name="My Editor",
                target_path=str(exe_file.resolve()),
                target_type="executable",
                category="Development",
                is_available=True,
                is_valid=True,
            ),
            DiscoveredApp(
                id="new-browser-id",
                name="New Browser",
                target_path=str(new_exe.resolve()),
                target_type="executable",
                category="Browsers",
                is_available=True,
                is_valid=True,
            ),
        ]

        # Sync discovery directly using service
        AppManagerService.sync_discovery(db_session, discovered_batch)

        # 3. Verify: existing app is STILL enabled!
        apps, total, enabled, disabled, _ = AppManagerService.list_apps(db_session)
        assert total == 2
        assert enabled == 1
        assert disabled == 1

        editor = next(a for a in apps if a.id == app_id)
        assert editor.is_enabled is True  # Preserved!

        new_browser = next(a for a in apps if a.id == "new-browser-id")
        assert new_browser.is_enabled is False  # Default deny for newly discovered!
