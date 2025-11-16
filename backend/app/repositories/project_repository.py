from sqlalchemy.orm import Session
from sqlalchemy import func, or_, select
from typing import Optional, List, Tuple
from uuid import UUID
import re
from datetime import datetime

from app.models.project import Project
from app.models.run import Run
from app.schemas.project import ProjectCreate, ProjectUpdate


def _generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from project name"""
    slug = name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, project_in: ProjectCreate, user_id: UUID) -> Project:
        """Create a new project"""
        slug = _generate_slug(project_in.name)

        # Ensure unique slug
        base_slug = slug
        counter = 1
        while self.db.query(Project).filter(Project.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        db_project = Project(
            name=project_in.name,
            slug=slug,
            description=project_in.description,
            visibility=project_in.visibility,
            created_by=user_id,
        )
        self.db.add(db_project)
        self.db.commit()
        self.db.refresh(db_project)
        return db_project

    def get(self, project_id: UUID) -> Optional[Project]:
        """Get project by ID"""
        return self.db.query(Project).filter(Project.id == project_id).first()

    def get_by_slug(self, slug: str) -> Optional[Project]:
        """Get project by slug"""
        return self.db.query(Project).filter(Project.slug == slug).first()

    def list(
        self,
        user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> tuple[List[Project], int]:
        """List projects with filtering and pagination"""
        query = self.db.query(Project)

        # Filter by user if provided
        if user_id:
            query = query.filter(Project.created_by == user_id)

        # Filter by visibility
        if visibility:
            query = query.filter(Project.visibility == visibility)

        # Search in name and description
        if search:
            search_filter = or_(
                Project.name.ilike(f"%{search}%"),
                Project.description.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        projects = (
            query.order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return projects, total

    def list_with_stats(
        self,
        user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> Tuple[List[Tuple[Project, int, Optional[datetime]]], int]:
        """
        List projects with stats (run_count, last_activity) in a single query.
        This avoids the N+1 query problem.

        Returns:
            Tuple of (list of (project, run_count, last_activity), total_count)
        """
        # Build subquery for run stats
        run_stats_subquery = (
            select(
                Run.project_id,
                func.count(Run.id).label('run_count'),
                func.max(Run.created_at).label('last_activity')
            )
            .group_by(Run.project_id)
            .subquery()
        )

        # Build main query with LEFT JOIN to include projects with no runs
        query = (
            select(
                Project,
                func.coalesce(run_stats_subquery.c.run_count, 0).label('run_count'),
                run_stats_subquery.c.last_activity
            )
            .outerjoin(run_stats_subquery, Project.id == run_stats_subquery.c.project_id)
        )

        # Apply filters
        if user_id:
            query = query.where(Project.created_by == user_id)

        if visibility:
            query = query.where(Project.visibility == visibility)

        if search:
            search_filter = or_(
                Project.name.ilike(f"%{search}%"),
                Project.description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)

        # Get total count (need to count distinct projects)
        count_query = select(func.count(Project.id.distinct()))
        if user_id:
            count_query = count_query.where(Project.created_by == user_id)
        if visibility:
            count_query = count_query.where(Project.visibility == visibility)
        if search:
            count_query = count_query.where(search_filter)

        total = self.db.execute(count_query).scalar() or 0

        # Apply ordering and pagination
        query = query.order_by(Project.created_at.desc()).offset(skip).limit(limit)

        # Execute query
        results = self.db.execute(query).all()

        return results, total

    def get_with_stats(self, project_id: UUID) -> Optional[Tuple[Project, int, Optional[datetime]]]:
        """
        Get a single project with stats (run_count, last_activity) in a single query.
        This avoids the N+1 query problem.

        Returns:
            Tuple of (project, run_count, last_activity) or None if not found
        """
        # Build subquery for run stats
        run_stats_subquery = (
            select(
                Run.project_id,
                func.count(Run.id).label('run_count'),
                func.max(Run.created_at).label('last_activity')
            )
            .where(Run.project_id == project_id)
            .group_by(Run.project_id)
            .subquery()
        )

        # Build main query with LEFT JOIN
        query = (
            select(
                Project,
                func.coalesce(run_stats_subquery.c.run_count, 0).label('run_count'),
                run_stats_subquery.c.last_activity
            )
            .outerjoin(run_stats_subquery, Project.id == run_stats_subquery.c.project_id)
            .where(Project.id == project_id)
        )

        result = self.db.execute(query).first()
        return result

    def update(self, project_id: UUID, project_in: ProjectUpdate) -> Optional[Project]:
        """Update project"""
        db_project = self.get(project_id)
        if not db_project:
            return None

        update_data = project_in.model_dump(exclude_unset=True)

        # Update slug if name changed
        if "name" in update_data:
            update_data["slug"] = _generate_slug(update_data["name"])

        for field, value in update_data.items():
            setattr(db_project, field, value)

        self.db.commit()
        self.db.refresh(db_project)
        return db_project

    def delete(self, project_id: UUID) -> bool:
        """Delete project"""
        db_project = self.get(project_id)
        if not db_project:
            return False

        self.db.delete(db_project)
        self.db.commit()
        return True

    def get_run_count(self, project_id: UUID) -> int:
        """Get number of runs in project"""
        return self.db.query(Run).filter(Run.project_id == project_id).count()

    def get_last_activity(self, project_id: UUID) -> Optional[str]:
        """Get last activity timestamp (most recent run)"""
        last_run = (
            self.db.query(Run)
            .filter(Run.project_id == project_id)
            .order_by(Run.created_at.desc())
            .first()
        )
        return last_run.created_at if last_run else None

    def user_has_access(self, project_id: UUID, user_id: UUID) -> bool:
        """Check if user has access to project"""
        project = self.get(project_id)
        if not project:
            return False

        # Owner has access
        if project.created_by == user_id:
            return True

        # Public projects are accessible to all
        if project.visibility == "public":
            return True

        # TODO: Check team membership when implemented
        return False
