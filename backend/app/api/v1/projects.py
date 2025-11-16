from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from uuid import UUID
import math

from app.db.database import get_db
from app.schemas.project import Project, ProjectCreate, ProjectUpdate, ProjectList
from app.schemas.user import User
from app.repositories.project_repository import ProjectRepository
from app.api.v1.auth import get_current_user

router = APIRouter()


def get_project_repo(db: Session = Depends(get_db)) -> ProjectRepository:
    return ProjectRepository(db)


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: ProjectRepository = Depends(get_project_repo),
):
    """Create a new project"""
    project = repo.create(project_in, current_user.id)
    return project


@router.get("", response_model=ProjectList)
async def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    repo: ProjectRepository = Depends(get_project_repo),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    visibility: Optional[str] = Query(None, pattern="^(public|private)$"),
    my_projects: bool = False,
):
    """List projects with pagination and filtering"""
    skip = (page - 1) * page_size

    # Filter by current user if my_projects is True
    user_id = current_user.id if my_projects else None

    # Use optimized method that avoids N+1 queries
    results, total = repo.list_with_stats(
        user_id=user_id,
        skip=skip,
        limit=page_size,
        search=search,
        visibility=visibility,
    )

    # Extract projects and add stats
    projects = []
    for project, run_count, last_activity in results:
        project.run_count = run_count
        project.last_activity = last_activity
        projects.append(project)

    total_pages = math.ceil(total / page_size)

    return ProjectList(
        items=projects,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: ProjectRepository = Depends(get_project_repo),
):
    """Get project by ID"""
    # Check access
    if not repo.user_has_access(project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Use optimized method that avoids N+1 queries
    result = repo.get_with_stats(project_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Unpack result and add stats to project
    project, run_count, last_activity = result
    project.run_count = run_count
    project.last_activity = last_activity

    return project


@router.patch("/{project_id}", response_model=Project)
async def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: ProjectRepository = Depends(get_project_repo),
):
    """Update project"""
    # Check if project exists and user is owner
    project = repo.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this project",
        )

    updated_project = repo.update(project_id, project_in)
    return updated_project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: ProjectRepository = Depends(get_project_repo),
):
    """Delete project"""
    # Check if project exists and user is owner
    project = repo.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this project",
        )

    repo.delete(project_id)
