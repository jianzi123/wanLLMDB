"""
Job executors for cluster integration.
"""

from typing import Dict, Any, Optional
from app.models.job import JobExecutorEnum
from app.executors.base import BaseExecutor
from app.executors.kubernetes_executor import KubernetesExecutor
from app.executors.slurm_executor import SlurmExecutor


class ExecutorFactory:
    """Factory for creating job executors."""

    _executors: Dict[JobExecutorEnum, BaseExecutor] = {}

    @classmethod
    def initialize(cls, config: Dict[str, Any]) -> None:
        """
        Initialize executors with global configuration.

        Args:
            config: Configuration dictionary
                {
                    "kubernetes": {
                        "kubeconfig_path": "/path/to/kubeconfig",
                        "default_namespace": "wanllmdb-jobs",
                    },
                    "slurm": {
                        "rest_api_url": "http://slurm:6820",
                        "auth_token": "user:token",
                    }
                }
        """
        if "kubernetes" in config:
            cls._executors[JobExecutorEnum.KUBERNETES] = KubernetesExecutor(
                config["kubernetes"]
            )

        if "slurm" in config:
            cls._executors[JobExecutorEnum.SLURM] = SlurmExecutor(
                config["slurm"]
            )

    @classmethod
    def get_executor(cls, executor_type: JobExecutorEnum) -> BaseExecutor:
        """
        Get executor instance.

        Args:
            executor_type: Type of executor

        Returns:
            Executor instance

        Raises:
            ValueError: If executor type is not configured
        """
        if executor_type not in cls._executors:
            raise ValueError(f"Executor {executor_type} not configured")

        return cls._executors[executor_type]

    @classmethod
    def is_configured(cls, executor_type: JobExecutorEnum) -> bool:
        """Check if executor is configured."""
        return executor_type in cls._executors


__all__ = [
    "BaseExecutor",
    "KubernetesExecutor",
    "SlurmExecutor",
    "ExecutorFactory",
]
