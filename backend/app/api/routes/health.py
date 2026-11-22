"""Health endpoint route definition."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return backend service health status."""
    return HealthResponse(status="ok", service="jarvis", version="0.1.0")
