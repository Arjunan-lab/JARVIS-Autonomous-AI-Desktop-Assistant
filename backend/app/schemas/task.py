"""Pydantic schemas for Task management and reminders."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    """Payload for creating a new task."""

    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: str | None = Field(default=None, description="Optional task details")
    due_date: datetime | None = Field(default=None, description="Optional due datetime (ISO 8601)")
    priority: Literal["low", "medium", "high"] = Field(
        default="medium", description="Task priority"
    )


class TaskUpdate(BaseModel):
    """Payload for updating an existing task."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None)
    due_date: datetime | None = Field(default=None)
    status: Literal["pending", "completed", "cancelled"] | None = Field(default=None)
    priority: Literal["low", "medium", "high"] | None = Field(default=None)


class TaskResponse(BaseModel):
    """Response payload representing a saved task."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None
    due_date: datetime | None
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime

    @property
    def is_overdue(self) -> bool:
        if self.status != "pending" or not self.due_date:
            return False
        return self.due_date < datetime.now(UTC)

    @property
    def is_due_today(self) -> bool:
        if not self.due_date:
            return False
        now = datetime.now(UTC)
        return self.due_date.date() == now.date()


class TaskListResponse(BaseModel):
    """List response with summary statistics."""

    tasks: list[TaskResponse]
    total: int
    pending_count: int
    completed_count: int
