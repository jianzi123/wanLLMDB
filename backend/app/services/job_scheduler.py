"""
Job scheduler service for managing job queue and execution.
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.job import Job, JobStatusEnum, JobTypeEnum
from app.repositories.job_repository import JobRepository
from app.repositories.job_queue_repository import JobQueueRepository, ProjectQuotaRepository
from app.executors import ExecutorFactory

logger = logging.getLogger(__name__)


class JobScheduler:
    """
    Job scheduler for queue management and job submission.

    Responsibilities:
    1. Enqueue jobs when submitted
    2. Check quota availability
    3. Schedule pending jobs when resources are available
    4. Update quota usage when jobs start/finish
    """

    def __init__(self, db: Session):
        self.db = db
        self.job_repo = JobRepository(db)
        self.queue_repo = JobQueueRepository(db)
        self.quota_repo = ProjectQuotaRepository(db)

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
            from datetime import datetime
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

    def check_quota_availability(self, job: Job) -> bool:
        """Check if quota is available for the job."""
        quota = self.quota_repo.get_or_create(job.project_id)

        if not quota.enforce_quota:
            return True

        return quota.has_available_quota(
            job.cpu_request,
            job.memory_request,
            job.gpu_request
        )

    def schedule_pending_jobs(self, project_id: Optional[str] = None) -> int:
        """
        Schedule pending jobs from queues.

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
        """Schedule jobs from a specific queue."""
        scheduled_count = 0

        # Check if queue has capacity
        if queue.running_jobs >= queue.max_concurrent_jobs:
            logger.debug(f"Queue {queue.id} at max capacity ({queue.running_jobs}/{queue.max_concurrent_jobs})")
            return 0

        # Get pending jobs from queue, ordered by position
        pending_jobs = self.db.query(Job).filter(
            Job.queue_id == queue.id,
            Job.status == JobStatusEnum.QUEUED
        ).order_by(Job.queue_position).all()

        for job in pending_jobs:
            # Check queue capacity
            if queue.running_jobs >= queue.max_concurrent_jobs:
                break

            # Check quota availability
            if not self.check_quota_availability(job):
                logger.debug(f"Insufficient quota for job {job.id}")
                continue

            # Try to submit job
            if self._submit_job(job):
                scheduled_count += 1
                queue.running_jobs += 1
            else:
                logger.error(f"Failed to submit job {job.id}")

        return scheduled_count

    def _submit_job(self, job: Job) -> bool:
        """Submit a job to executor."""
        try:
            # Allocate quota
            quota = self.quota_repo.get_or_create(job.project_id)
            if not self.quota_repo.allocate_resources(
                quota,
                job.cpu_request,
                job.memory_request,
                job.gpu_request,
                job.job_type
            ):
                logger.warning(f"Failed to allocate quota for job {job.id}")
                return False

            # Submit to executor
            executor = ExecutorFactory.get_executor(job.executor)
            external_id = executor.submit_job(job)

            # Update job
            job.external_id = external_id
            job.status = JobStatusEnum.RUNNING
            from datetime import datetime
            job.started_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(job)

            logger.info(f"Job {job.id} submitted successfully with external ID: {external_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to submit job {job.id}: {e}")

            # Release quota if submission failed
            try:
                quota = self.quota_repo.get_by_project(job.project_id)
                if quota:
                    self.quota_repo.release_resources(
                        quota,
                        job.cpu_request,
                        job.memory_request,
                        job.gpu_request,
                        job.job_type
                    )
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
            quota = self.quota_repo.get_by_project(job.project_id)
            if quota:
                self.quota_repo.release_resources(
                    quota,
                    job.cpu_request,
                    job.memory_request,
                    job.gpu_request,
                    job.job_type
                )
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
                        from datetime import datetime
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
            from datetime import datetime

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


def extract_resource_requirements(job: Job) -> tuple:
    """
    Extract resource requirements from executor_config.

    Returns:
        Tuple of (cpu_cores, memory_gb, gpu_count)
    """
    config = job.executor_config
    cpu = 1.0
    memory = 2.0
    gpu = 0

    if "resources" in config:
        resources = config["resources"]
        if "requests" in resources:
            requests = resources["requests"]

            # Parse CPU
            if "cpu" in requests:
                cpu_str = str(requests["cpu"])
                if cpu_str.endswith('m'):  # millicores
                    cpu = float(cpu_str[:-1]) / 1000
                else:
                    cpu = float(cpu_str)

            # Parse memory
            if "memory" in requests:
                mem_str = str(requests["memory"])
                if mem_str.endswith('Gi'):
                    memory = float(mem_str[:-2])
                elif mem_str.endswith('Mi'):
                    memory = float(mem_str[:-2]) / 1024
                elif mem_str.endswith('G'):
                    memory = float(mem_str[:-1])
                elif mem_str.endswith('M'):
                    memory = float(mem_str[:-1]) / 1024
                else:
                    memory = float(mem_str) / (1024 ** 3)  # Assume bytes

            # Parse GPU
            if "nvidia.com/gpu" in requests:
                gpu = int(requests["nvidia.com/gpu"])

    # Slurm config
    elif "cpus_per_task" in config:
        cpu = float(config.get("cpus_per_task", 1))

        # Parse memory
        mem_str = config.get("mem", "2G")
        if mem_str.endswith("GB"):
            memory = float(mem_str[:-2])
        elif mem_str.endswith("MB"):
            memory = float(mem_str[:-2]) / 1024
        else:
            memory = 2.0

        gpu = config.get("gpus_per_node", 0) * config.get("nodes", 1)

    return (cpu, memory, gpu)
