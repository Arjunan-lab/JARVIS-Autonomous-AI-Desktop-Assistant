"""Test that data survives database restart / connection re-opening."""

import os
import tempfile

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.models import Task
from app.db.session import Base


def test_sqlite_persistence_across_restart():
    """Verify that records persist to disk when the session/engine is closed and reopened."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_persist.db")
        db_url = f"sqlite:///{db_path}"

        # Session 1: Create table and insert a task
        engine1 = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine1)
        Session1 = sessionmaker(bind=engine1)
        with Session1() as s1:
            t = Task(title="Persistent Task Across Restarts", status="pending")
            s1.add(t)
            s1.commit()
            task_id = t.id
        engine1.dispose()

        # Session 2: Fresh engine and session from the same file
        engine2 = create_engine(db_url, connect_args={"check_same_thread": False})
        Session2 = sessionmaker(bind=engine2)
        with Session2() as s2:
            reloaded = s2.scalar(select(Task).where(Task.id == task_id))
            assert reloaded is not None
            assert reloaded.title == "Persistent Task Across Restarts"
            assert reloaded.status == "pending"
        engine2.dispose()
