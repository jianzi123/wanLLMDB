from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from app.models.run import Run
from app.schemas.run import RunCreate, RunUpdate


class RunRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, run_in: RunCreate, user_id: UUID) -> Run:
        """Create a new run"""
        db_run = Run(
            name=run_in.name,
            project_id=run_in.project_id,
            user_id=user_id,
            state="running",
            git_commit=run_in.git_commit,
            git_remote=run_in.git_remote,
            git_branch=run_in.git_branch,
            host=run_in.host,
            os=run_in.os,
            python_version=run_in.python_version,
            notes=run_in.notes,
            tags=run_in.tags,
        )
        self.db.add(db_run)
        self.db.commit()
        self.db.refresh(db_run)
        return db_run

    def get(self, run_id: UUID) -> Optional[Run]:
        """Get run by ID"""
        return self.db.query(Run).filter(Run.id == run_id).first()

    def list(
        self,
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        state: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> tuple[List[Run], int]:
        """List runs with filtering and pagination"""
        query = self.db.query(Run)

        # Filter by project
        if project_id:
            query = query.filter(Run.project_id == project_id)

        # Filter by user
        if user_id:
            query = query.filter(Run.user_id == user_id)

        # Filter by state
        if state:
            query = query.filter(Run.state == state)

        # Search in name and notes
        if search:
            search_filter = or_(
                Run.name.ilike(f"%{search}%"),
                Run.notes.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        runs = (
            query.order_by(Run.started_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return runs, total

    def update(self, run_id: UUID, run_in: RunUpdate) -> Optional[Run]:
        """Update run"""
        db_run = self.get(run_id)
        if not db_run:
            return None

        update_data = run_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_run, field, value)

        self.db.commit()
        self.db.refresh(db_run)
        return db_run

    def delete(self, run_id: UUID) -> bool:
        """Delete run"""
        db_run = self.get(run_id)
        if not db_run:
            return False

        self.db.delete(db_run)
        self.db.commit()
        return True

    def finish(self, run_id: UUID, exit_code: int = 0) -> Optional[Run]:
        """Mark run as finished"""
        db_run = self.get(run_id)
        if not db_run:
            return None

        db_run.state = "finished" if exit_code == 0 else "crashed"
        db_run.finished_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(db_run)
        return db_run

    def update_heartbeat(self, run_id: UUID) -> Optional[Run]:
        """Update run heartbeat timestamp"""
        db_run = self.get(run_id)
        if not db_run:
            return None

        db_run.heartbeat_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_run)
        return db_run

    def add_tags(self, run_id: UUID, tags: List[str]) -> Optional[Run]:
        """Add tags to run"""
        db_run = self.get(run_id)
        if not db_run:
            return None

        # Merge new tags with existing ones (avoid duplicates)
        existing_tags = set(db_run.tags or [])
        new_tags = set(tags)
        db_run.tags = list(existing_tags | new_tags)

        self.db.commit()
        self.db.refresh(db_run)
        return db_run

    def remove_tag(self, run_id: UUID, tag: str) -> Optional[Run]:
        """Remove a tag from run"""
        db_run = self.get(run_id)
        if not db_run:
            return None

        if db_run.tags and tag in db_run.tags:
            db_run.tags = [t for t in db_run.tags if t != tag]
            self.db.commit()
            self.db.refresh(db_run)

        return db_run

    def user_has_access(self, run_id: UUID, user_id: UUID) -> bool:
        """Check if user has access to run"""
        run = self.get(run_id)
        if not run:
            return False

        # Owner has access
        if run.user_id == user_id:
            return True

        # TODO: Check project access when project permissions are implemented
        return False
