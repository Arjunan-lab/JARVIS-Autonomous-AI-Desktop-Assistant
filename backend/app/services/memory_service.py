"""Service layer for structured memory persistence, retrieval, and document keyword search."""

import os
from pathlib import Path

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models import Memory
from app.schemas.memory import DocumentSearchResult, MemoryCreate, MemoryUpdate

ALLOWED_SEARCH_EXTENSIONS = {
    ".md",
    ".txt",
    ".py",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".csv",
    ".rst",
    ".ts",
    ".tsx",
    ".js",
}

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "target",
}


class MemoryService:
    """Service providing CRUD and search operations for user memories and local files."""

    @staticmethod
    def create_memory(db: Session, memory_in: MemoryCreate) -> Memory:
        """Create and persist an explicitly approved user memory."""
        memory = Memory(
            category=memory_in.category,
            content=memory_in.content,
            approved=memory_in.approved,
            source=memory_in.source,
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def get_memory(db: Session, memory_id: str) -> Memory | None:
        """Retrieve a single memory record by its primary key ID."""
        stmt: Select[tuple[Memory]] = select(Memory).where(Memory.id == memory_id)
        return db.scalars(stmt).first()

    @staticmethod
    def list_memories(
        db: Session,
        category: str | None = None,
        approved_only: bool = False,
        query: str | None = None,
    ) -> list[Memory]:
        """List memories with optional category filtering, approval filtering, or text matching."""
        stmt: Select[tuple[Memory]] = select(Memory).order_by(Memory.created_at.desc())

        if category is not None:
            stmt = stmt.where(Memory.category == category)
        if approved_only:
            stmt = stmt.where(Memory.approved.is_(True))
        if query:
            stmt = stmt.where(Memory.content.ilike(f"%{query.strip()}%"))

        return list(db.scalars(stmt).all())

    @staticmethod
    def get_category_counts(db: Session) -> dict[str, int]:
        """Return counts of memories partitioned by category and total."""
        categories = ["preference", "project", "knowledge", "task_history"]
        counts: dict[str, int] = {cat: 0 for cat in categories}

        stmt = select(Memory.category, func.count(Memory.id)).group_by(Memory.category)
        results = db.execute(stmt).all()
        for cat, cnt in results:
            if cat in counts:
                counts[cat] = cnt

        total_stmt = select(func.count(Memory.id))
        counts["total"] = db.scalar(total_stmt) or 0
        return counts

    @staticmethod
    def update_memory(
        db: Session, memory_id: str, memory_in: MemoryUpdate
    ) -> Memory | None:
        """Update an existing memory's content, category, or approved status."""
        memory = MemoryService.get_memory(db, memory_id)
        if memory is None:
            return None

        if memory_in.category is not None:
            memory.category = memory_in.category
        if memory_in.content is not None:
            memory.content = memory_in.content
        if memory_in.approved is not None:
            memory.approved = memory_in.approved
        if memory_in.source is not None:
            memory.source = memory_in.source

        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def delete_memory(db: Session, memory_id: str) -> bool:
        """Delete a saved memory record. Returns True if deleted, False if not found."""
        memory = MemoryService.get_memory(db, memory_id)
        if memory is None:
            return False

        db.delete(memory)
        db.commit()
        return True

    @staticmethod
    def search_memories(
        db: Session,
        query: str,
        category: str | None = None,
        approved_only: bool = True,
        limit: int = 10,
    ) -> list[Memory]:
        """Search memory content by keyword."""
        clean_query = query.strip()
        if not clean_query:
            return []

        stmt = select(Memory).where(Memory.content.ilike(f"%{clean_query}%"))
        if category:
            stmt = stmt.where(Memory.category == category)
        if approved_only:
            stmt = stmt.where(Memory.approved.is_(True))

        stmt = stmt.order_by(Memory.created_at.desc()).limit(limit)
        return list(db.scalars(stmt).all())

    @staticmethod
    def search_allowed_documents(
        query: str,
        allowed_dirs: list[str] | str | None,
        max_results: int = 10,
    ) -> list[DocumentSearchResult]:
        """Search approved local folders for keywords without path traversal risk."""
        clean_query = query.strip().lower()
        if not clean_query or not allowed_dirs:
            return []

        if isinstance(allowed_dirs, str):
            raw_paths = [p.strip() for p in allowed_dirs.split(",") if p.strip()]
        else:
            raw_paths = [str(p).strip() for p in allowed_dirs if str(p).strip()]

        valid_roots: list[Path] = []
        for p in raw_paths:
            resolved = Path(p).resolve()
            if resolved.exists() and resolved.is_dir():
                valid_roots.append(resolved)

        if not valid_roots:
            return []

        results: list[DocumentSearchResult] = []

        for root in valid_roots:
            if len(results) >= max_results:
                break

            for dirpath, dirnames, filenames in os.walk(root):
                # Filter out excluded directories in-place to prevent traversal into them
                dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRECTORIES]

                for filename in filenames:
                    if len(results) >= max_results:
                        break

                    file_path = Path(dirpath) / filename
                    if file_path.suffix.lower() not in ALLOWED_SEARCH_EXTENSIONS:
                        continue

                    # Guarantee the file is strictly within an allowed root (no path traversal)
                    try:
                        resolved_file = file_path.resolve()
                        if not any(
                            resolved_file.is_relative_to(r) for r in valid_roots
                        ):
                            continue
                    except (ValueError, OSError):
                        continue

                    # Read and search lines
                    try:
                        with open(
                            resolved_file, "r", encoding="utf-8", errors="replace"
                        ) as f:
                            for line_idx, line in enumerate(f, start=1):
                                if clean_query in line.lower():
                                    snippet = line.strip()
                                    if len(snippet) > 200:
                                        snippet = snippet[:197] + "..."
                                    results.append(
                                        DocumentSearchResult(
                                            file_path=str(resolved_file),
                                            file_name=filename,
                                            snippet=snippet,
                                            line_number=line_idx,
                                        )
                                    )
                                    if len(results) >= max_results:
                                        break
                    except (OSError, UnicodeError):
                        continue

        return results
