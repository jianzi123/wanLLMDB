"""
Refactored job scheduler using pluggable policies and quota providers.
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.job import Job, JobStatusEnum, JobTypeEnum
from app.repositories.job_repository import JobRepository
from app.repositories.job_queue_repository import JobQueueRepository
from app.executors import ExecutorFactory
from app.scheduling.types import Resources
from app.scheduling.policies import SchedulingPolicy, FIFOPolicy
from app.scheduling.quota_providers import QuotaProvider, LocalQuotaProvider

logger = logging.getLogger(__name__)


class JobScheduler:
    """
    Refactored job scheduler with pluggable policies and quota providers.

    Responsibilities:
    1. Enqueue jobs when submitted
    2. Select next job to schedule using SchedulingPolicy
    3. Check quota using QuotaProvider
    4. Submit jobs to executors
    5. Sync job status and release quotas
    """

    def __init__(
        self,
        db: Session,
        policy: Optional[SchedulingPolicy] = None,
        quota_provider: Optional[QuotaProvider] = None
    ):
        """
        Initialize job scheduler.

        Args:
            db: Database session
            policy: Scheduling policy (defaults to FIFO)
            quota_provider: Quota provider (defaults to LocalQuotaProvider)
        """
        self.db = db
        self.job_repo = JobRepository(db)
        self.queue_repo = JobQueueRepository(db)

        # Use dependency injection for policy and quota provider
        self.policy = policy or FIFOPolicy()
        self.quota_provider = quota_provider or LocalQuotaProvider(db)

        logger.info(
            f"JobScheduler initialized with policy={type(self.policy).__name__}, "
            f"quota_provider={type(self.quota_provider).__name__}"
        )

    def enqueue_job(self, job: Job) -> bool:
        """
        Enqueue a job for execution.

        Returns:
            True if job was successfully enqueued, False otherwise
        """
        try:
            # Get or create default queue for project
            queue = self.queue_repo.get_default_queue(job.project_id)
            if not queue:
                logger.error(f"No queue available for project {job.project_id}")
                return False

            if not queue.enabled:
                logger.error(f"Queue {queue.id} is disabled")
                return False

            # Assign job to queue
            job.queue_id = queue.id

            # Calculate queue position
            from sqlalchemy import func
            max_position = self.db.query(func.max(Job.queue_position)).filter(
                Job.queue_id == queue.id,
                Job.status.in_([JobStatusEnum.PENDING, JobStatusEnum.QUEUED])
            ).scalar()

            job.queue_position = (max_position or 0) + 1

            # Set enqueued timestamp
            job.enqueued_at = datetime.utcnow()

            # Update job status
            job.status = JobStatusEnum.QUEUED

            self.db.commit()
            self.db.refresh(job)

            logger.info(f"Job {job.id} enqueued to queue {queue.id} at position {job.queue_position}")
            return True

        except Exception as e:
            logger.error(f"Failed to enqueue job {job.id}: {e}")
            self.db.rollback()
            return False

    def schedule_pending_jobs(self, project_id: Optional[str] = None) -> int:
        """
        Schedule pending jobs from queues using configured policy.

        Args:
            project_id: If specified, only schedule jobs from this project

        Returns:
            Number of jobs successfully scheduled
        """
        scheduled_count = 0

        # Get queues to process
        if project_id:
            queues = self.queue_repo.get_by_project(project_id)
        else:
            # Get all enabled queues, ordered by priority
            from app.models.job_queue import JobQueue
            queues = self.db.query(JobQueue).filter(
                JobQueue.enabled == True
            ).order_by(JobQueue.priority.desc()).all()

        for queue in queues:
            try:
                scheduled = self._schedule_queue_jobs(queue)
                scheduled_count += scheduled
            except Exception as e:
                logger.error(f"Error scheduling jobs from queue {queue.id}: {e}")

        return scheduled_count

    def _schedule_queue_jobs(self, queue) -> int:
        """Schedule jobs from a specific queue using policy."""
        scheduled_count = 0

        # Check if queue has capacity
        if queue.running_jobs >= queue.max_concurrent_jobs:
            logger.debug(f"Queue {queue.id} at max capacity ({queue.running_jobs}/{queue.max_concurrent_jobs})")
            return 0

        # Get pending jobs from queue
        pending_jobs = self.db.query(Job).filter(
            Job.queue_id == queue.id,
            Job.status == JobStatusEnum.QUEUED
        ).all()

        if not pending_jobs:
            return 0

        # Schedule jobs while capacity available
        while queue.running_jobs < queue.max_concurrent_jobs and pending_jobs:
            # Use policy to select next job
            job = self.policy.select_next_job(queue, pending_jobs)

            if not job:
                break

            # Remove from pending list
            pending_jobs.remove(job)

            # Check quota and submit
            if self._try_submit_job(job):
                scheduled_count += 1
                queue.running_jobs += 1
            else:
                # If job can't be scheduled, try next one
                logger.debug(f"Job {job.id} cannot be scheduled (quota or other constraint)")
                continue

        return scheduled_count

    def _try_submit_job(self, job: Job) -> bool:
        """
        Try to submit a job - check quota and submit to executor.

        Returns:
            True if job was submitted successfully
        """
        # Extract resources
        resources = Resources(
            cpu=job.cpu_request,
            memory=job.memory_request,
            gpu=job.gpu_request
        )

        # Check quota
        if not self.quota_provider.check_quota(job.project_id, resources, job.job_type):
            logger.debug(f"Insufficient quota for job {job.id}")
            return False

        # Allocate quota
        if not self.quota_provider.allocate_quota(job.project_id, resources, job.job_type):
            logger.warning(f"Failed to allocate quota for job {job.id}")
            return False

        # Submit to executor
        try:
            executor = ExecutorFactory.get_executor(job.executor)
            external_id = executor.submit_job(job)

            # Update job
            job.external_id = external_id
            job.status = JobStatusEnum.RUNNING
            job.started_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(job)

            logger.info(f"Job {job.id} submitted successfully with external ID: {external_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to submit job {job.id}: {e}")

            # Release quota if submission failed
            try:
                self.quota_provider.release_quota(job.project_id, resources, job.job_type)
            except Exception as release_error:
                logger.error(f"Failed to release quota: {release_error}")

            self.db.rollback()
            return False

    def on_job_completed(self, job: Job) -> None:
        """
        Handle job completion - release quota.

        Call this when a job finishes (succeeded/failed/cancelled/timeout).
        """
        try:
            resources = Resources(
                cpu=job.cpu_request,
                memory=job.memory_request,
                gpu=job.gpu_request
            )

            self.quota_provider.release_quota(job.project_id, resources, job.job_type)
            logger.info(f"Released quota for job {job.id}")

            # Update queue stats
            if job.queue_id:
                queue = self.queue_repo.get_by_id(job.queue_id)
                if queue:
                    queue.running_jobs = max(0, queue.running_jobs - 1)
                    self.db.commit()

        except Exception as e:
            logger.error(f"Error releasing resources for job {job.id}: {e}")

    def sync_job_status(self, job: Job) -> bool:
        """
        Sync job status from executor and update associated Run.

        Returns True if status changed.
        """
        try:
            executor = ExecutorFactory.get_executor(job.executor)
            current_status = executor.get_job_status(job.external_id)

            if current_status != job.status:
                old_status = job.status
                job.status = current_status

                # Handle completion
                if current_status in [
                    JobStatusEnum.SUCCEEDED,
                    JobStatusEnum.FAILED,
                    JobStatusEnum.CANCELLED,
                    JobStatusEnum.TIMEOUT
                ]:
                    if not job.finished_at:
                        job.finished_at = datetime.utcnow()

                    # Release quota
                    self.on_job_completed(job)

                # Sync associated Run status if exists
                self._sync_run_status(job, current_status)

                self.db.commit()
                logger.info(f"Job {job.id} status updated: {old_status} -> {current_status}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to sync job {job.id} status: {e}")
            return False

    def _sync_run_status(self, job: Job, job_status: JobStatusEnum) -> None:
        """
        Sync Run status based on Job status.

        Args:
            job: The job whose run should be synced
            job_status: Current job status
        """
        if not job.run_id:
            return  # No associated run

        try:
            from app.models.run import Run, RunStateEnum

            run = self.db.query(Run).filter(Run.id == job.run_id).first()
            if not run:
                logger.warning(f"Run {job.run_id} not found for job {job.id}")
                return

            # Map Job status to Run state
            status_mapping = {
                JobStatusEnum.PENDING: None,  # Don't update run when job is pending
                JobStatusEnum.QUEUED: None,   # Don't update run when job is queued
                JobStatusEnum.RUNNING: RunStateEnum.RUNNING,
                JobStatusEnum.SUCCEEDED: RunStateEnum.FINISHED,
                JobStatusEnum.FAILED: RunStateEnum.CRASHED,
                JobStatusEnum.CANCELLED: RunStateEnum.KILLED,
                JobStatusEnum.TIMEOUT: RunStateEnum.CRASHED,
            }

            new_run_state = status_mapping.get(job_status)
            if new_run_state and run.state != new_run_state:
                old_state = run.state
                run.state = new_run_state

                # Update finished_at timestamp for terminal states
                if new_run_state in [RunStateEnum.FINISHED, RunStateEnum.CRASHED, RunStateEnum.KILLED]:
                    if not run.finished_at:
                        run.finished_at = datetime.utcnow()

                logger.info(f"Run {run.id} state synced: {old_state} -> {new_run_state} (from job {job.id})")

        except Exception as e:
            logger.error(f"Failed to sync run status for job {job.id}: {e}")

    def sync_all_active_jobs(self) -> int:
        """
        Sync status for all active jobs.

        Returns number of jobs updated.
        """
        updated_count = 0

        active_jobs = self.job_repo.get_active_jobs()

        for job in active_jobs:
            if job.external_id:  # Only sync if job has been submitted to executor
                if self.sync_job_status(job):
                    updated_count += 1

        return updated_count


def create_scheduler(
    db: Session,
    policy_type: str = "fifo",
    quota_provider_type: str = "local",
    **kwargs
) -> JobScheduler:
    """
    Factory function to create a JobScheduler with specified policy and provider.

    Args:
        db: Database session
        policy_type: Type of scheduling policy ("fifo", "priority", "fairshare")
        quota_provider_type: Type of quota provider ("local", "k8s", "slurm")
        **kwargs: Additional arguments for providers

    Returns:
        Configured JobScheduler instance
    """
    from app.scheduling.policies import FIFOPolicy, PriorityPolicy, FairSharePolicy
    from app.scheduling.quota_providers import LocalQuotaProvider, K8sQuotaProvider, SlurmQuotaProvider

    # Create policy
    policy_map = {
        "fifo": FIFOPolicy,
        "priority": PriorityPolicy,
        "fairshare": FairSharePolicy,
    }

    if policy_type not in policy_map:
        logger.warning(f"Unknown policy type {policy_type}, using FIFO")
        policy_type = "fifo"

    policy = policy_map[policy_type]()

    # Create quota provider
    if quota_provider_type == "local":
        quota_provider = LocalQuotaProvider(db)
    elif quota_provider_type == "k8s":
        namespace = kwargs.get("k8s_namespace", "wanllmdb-jobs")
        quota_provider = K8sQuotaProvider(namespace=namespace)
    elif quota_provider_type == "slurm":
        quota_provider = SlurmQuotaProvider(
            rest_api_url=kwargs.get("slurm_api_url"),
            auth_token=kwargs.get("slurm_auth_token"),
            account_prefix=kwargs.get("slurm_account_prefix", "project-")
        )
    else:
        logger.warning(f"Unknown quota provider {quota_provider_type}, using local")
        quota_provider = LocalQuotaProvider(db)

    return JobScheduler(db, policy=policy, quota_provider=quota_provider)
