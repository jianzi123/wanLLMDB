"""
Base executor interface for job execution.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.models.job import Job, JobTypeEnum, JobStatusEnum


class ExecutorError(Exception):
    """Base exception for executor errors."""
    pass


class JobSubmissionError(ExecutorError):
    """Error during job submission."""
    pass


class JobCancellationError(ExecutorError):
    """Error during job cancellation."""
    pass


class JobStatusError(ExecutorError):
    """Error getting job status."""
    pass


class BaseExecutor(ABC):
    """
    Base class for job executors.

    Executors are responsible for:
    1. Submitting jobs to the target platform (K8s, Slurm, etc.)
    2. Monitoring job status
    3. Cancelling jobs
    4. Retrieving job logs and outputs
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize executor.

        Args:
            config: Executor-specific configuration
        """
        self.config = config or {}

    @abstractmethod
    def submit_job(self, job: Job) -> str:
        """
        Submit a job to the executor.

        Args:
            job: Job object containing configuration

        Returns:
            External job ID (K8s job name, Slurm job ID, etc.)

        Raises:
            JobSubmissionError: If job submission fails
        """
        pass

    @abstractmethod
    def get_job_status(self, external_id: str) -> JobStatusEnum:
        """
        Get current job status.

        Args:
            external_id: External job identifier

        Returns:
            Current job status

        Raises:
            JobStatusError: If status retrieval fails
        """
        pass

    @abstractmethod
    def cancel_job(self, external_id: str) -> None:
        """
        Cancel a running job.

        Args:
            external_id: External job identifier

        Raises:
            JobCancellationError: If cancellation fails
        """
        pass

    @abstractmethod
    def get_job_logs(self, external_id: str) -> str:
        """
        Get job logs.

        Args:
            external_id: External job identifier

        Returns:
            Job logs as string

        Raises:
            ExecutorError: If log retrieval fails
        """
        pass

    @abstractmethod
    def get_job_metrics(self, external_id: str) -> Dict[str, Any]:
        """
        Get job metrics (resource usage, etc.).

        Args:
            external_id: External job identifier

        Returns:
            Dictionary of metrics

        Raises:
            ExecutorError: If metrics retrieval fails
        """
        pass

    def validate_config(self, job: Job) -> None:
        """
        Validate job configuration.

        Args:
            job: Job to validate

        Raises:
            ValueError: If configuration is invalid
        """
        if not job.executor_config:
            raise ValueError("executor_config is required")

    def _build_training_spec(self, job: Job) -> Dict[str, Any]:
        """
        Build training job specification.

        Args:
            job: Job object

        Returns:
            Job specification dictionary
        """
        raise NotImplementedError("Subclass must implement _build_training_spec")

    def _build_inference_spec(self, job: Job) -> Dict[str, Any]:
        """
        Build inference job specification.

        Args:
            job: Job object

        Returns:
            Job specification dictionary
        """
        raise NotImplementedError("Subclass must implement _build_inference_spec")

    def _build_workflow_spec(self, job: Job) -> Dict[str, Any]:
        """
        Build workflow job specification.

        Args:
            job: Job object

        Returns:
            Job specification dictionary
        """
        raise NotImplementedError("Subclass must implement _build_workflow_spec")
