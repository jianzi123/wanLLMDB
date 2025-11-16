from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from uuid import UUID
import math

from app.db.database import get_db
from app.schemas.run import (
    Run,
    RunCreate,
    RunUpdate,
    RunList,
    RunFinish,
    RunTagAdd,
)
from app.schemas.user import User
from app.repositories.run_repository import RunRepository
from app.repositories.project_repository import ProjectRepository
from app.api.v1.auth import get_current_user

router = APIRouter()


def get_run_repo(db: Session = Depends(get_db)) -> RunRepository:
    return RunRepository(db)


def get_project_repo(db: Session = Depends(get_db)) -> ProjectRepository:
    return ProjectRepository(db)


@router.post("", response_model=Run, status_code=status.HTTP_201_CREATED)
async def create_run(
    run_in: RunCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    run_repo: RunRepository = Depends(get_run_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Create a new run"""
    # Check if project exists and user has access
    if not project_repo.user_has_access(run_in.project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    run = run_repo.create(run_in, current_user.id)
    return run


@router.get("", response_model=RunList)
async def list_runs(
    current_user: Annotated[User, Depends(get_current_user)],
    run_repo: RunRepository = Depends(get_run_repo),
    project_id: Optional[UUID] = None,
    state: Optional[str] = Query(None, pattern="^(running|finished|crashed|killed)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    my_runs: bool = False,
):
    """List runs with pagination and filtering"""
    skip = (page - 1) * page_size

    # Filter by current user if my_runs is True
    user_id = current_user.id if my_runs else None

    runs, total = run_repo.list(
        project_id=project_id,
        user_id=user_id,
        state=state,
        skip=skip,
        limit=page_size,
        search=search,
    )

    # TODO: Add config and summary data

    total_pages = math.ceil(total / page_size)

    return RunList(
        items=runs,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{run_id}", response_model=Run)
async def get_run(
    run_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    run_repo: RunRepository = Depends(get_run_repo),
):
    """Get run by ID"""
    # Check access
    if not run_repo.user_has_access(run_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    # TODO: Add config and summary data

    return run


@router.patch("/{run_id}", response_model=Run)
async def update_run(
    run_id: UUID,
    run_in: RunUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    run_repo: RunRepository = Depends(get_run_repo),
):
    """Update run"""
    # Check if run exists and user is owner
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    if run.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this run",
        )

    updated_run = run_repo.update(run_id, run_in)
    return updated_run


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(
    run_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    run_repo: RunRepository = Depends(get_run_repo),
):
    """Delete run"""
    # Check if run exists and user is owner
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    if run.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this run",
        )

    run_repo.delete(run_id)


@router.post("/{run_id}/finish", response_model=Run)
async def finish_run(
    run_id: UUID,
    finish_data: RunFinish,
    current_user: Annotated[User, Depends(get_current_user)],
    run_repo: RunRepository = Depends(get_run_repo),
):
    """Mark run as finished"""
    # Check if run exists and user is owner
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    if run.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to finish this run",
        )

    finished_run = run_repo.finish(run_id, finish_data.exit_code)
    # TODO: Save summary data
    return finished_run


@router.post("/{run_id}/heartbeat", response_model=Run)
async def update_heartbeat(
    run_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    run_repo: RunRepository = Depends(get_run_repo),
):
    """Update run heartbeat"""
    # Check if run exists and user is owner
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    if run.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this run",
        )

    updated_run = run_repo.update_heartbeat(run_id)
    return updated_run


@router.post("/{run_id}/tags", response_model=Run)
async def add_tags(
    run_id: UUID,
    tag_data: RunTagAdd,
    current_user: Annotated[User, Depends(get_current_user)],
    run_repo: RunRepository = Depends(get_run_repo),
):
    """Add tags to run"""
    # Check if run exists and user is owner
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    if run.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this run",
        )

    updated_run = run_repo.add_tags(run_id, tag_data.tags)
    return updated_run


@router.delete("/{run_id}/tags/{tag}", response_model=Run)
async def remove_tag(
    run_id: UUID,
    tag: str,
    current_user: Annotated[User, Depends(get_current_user)],
    run_repo: RunRepository = Depends(get_run_repo),
):
    """Remove a tag from run"""
    # Check if run exists and user is owner
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    if run.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this run",
        )

    updated_run = run_repo.remove_tag(run_id, tag)
    return updated_run
