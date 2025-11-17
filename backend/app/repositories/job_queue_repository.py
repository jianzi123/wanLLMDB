"""
Job queue and quota repository for database operations.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.job_queue import JobQueue, ProjectQuota
from app.models.job import Job, JobStatusEnum, JobTypeEnum


class JobQueueRepository:
    """Repository for job queue operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, queue_data: Dict[str, Any]) -> JobQueue:
        """Create a new job queue."""
        queue = JobQueue(**queue_data)
        self.db.add(queue)
        self.db.commit()
        self.db.refresh(queue)
        return queue

    def get_by_id(self, queue_id: UUID) -> Optional[JobQueue]:
        """Get queue by ID."""
        return self.db.query(JobQueue).filter(JobQueue.id == queue_id).first()

    def get_by_project(self, project_id: UUID) -> List[JobQueue]:
        """Get all queues for a project."""
        return self.db.query(JobQueue).filter(JobQueue.project_id == project_id).all()

    def get_default_queue(self, project_id: UUID) -> Optional[JobQueue]:
        """
        Get or create default queue for a project.

        If project has no queues, create a default one.
        """
        queues = self.get_by_project(project_id)

        if queues:
            # Return first enabled queue with highest priority
            enabled_queues = [q for q in queues if q.enabled]
            if enabled_queues:
                return max(enabled_queues, key=lambda q: q.priority)
            return queues[0]

        # Create default queue
        default_queue = self.create({
            "project_id": project_id,
            "name": "default",
            "description": "Default job queue",
            "priority": 0,
            "max_concurrent_jobs": 10,
            "enabled": True,
        })
        return default_queue

    def update(self, queue: JobQueue, update_data: Dict[str, Any]) -> JobQueue:
        """Update queue."""
        for key, value in update_data.items():
            if value is not None and hasattr(queue, key):
                setattr(queue, key, value)

        self.db.commit()
        self.db.refresh(queue)
        return queue

    def update_stats(self, queue: JobQueue) -> JobQueue:
        """Update queue statistics based on current jobs."""
        from sqlalchemy import func, Integer

        # Count jobs by status
        stats = self.db.query(
            func.count(Job.id).label('total'),
            func.sum(
                (Job.status == JobStatusEnum.RUNNING).cast(Integer)
            ).label('running'),
            func.sum(
                (Job.status.in_([JobStatusEnum.PENDING, JobStatusEnum.QUEUED])).cast(Integer)
            ).label('pending'),
        ).filter(Job.queue_id == queue.id).first()

        queue.total_jobs = stats.total or 0
        queue.running_jobs = stats.running or 0
        queue.pending_jobs = stats.pending or 0

        self.db.commit()
        self.db.refresh(queue)
        return queue

    def delete(self, queue: JobQueue) -> None:
        """Delete queue."""
        self.db.delete(queue)
        self.db.commit()


class ProjectQuotaRepository:
    """Repository for project quota operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, quota_data: Dict[str, Any]) -> ProjectQuota:
        """Create a new project quota."""
        quota = ProjectQuota(**quota_data)
        self.db.add(quota)
        self.db.commit()
        self.db.refresh(quota)
        return quota

    def get_by_id(self, quota_id: UUID) -> Optional[ProjectQuota]:
        """Get quota by ID."""
        return self.db.query(ProjectQuota).filter(ProjectQuota.id == quota_id).first()

    def get_by_project(self, project_id: UUID) -> Optional[ProjectQuota]:
        """Get quota for a project."""
        return self.db.query(ProjectQuota).filter(ProjectQuota.project_id == project_id).first()

    def get_or_create(self, project_id: UUID) -> ProjectQuota:
        """Get or create quota for a project."""
        quota = self.get_by_project(project_id)

        if not quota:
            # Create default quota
            quota = self.create({
                "project_id": project_id,
                "cpu_quota": 100.0,
                "memory_quota": 500.0,
                "gpu_quota": 10,
                "max_concurrent_jobs": 50,
                "enforce_quota": True,
            })

        return quota

    def update(self, quota: ProjectQuota, update_data: Dict[str, Any]) -> ProjectQuota:
        """Update quota."""
        for key, value in update_data.items():
            if value is not None and hasattr(quota, key):
                setattr(quota, key, value)

        self.db.commit()
        self.db.refresh(quota)
        return quota

    def allocate_resources(
        self,
        quota: ProjectQuota,
        cpu: float,
        memory: float,
        gpu: int,
        job_type: JobTypeEnum
    ) -> bool:
        """
        Allocate resources for a job.

        Returns True if allocation succeeded, False if quota exceeded.
        """
        if not quota.enforce_quota:
            # Quota not enforced, allow allocation
            quota.used_cpu += cpu
            quota.used_memory += memory
            quota.used_gpu += gpu
            quota.current_jobs += 1

            if job_type == JobTypeEnum.TRAINING:
                quota.current_training_jobs += 1
            elif job_type == JobTypeEnum.INFERENCE:
                quota.current_inference_jobs += 1
            elif job_type == JobTypeEnum.WORKFLOW:
                quota.current_workflow_jobs += 1

            self.db.commit()
            return True

        # Check if resources available
        if not quota.has_available_quota(cpu, memory, gpu):
            return False

        # Check job type limits
        if job_type == JobTypeEnum.TRAINING and quota.max_training_jobs:
            if quota.current_training_jobs >= quota.max_training_jobs:
                return False
        elif job_type == JobTypeEnum.INFERENCE and quota.max_inference_jobs:
            if quota.current_inference_jobs >= quota.max_inference_jobs:
                return False
        elif job_type == JobTypeEnum.WORKFLOW and quota.max_workflow_jobs:
            if quota.current_workflow_jobs >= quota.max_workflow_jobs:
                return False

        # Allocate resources
        quota.used_cpu += cpu
        quota.used_memory += memory
        quota.used_gpu += gpu
        quota.current_jobs += 1

        if job_type == JobTypeEnum.TRAINING:
            quota.current_training_jobs += 1
        elif job_type == JobTypeEnum.INFERENCE:
            quota.current_inference_jobs += 1
        elif job_type == JobTypeEnum.WORKFLOW:
            quota.current_workflow_jobs += 1

        self.db.commit()
        self.db.refresh(quota)
        return True

    def release_resources(
        self,
        quota: ProjectQuota,
        cpu: float,
        memory: float,
        gpu: int,
        job_type: JobTypeEnum
    ) -> None:
        """Release allocated resources."""
        quota.used_cpu = max(0, quota.used_cpu - cpu)
        quota.used_memory = max(0, quota.used_memory - memory)
        quota.used_gpu = max(0, quota.used_gpu - gpu)
        quota.current_jobs = max(0, quota.current_jobs - 1)

        if job_type == JobTypeEnum.TRAINING:
            quota.current_training_jobs = max(0, quota.current_training_jobs - 1)
        elif job_type == JobTypeEnum.INFERENCE:
            quota.current_inference_jobs = max(0, quota.current_inference_jobs - 1)
        elif job_type == JobTypeEnum.WORKFLOW:
            quota.current_workflow_jobs = max(0, quota.current_workflow_jobs - 1)

        self.db.commit()
        self.db.refresh(quota)

    def delete(self, quota: ProjectQuota) -> None:
        """Delete quota."""
        self.db.delete(quota)
        self.db.commit()
