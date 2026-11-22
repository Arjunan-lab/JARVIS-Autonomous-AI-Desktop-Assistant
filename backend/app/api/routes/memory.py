"""Structured memory and local knowledge retrieval routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.memory import (
    MemoryCreate,
    MemoryListResponse,
    MemoryResponse,
    MemorySearchResponse,
    MemoryUpdate,
)
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/api/memory", tags=["memory"])


def get_current_settings(request: Request) -> Settings:
    """Dependency providing current application settings."""
    return getattr(request.app.state, "settings", None) or get_settings()


@router.get("", response_model=MemoryListResponse, summary="List saved memories")
def list_memories(
    db: Annotated[Session, Depends(get_db)],
    category: str | None = Query(
        default=None,
        description="Filter by category (preference, project, knowledge, task_history)",
    ),
    approved_only: bool = Query(
        default=False, description="Filter to only approved memories"
    ),
    search: str | None = Query(
        default=None, description="Search keyword in memory content"
    ),
) -> MemoryListResponse:
    """Retrieve saved memories with category breakdown counts."""
    memories = MemoryService.list_memories(
        db, category=category, approved_only=approved_only, query=search
    )
    counts = MemoryService.get_category_counts(db)
    return MemoryListResponse(
        memories=[MemoryResponse.model_validate(m) for m in memories],
        total=counts.get("total", 0),
        preference_count=counts.get("preference", 0),
        project_count=counts.get("project", 0),
        knowledge_count=counts.get("knowledge", 0),
        task_history_count=counts.get("task_history", 0),
    )


@router.post(
    "",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save an explicitly approved memory",
)
def create_memory(
    memory_in: MemoryCreate,
    db: Annotated[Session, Depends(get_db)],
) -> MemoryResponse:
    """Create a persistent user memory."""
    memory = MemoryService.create_memory(db, memory_in)
    return MemoryResponse.model_validate(memory)


@router.get(
    "/search",
    response_model=MemorySearchResponse,
    summary="Search memories and allowed local documents",
)
def search_memory_and_documents(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_current_settings)],
    q: str = Query(..., min_length=1, description="Search keyword"),
    category: str | None = Query(default=None, description="Optional category filter"),
    approved_only: bool = Query(
        default=True, description="Only search approved memories"
    ),
    search_docs: bool = Query(
        default=True, description="Whether to also search allowed local folders"
    ),
) -> MemorySearchResponse:
    """Unified keyword search across structured memories and local documents."""
    memories = MemoryService.search_memories(
        db, query=q, category=category, approved_only=approved_only
    )
    documents = []
    if search_docs and settings.jarvis_allowed_dirs:
        documents = MemoryService.search_allowed_documents(
            query=q, allowed_dirs=settings.jarvis_allowed_dirs
        )
    return MemorySearchResponse(
        query=q,
        memories=[MemoryResponse.model_validate(m) for m in memories],
        documents=documents,
    )


@router.get("/{memory_id}", response_model=MemoryResponse, summary="Get memory by ID")
def get_memory(
    memory_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> MemoryResponse:
    """Retrieve an individual memory record."""
    memory = MemoryService.get_memory(db, memory_id)
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory with ID '{memory_id}' not found",
        )
    return MemoryResponse.model_validate(memory)


@router.patch("/{memory_id}", response_model=MemoryResponse, summary="Update memory")
def update_memory(
    memory_id: str,
    memory_in: MemoryUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> MemoryResponse:
    """Update memory content, category, or approval status."""
    memory = MemoryService.update_memory(db, memory_id, memory_in)
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory with ID '{memory_id}' not found",
        )
    return MemoryResponse.model_validate(memory)


@router.delete(
    "/{memory_id}", status_code=status.HTTP_200_OK, summary="Delete memory"
)
def delete_memory(
    memory_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    """Delete a memory record."""
    success = MemoryService.delete_memory(db, memory_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory with ID '{memory_id}' not found",
        )
    return {"deleted": True, "id": memory_id}
