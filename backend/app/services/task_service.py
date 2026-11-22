"""Service implementing task CRUD, due date tracking, and reminder queries."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.models import Task
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    """Task operations manager backed by SQLAlchemy session."""

    def __init__(self, db: Session):
        self.db = db

    def create_task(self, task_in: TaskCreate) -> Task:
        """Create and persist a new task."""
        task = Task(
            title=task_in.title,
            description=task_in.description,
            due_date=task_in.due_date,
            priority=task_in.priority,
            status="pending",
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task(self, task_id: str) -> Task:
        """Retrieve a task by ID or raise NotFoundError."""
        task = self.db.scalar(select(Task).where(Task.id == task_id))
        if not task:
            raise NotFoundError(f"Task with ID '{task_id}' not found.")
        return task

    def list_tasks(
        self,
        status: str | None = None,
        priority: str | None = None,
        due_today: bool = False,
    ) -> tuple[list[Task], int, int, int]:
        """List tasks matching filters and calculate counts."""
        query = select(Task).order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc())

        if status:
            query = query.where(Task.status == status)
        if priority:
            query = query.where(Task.priority == priority)
        if due_today:
            now = datetime.now(UTC)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.where(
                Task.due_date >= start_of_day,
                Task.due_date <= end_of_day,
            )

        tasks = list(self.db.scalars(query).all())

        total = self.db.scalar(select(func.count(Task.id))) or 0
        pending = self.db.scalar(select(func.count(Task.id)).where(Task.status == "pending")) or 0
        completed = (
            self.db.scalar(select(func.count(Task.id)).where(Task.status == "completed")) or 0
        )

        return tasks, total, pending, completed

    def update_task(self, task_id: str, update_in: TaskUpdate) -> Task:
        """Update existing task fields."""
        task = self.get_task(task_id)

        update_data = update_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        self.db.commit()
        self.db.refresh(task)
        return task

    def complete_task(self, task_id: str) -> Task:
        """Mark task as completed."""
        task = self.get_task(task_id)
        task.status = "completed"
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete_task(self, task_id: str) -> None:
        """Delete task from persistent storage."""
        task = self.get_task(task_id)
        self.db.delete(task)
        self.db.commit()

    def get_due_reminders(self) -> list[Task]:
        """Retrieve pending tasks that are overdue or due within the next 24 hours."""
        now = datetime.now(UTC)
        query = (
            select(Task)
            .where(
                Task.status == "pending",
                Task.due_date.is_not(None),
                Task.due_date <= now,
            )
            .order_by(Task.due_date.asc())
        )
        return list(self.db.scalars(query).all())
