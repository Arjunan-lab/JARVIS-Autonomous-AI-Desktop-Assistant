"""Task management routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def get_task_service(db: Annotated[Session, Depends(get_db)]) -> TaskService:
    """Dependency providing TaskService backed by active db session."""
    return TaskService(db=db)


@router.get("", response_model=TaskListResponse, summary="List tasks with optional filters")
def list_tasks(
    service: Annotated[TaskService, Depends(get_task_service)],
    task_status: str | None = Query(default=None, alias="status", description="Filter by status"),
    priority: str | None = Query(default=None, description="Filter by priority"),
    due_today: bool = Query(default=False, description="Filter tasks due today"),
) -> TaskListResponse:
    """Retrieve saved tasks with total, pending, and completed summary counts."""
    tasks, total, pending, completed = service.list_tasks(
        status=task_status,
        priority=priority,
        due_today=due_today,
    )
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        pending_count=pending,
        completed_count=completed,
    )


@router.get("/reminders", response_model=list[TaskResponse], summary="Get pending overdue or due tasks")
def get_reminders(
    service: Annotated[TaskService, Depends(get_task_service)],
) -> list[TaskResponse]:
    """Retrieve all pending tasks requiring reminder alerts."""
    reminders = service.get_due_reminders()
    return [TaskResponse.model_validate(t) for t in reminders]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, summary="Create a new task")
def create_task(
    task_in: TaskCreate,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """Create a new task with title, description, priority, and optional due date."""
    task = service.create_task(task_in)
    return TaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=TaskResponse, summary="Get task details by ID")
def get_task(
    task_id: str,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """Retrieve single task by its unique identifier."""
    task = service.get_task(task_id)
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse, summary="Update task details or status")
def update_task(
    task_id: str,
    update_in: TaskUpdate,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """Update title, description, due date, status, or priority of a task."""
    task = service.update_task(task_id, update_in)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a task")
def delete_task(
    task_id: str,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> Response:
    """Permanently delete a task by ID."""
    service.delete_task(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
