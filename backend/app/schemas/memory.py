"""Pydantic schemas for persistent structured memory and document retrieval."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MemoryCategory = Literal["preference", "project", "knowledge", "task_history"]


class MemoryCreate(BaseModel):
    """Schema for saving a new explicitly approved memory."""

    category: MemoryCategory = Field(
        default="preference",
        description="Memory category: preference, project, knowledge, or task_history",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Text content of the memory or note",
    )
    approved: bool = Field(
        default=True,
        description="Whether this memory has explicit user approval to persist",
    )
    source: str | None = Field(
        default="user",
        max_length=64,
        description="Origin source (e.g. user, assistant, document)",
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Memory content cannot be empty or whitespace only")
        return v


class MemoryUpdate(BaseModel):
    """Schema for updating/editing an existing memory."""

    category: MemoryCategory | None = Field(
        default=None,
        description="Updated memory category",
    )
    content: str | None = Field(
        default=None,
        max_length=10000,
        description="Updated memory text content",
    )
    approved: bool | None = Field(
        default=None,
        description="Updated approval status",
    )
    source: str | None = Field(
        default=None,
        max_length=64,
        description="Updated origin source",
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Memory content cannot be empty or whitespace only")
        return v


class MemoryResponse(BaseModel):
    """Schema for serialized memory model response."""

    id: str
    category: str
    content: str
    approved: bool
    source: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemoryListResponse(BaseModel):
    """Schema for listing memories with summary category counts."""

    memories: list[MemoryResponse]
    total: int
    preference_count: int
    project_count: int
    knowledge_count: int
    task_history_count: int


class DocumentSearchResult(BaseModel):
    """Schema for matched text within allowed local documents."""

    file_path: str
    file_name: str
    snippet: str
    line_number: int | None = None


class MemorySearchResponse(BaseModel):
    """Unified search response for structured memories and allowed local documents."""

    query: str
    memories: list[MemoryResponse]
    documents: list[DocumentSearchResult]
