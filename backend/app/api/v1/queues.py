"""
Queue and Quota management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import logging

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.job_queue import JobQueue, ProjectQuota
from app.schemas.job_details import (
    QueueResponse,
    QueueCreate,
    QueueUpdate,
    QuotaResponse,
    QuotaUpdate,
)
from app.repositories.job_queue_repository import JobQueueRepository, ProjectQuotaRepository
from app.repositories.project_repository import ProjectRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/queues", tags=["queues"])


@router.post("", response_model=QueueResponse, status_code=status.HTTP_201_CREATED)
def create_queue(
    project_id: UUID,
    queue_data: QueueCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueueResponse:
    """Create a new job queue for a project."""
    queue_repo = JobQueueRepository(db)
    project_repo = ProjectRepository(db)

    # Verify project exists and user has access
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this project")

    # Create queue
    queue_dict = queue_data.model_dump()
    queue_dict["project_id"] = project_id

    queue = queue_repo.create(queue_dict)

    logger.info(f"Created queue {queue.id} for project {project_id}")
    return QueueResponse.model_validate(queue)


@router.get("", response_model=List[QueueResponse])
def list_queues(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[QueueResponse]:
    """List all queues for a project."""
    queue_repo = JobQueueRepository(db)
    project_repo = ProjectRepository(db)

    # Verify project exists and user has access
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this project")

    queues = queue_repo.get_by_project(project_id)
    return [QueueResponse.model_validate(q) for q in queues]


@router.get("/{queue_id}", response_model=QueueResponse)
def get_queue(
    queue_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueueResponse:
    """Get queue details."""
    queue_repo = JobQueueRepository(db)
    project_repo = ProjectRepository(db)

    queue = queue_repo.get_by_id(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")

    # Check permission
    project = project_repo.get_by_id(queue.project_id)
    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this queue")

    return QueueResponse.model_validate(queue)


@router.patch("/{queue_id}", response_model=QueueResponse)
def update_queue(
    queue_id: UUID,
    queue_update: QueueUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueueResponse:
    """Update queue configuration."""
    queue_repo = JobQueueRepository(db)
    project_repo = ProjectRepository(db)

    queue = queue_repo.get_by_id(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")

    # Check permission
    project = project_repo.get_by_id(queue.project_id)
    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this queue")

    # Update queue
    update_data = queue_update.model_dump(exclude_unset=True)
    updated_queue = queue_repo.update(queue, update_data)

    logger.info(f"Updated queue {queue_id}")
    return QueueResponse.model_validate(updated_queue)


@router.delete("/{queue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_queue(
    queue_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a queue."""
    queue_repo = JobQueueRepository(db)
    project_repo = ProjectRepository(db)

    queue = queue_repo.get_by_id(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")

    # Check permission
    project = project_repo.get_by_id(queue.project_id)
    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this queue")

    # Check if queue has jobs
    if queue.total_jobs > 0:
        raise HTTPException(status_code=400, detail="Cannot delete queue with jobs. Remove jobs first.")

    queue_repo.delete(queue)
    logger.info(f"Deleted queue {queue_id}")


# Quota endpoints

@router.get("/quota/{project_id}", response_model=QuotaResponse)
def get_project_quota(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuotaResponse:
    """Get project quota information."""
    quota_repo = ProjectQuotaRepository(db)
    project_repo = ProjectRepository(db)

    # Verify project exists and user has access
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this project")

    quota = quota_repo.get_or_create(project_id)

    # Compute available resources
    available = quota.get_available_resources()
    usage_percent = quota.get_usage_percentage()

    response_data = {
        **quota.__dict__,
        "available_cpu": available["cpu"],
        "available_memory": available["memory"],
        "available_gpu": available["gpu"],
        "available_jobs": available["jobs"],
        "cpu_usage_percent": usage_percent["cpu"],
        "memory_usage_percent": usage_percent["memory"],
        "gpu_usage_percent": usage_percent["gpu"],
        "jobs_usage_percent": usage_percent["jobs"],
    }

    return QuotaResponse(**response_data)


@router.patch("/quota/{project_id}", response_model=QuotaResponse)
def update_project_quota(
    project_id: UUID,
    quota_update: QuotaUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuotaResponse:
    """Update project quota limits."""
    quota_repo = ProjectQuotaRepository(db)
    project_repo = ProjectRepository(db)

    # Verify project exists and user has access
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this project")

    quota = quota_repo.get_or_create(project_id)

    # Update quota
    update_data = quota_update.model_dump(exclude_unset=True)
    updated_quota = quota_repo.update(quota, update_data)

    # Compute available resources
    available = updated_quota.get_available_resources()
    usage_percent = updated_quota.get_usage_percentage()

    response_data = {
        **updated_quota.__dict__,
        "available_cpu": available["cpu"],
        "available_memory": available["memory"],
        "available_gpu": available["gpu"],
        "available_jobs": available["jobs"],
        "cpu_usage_percent": usage_percent["cpu"],
        "memory_usage_percent": usage_percent["memory"],
        "gpu_usage_percent": usage_percent["gpu"],
        "jobs_usage_percent": usage_percent["jobs"],
    }

    logger.info(f"Updated quota for project {project_id}")
    return QuotaResponse(**response_data)
