"""
Scheduling policies for job selection and prioritization.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from app.models.job import Job, JobStatusEnum
from app.models.job_queue import JobQueue
import logging

logger = logging.getLogger(__name__)


class SchedulingPolicy(ABC):
    """
    Abstract base class for scheduling policies.

    A scheduling policy determines which job to schedule next from a queue.
    """

    @abstractmethod
    def select_next_job(self, queue: JobQueue, pending_jobs: List[Job]) -> Optional[Job]:
        """
        Select the next job to schedule from a list of pending jobs.

        Args:
            queue: The job queue
            pending_jobs: List of jobs in QUEUED status

        Returns:
            The job to schedule next, or None if no suitable job found
        """
        pass

    def should_preempt(self, running_jobs: List[Job], new_job: Job) -> Optional[Job]:
        """
        Determine if a running job should be preempted for a new job.

        Args:
            running_jobs: List of currently running jobs
            new_job: The new job requesting resources

        Returns:
            Job to preempt, or None if no preemption needed
        """
        # Default: no preemption
        return None


class FIFOPolicy(SchedulingPolicy):
    """
    First-In-First-Out scheduling policy.

    Jobs are scheduled in the order they were enqueued (by queue_position).
    """

    def select_next_job(self, queue: JobQueue, pending_jobs: List[Job]) -> Optional[Job]:
        """Select job with lowest queue position (earliest submission)."""
        if not pending_jobs:
            return None

        # Sort by queue position (FIFO)
        sorted_jobs = sorted(pending_jobs, key=lambda j: j.queue_position or float('inf'))
        return sorted_jobs[0]


class PriorityPolicy(SchedulingPolicy):
    """
    Priority-based scheduling policy.

    Jobs are scheduled based on priority (higher priority first),
    with FIFO as tiebreaker.
    """

    def select_next_job(self, queue: JobQueue, pending_jobs: List[Job]) -> Optional[Job]:
        """Select job with highest priority."""
        if not pending_jobs:
            return None

        # Sort by priority (descending) then queue position (ascending)
        sorted_jobs = sorted(
            pending_jobs,
            key=lambda j: (-getattr(j, 'priority', 0), j.queue_position or float('inf'))
        )
        return sorted_jobs[0]

    def should_preempt(self, running_jobs: List[Job], new_job: Job) -> Optional[Job]:
        """
        Preempt lowest priority running job if new job has higher priority.
        """
        if not running_jobs:
            return None

        new_priority = getattr(new_job, 'priority', 0)

        # Find lowest priority running job
        lowest_priority_job = min(
            running_jobs,
            key=lambda j: getattr(j, 'priority', 0)
        )

        lowest_priority = getattr(lowest_priority_job, 'priority', 0)

        # Preempt if new job has significantly higher priority
        if new_priority > lowest_priority + 10:  # Threshold to avoid thrashing
            logger.info(
                f"Preemption candidate: job {lowest_priority_job.id} "
                f"(priority {lowest_priority}) for job {new_job.id} (priority {new_priority})"
            )
            return lowest_priority_job

        return None


class FairSharePolicy(SchedulingPolicy):
    """
    Fair-share scheduling policy.

    Attempts to give each user/project a fair share of resources based on
    their historical usage.
    """

    def __init__(self, lookback_hours: int = 24):
        """
        Initialize fair-share policy.

        Args:
            lookback_hours: Hours to look back for usage calculation
        """
        self.lookback_hours = lookback_hours

    def select_next_job(self, queue: JobQueue, pending_jobs: List[Job]) -> Optional[Job]:
        """
        Select job from user with lowest fair-share score.

        Fair-share score = recent_usage / fair_share_target
        Lower score = higher priority
        """
        if not pending_jobs:
            return None

        # Calculate fair-share scores for each user
        user_scores = self._calculate_fairshare_scores(pending_jobs)

        # Select job from user with lowest score
        selected_job = min(
            pending_jobs,
            key=lambda j: (
                user_scores.get(j.user_id, 0),
                j.queue_position or float('inf')
            )
        )

        return selected_job

    def _calculate_fairshare_scores(self, jobs: List[Job]) -> dict:
        """
        Calculate fair-share score for each user.

        Returns:
            Dict mapping user_id to fair-share score
        """
        from datetime import datetime, timedelta
        from sqlalchemy import func

        # Get unique users
        user_ids = set(j.user_id for j in jobs)

        # Calculate recent usage for each user
        # This would need database access - simplified here
        scores = {}
        for user_id in user_ids:
            # TODO: Query recent resource usage from completed jobs
            # For now, use simple count as proxy
            user_job_count = sum(1 for j in jobs if j.user_id == user_id)
            scores[user_id] = user_job_count

        return scores


class BackfillPolicy(SchedulingPolicy):
    """
    Backfill scheduling policy.

    Allows smaller jobs to "backfill" and run while larger jobs wait,
    if they won't delay the larger job.
    """

    def __init__(self, base_policy: SchedulingPolicy = None):
        """
        Initialize backfill policy.

        Args:
            base_policy: Base policy to use for primary scheduling
        """
        self.base_policy = base_policy or FIFOPolicy()

    def select_next_job(self, queue: JobQueue, pending_jobs: List[Job]) -> Optional[Job]:
        """
        Select job using backfill algorithm.

        1. Reserve resources for highest priority job
        2. Try to backfill smaller jobs that fit in gaps
        """
        if not pending_jobs:
            return None

        # Get highest priority job (by base policy)
        primary_job = self.base_policy.select_next_job(queue, pending_jobs)

        if not primary_job:
            return None

        # Check if there are smaller jobs that could backfill
        # TODO: Implement backfill logic with resource reservation
        # For now, just use base policy
        return primary_job
