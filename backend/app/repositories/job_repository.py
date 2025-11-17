"""
Job repository for database operations.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.models.job import Job, JobStatusEnum, JobTypeEnum, JobExecutorEnum


class JobRepository:
    """Repository for job database operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, job_data: Dict[str, Any]) -> Job:
        """Create a new job."""
        job = Job(**job_data)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_by_id(self, job_id: UUID) -> Optional[Job]:
        """Get job by ID."""
        return self.db.query(Job).filter(Job.id == job_id).first()

    def get_by_external_id(self, external_id: str, executor: JobExecutorEnum) -> Optional[Job]:
        """Get job by external ID (K8s job name or Slurm job ID)."""
        return self.db.query(Job).filter(
            and_(
                Job.external_id == external_id,
                Job.executor == executor
            )
        ).first()

    def list(
        self,
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        job_type: Optional[JobTypeEnum] = None,
        executor: Optional[JobExecutorEnum] = None,
        status: Optional[JobStatusEnum] = None,
        statuses: Optional[List[JobStatusEnum]] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "submitted_at",
        order_desc: bool = True,
    ) -> tuple[List[Job], int]:
        """
        List jobs with filters and pagination.

        Returns:
            Tuple of (jobs, total_count)
        """
        query = self.db.query(Job)

        # Apply filters
        if project_id:
            query = query.filter(Job.project_id == project_id)
        if user_id:
            query = query.filter(Job.user_id == user_id)
        if run_id:
            query = query.filter(Job.run_id == run_id)
        if job_type:
            query = query.filter(Job.job_type == job_type)
        if executor:
            query = query.filter(Job.executor == executor)
        if status:
            query = query.filter(Job.status == status)
        if statuses:
            query = query.filter(Job.status.in_(statuses))
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Job.name.ilike(search_pattern),
                    Job.description.ilike(search_pattern),
                )
            )

        # Get total count
        total = query.count()

        # Apply ordering
        if hasattr(Job, order_by):
            order_column = getattr(Job, order_by)
            if order_desc:
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())

        # Apply pagination
        jobs = query.offset(skip).limit(limit).all()

        return jobs, total

    def update(self, job: Job, update_data: Dict[str, Any]) -> Job:
        """Update job."""
        for key, value in update_data.items():
            if value is not None and hasattr(job, key):
                setattr(job, key, value)

        self.db.commit()
        self.db.refresh(job)
        return job

    def delete(self, job: Job) -> None:
        """Delete job."""
        self.db.delete(job)
        self.db.commit()

    def get_stats(
        self,
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Get job statistics."""
        query = self.db.query(Job)

        if project_id:
            query = query.filter(Job.project_id == project_id)
        if user_id:
            query = query.filter(Job.user_id == user_id)

        total = query.count()

        # Count by status
        status_counts = {}
        for status in JobStatusEnum:
            count = query.filter(Job.status == status).count()
            status_counts[status.value] = count

        # Count by type
        type_counts = {}
        for job_type in JobTypeEnum:
            count = query.filter(Job.job_type == job_type).count()
            type_counts[job_type.value] = count

        # Count by executor
        executor_counts = {}
        for executor in JobExecutorEnum:
            count = query.filter(Job.executor == executor).count()
            executor_counts[executor.value] = count

        return {
            "total": total,
            "by_status": status_counts,
            "by_type": type_counts,
            "by_executor": executor_counts,
        }

    def get_active_jobs(
        self,
        executor: Optional[JobExecutorEnum] = None,
    ) -> List[Job]:
        """Get all active jobs (pending, queued, or running)."""
        active_statuses = [
            JobStatusEnum.PENDING,
            JobStatusEnum.QUEUED,
            JobStatusEnum.RUNNING,
        ]

        query = self.db.query(Job).filter(Job.status.in_(active_statuses))

        if executor:
            query = query.filter(Job.executor == executor)

        return query.all()

    def update_status(
        self,
        job: Job,
        status: JobStatusEnum,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None,
    ) -> Job:
        """Update job status and related fields."""
        from datetime import datetime

        job.status = status

        if error_message:
            job.error_message = error_message
        if exit_code is not None:
            job.exit_code = exit_code

        # Update timestamps
        if status == JobStatusEnum.RUNNING and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in [JobStatusEnum.SUCCEEDED, JobStatusEnum.FAILED, JobStatusEnum.CANCELLED, JobStatusEnum.TIMEOUT]:
            if not job.finished_at:
                job.finished_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(job)
        return job
