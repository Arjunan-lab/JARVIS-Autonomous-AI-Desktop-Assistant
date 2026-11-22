from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import applications, approvals, commands, health, memory, tasks, voice
from app.api.routes import settings as settings_routes
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Reset active sessions counter on server boot
    try:
        from app.db.session import SessionLocal
        from app.services.budget_service import BudgetService

        with SessionLocal() as db:
            BudgetService._set_setting(db, BudgetService.KEY_ACTIVE, "0")
    except (OSError, RuntimeError):
        pass
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    if settings is None:
        settings = get_settings()

    setup_logging(level=settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="JARVIS Personal AI Desktop Assistant API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.state.settings = settings

    # CORS configuration for desktop frontend
    origins = [settings.frontend_origin]
    if "http://localhost:5173" not in origins:
        origins.append("http://localhost:5173")
    if "http://127.0.0.1:5173" not in origins:
        origins.append("http://127.0.0.1:5173")
    if "tauri://localhost" not in origins:
        origins.append("tauri://localhost")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handling
    register_error_handlers(app)

    # Routers
    app.include_router(health.router)
    app.include_router(voice.router)
    app.include_router(tasks.router)
    app.include_router(memory.router)
    app.include_router(approvals.router)
    app.include_router(settings_routes.router)
    app.include_router(applications.router)
    app.include_router(commands.router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    current_settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=current_settings.host,
        port=current_settings.port,
        reload=current_settings.app_env == "development",
    )
