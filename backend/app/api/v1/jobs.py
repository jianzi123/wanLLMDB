"""
Jobs API endpoints for cluster job management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import logging

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.job import Job, JobStatusEnum, JobTypeEnum, JobExecutorEnum
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobResponse,
    JobListResponse,
    JobStatsResponse,
    JobStatus,
    JobType,
    JobExecutor,
)
from app.repositories.job_repository import JobRepository
from app.repositories.project_repository import ProjectRepository
from app.executors import ExecutorFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """
    Create and submit a new job to the cluster.

    Supports three job types:
    - **training**: ML model training jobs
    - **inference**: Model inference/serving jobs
    - **workflow**: Multi-step workflow jobs (DAG)

    And two executors:
    - **kubernetes**: Run on Kubernetes cluster
    - **slurm**: Run on Slurm cluster
    """
    job_repo = JobRepository(db)
    project_repo = ProjectRepository(db)

    # Verify project exists and user has access
    project = project_repo.get_by_id(job_data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if user owns the project (future: check team membership)
    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create jobs in this project")

    # Check if executor is configured
    executor_type = JobExecutorEnum(job_data.executor.value)
    if not ExecutorFactory.is_configured(executor_type):
        raise HTTPException(
            status_code=400,
            detail=f"Executor {job_data.executor} is not configured. Please contact administrator."
        )

    # Create job in database
    job_dict = job_data.model_dump()
    job_dict["user_id"] = current_user.id
    job_dict["status"] = JobStatusEnum.PENDING

    job = job_repo.create(job_dict)

    # Submit job to executor
    try:
        executor = ExecutorFactory.get_executor(executor_type)
        external_id = executor.submit_job(job)

        # Update job with external ID
        job_repo.update(job, {
            "external_id": external_id,
            "namespace": job_data.executor_config.get("namespace", executor.default_namespace if hasattr(executor, 'default_namespace') else None),
            "status": JobStatusEnum.QUEUED,
        })

        logger.info(f"Job {job.id} submitted successfully with external ID: {external_id}")
    except Exception as e:
        # Update job status to failed
        job_repo.update(job, {
            "status": JobStatusEnum.FAILED,
            "error_message": f"Failed to submit job: {str(e)}",
        })
        logger.error(f"Failed to submit job {job.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")

    return JobResponse.model_validate(job)


@router.get("", response_model=JobListResponse)
def list_jobs(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    run_id: Optional[UUID] = Query(None, description="Filter by run ID"),
    job_type: Optional[JobType] = Query(None, description="Filter by job type"),
    executor: Optional[JobExecutor] = Query(None, description="Filter by executor"),
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobListResponse:
    """
    List jobs with filtering and pagination.

    Filters:
    - project_id: Filter by project
    - run_id: Filter by experiment run
    - job_type: Filter by training/inference/workflow
    - executor: Filter by kubernetes/slurm
    - status: Filter by job status
    - search: Search in job name and description
    """
    job_repo = JobRepository(db)

    skip = (page - 1) * page_size

    # Build filters
    filters = {
        "skip": skip,
        "limit": page_size,
        "search": search,
    }

    if project_id:
        filters["project_id"] = project_id
    if run_id:
        filters["run_id"] = run_id
    if job_type:
        filters["job_type"] = JobTypeEnum(job_type.value)
    if executor:
        filters["executor"] = JobExecutorEnum(executor.value)
    if status:
        filters["status"] = JobStatusEnum(status.value)

    # TODO: Add permission check - only show jobs user has access to
    # For now, show all jobs (in production, filter by user or team)
    filters["user_id"] = current_user.id

    jobs, total = job_repo.list(**filters)

    return JobListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=JobStatsResponse)
def get_job_stats(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobStatsResponse:
    """Get job statistics."""
    job_repo = JobRepository(db)

    stats = job_repo.get_stats(
        project_id=project_id,
        user_id=current_user.id,
    )

    return JobStatsResponse(**stats)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Get job details by ID."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    return JobResponse.model_validate(job)


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: UUID,
    job_update: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Update job metadata (name, description, tags, etc.)."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this job")

    # Update job
    update_data = job_update.model_dump(exclude_unset=True)
    updated_job = job_repo.update(job, update_data)

    return JobResponse.model_validate(updated_job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Cancel a running job."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this job")

    # Check if job can be cancelled
    if job.status not in [JobStatusEnum.PENDING, JobStatusEnum.QUEUED, JobStatusEnum.RUNNING]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job in {job.status} state")

    # Cancel job via executor
    try:
        executor = ExecutorFactory.get_executor(job.executor)
        executor.cancel_job(job.external_id)

        # Update job status
        updated_job = job_repo.update_status(job, JobStatusEnum.CANCELLED)

        logger.info(f"Job {job.id} cancelled successfully")
        return JobResponse.model_validate(updated_job)
    except Exception as e:
        logger.error(f"Failed to cancel job {job.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.get("/{job_id}/logs")
def get_job_logs(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get job logs."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    # Get logs from executor
    try:
        executor = ExecutorFactory.get_executor(job.executor)
        logs = executor.get_job_logs(job.external_id)

        return {
            "job_id": str(job.id),
            "external_id": job.external_id,
            "logs": logs,
        }
    except Exception as e:
        logger.error(f"Failed to get logs for job {job.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")


@router.get("/{job_id}/metrics")
def get_job_metrics(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get job resource usage metrics."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    # Get metrics from executor
    try:
        executor = ExecutorFactory.get_executor(job.executor)
        metrics = executor.get_job_metrics(job.external_id)

        return {
            "job_id": str(job.id),
            "external_id": job.external_id,
            "metrics": metrics,
            "stored_metrics": job.metrics,
        }
    except Exception as e:
        logger.error(f"Failed to get metrics for job {job.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.post("/{job_id}/refresh-status", response_model=JobResponse)
def refresh_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Manually refresh job status from executor."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to refresh this job")

    # Get status from executor
    try:
        executor = ExecutorFactory.get_executor(job.executor)
        current_status = executor.get_job_status(job.external_id)

        # Update job status if changed
        if current_status != job.status:
            updated_job = job_repo.update_status(job, current_status)
            logger.info(f"Job {job.id} status updated: {job.status} -> {current_status}")
            return JobResponse.model_validate(updated_job)

        return JobResponse.model_validate(job)
    except Exception as e:
        logger.error(f"Failed to refresh status for job {job.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh status: {str(e)}")


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a job record (does not cancel running job)."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this job")

    # Warn if job is still running
    if job.status in [JobStatusEnum.PENDING, JobStatusEnum.QUEUED, JobStatusEnum.RUNNING]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete running job. Please cancel it first."
        )

    job_repo.delete(job)
    logger.info(f"Job {job.id} deleted")
