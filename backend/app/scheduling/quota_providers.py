"""
Quota providers for different backends (local DB, K8s, Slurm).
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from app.scheduling.types import Resources, QuotaInfo
from app.models.job import JobTypeEnum

logger = logging.getLogger(__name__)


class QuotaProvider(ABC):
    """
    Abstract base class for quota providers.

    A quota provider manages resource quotas and can integrate with
    different backends (local DB, K8s ResourceQuota, Slurm QOS, etc.).
    """

    @abstractmethod
    def get_quota(self, project_id: UUID) -> Optional[QuotaInfo]:
        """
        Get quota information for a project.

        Args:
            project_id: Project ID

        Returns:
            QuotaInfo with limits and current usage, or None if not found
        """
        pass

    @abstractmethod
    def check_quota(self, project_id: UUID, resources: Resources, job_type: JobTypeEnum) -> bool:
        """
        Check if quota is available for requested resources.

        Args:
            project_id: Project ID
            resources: Requested resources
            job_type: Type of job (for per-type limits)

        Returns:
            True if quota available, False otherwise
        """
        pass

    @abstractmethod
    def allocate_quota(
        self,
        project_id: UUID,
        resources: Resources,
        job_type: JobTypeEnum
    ) -> bool:
        """
        Allocate quota for a job.

        Args:
            project_id: Project ID
            resources: Resources to allocate
            job_type: Type of job

        Returns:
            True if allocation succeeded, False if insufficient quota
        """
        pass

    @abstractmethod
    def release_quota(
        self,
        project_id: UUID,
        resources: Resources,
        job_type: JobTypeEnum
    ) -> None:
        """
        Release quota when job completes.

        Args:
            project_id: Project ID
            resources: Resources to release
            job_type: Type of job
        """
        pass

    def sync_quota_state(self) -> None:
        """
        Sync quota state with backend.

        Optional method for providers that need to sync with external systems.
        """
        pass


class LocalQuotaProvider(QuotaProvider):
    """
    Local database-based quota provider.

    Uses the project_quotas table in PostgreSQL.
    """

    def __init__(self, db: Session):
        """
        Initialize local quota provider.

        Args:
            db: Database session
        """
        self.db = db

    def get_quota(self, project_id: UUID) -> Optional[QuotaInfo]:
        """Get quota from database."""
        from app.repositories.job_queue_repository import ProjectQuotaRepository

        quota_repo = ProjectQuotaRepository(self.db)
        quota = quota_repo.get_or_create(project_id)

        if not quota:
            return None

        return QuotaInfo(
            limits=Resources(
                cpu=quota.cpu_quota,
                memory=quota.memory_quota,
                gpu=quota.gpu_quota
            ),
            used=Resources(
                cpu=quota.used_cpu,
                memory=quota.used_memory,
                gpu=quota.used_gpu
            )
        )

    def check_quota(self, project_id: UUID, resources: Resources, job_type: JobTypeEnum) -> bool:
        """Check quota availability."""
        from app.repositories.job_queue_repository import ProjectQuotaRepository

        quota_repo = ProjectQuotaRepository(self.db)
        quota = quota_repo.get_or_create(project_id)

        if not quota.enforce_quota:
            return True

        # Check resource quota
        if not quota.has_available_quota(resources.cpu, resources.memory, resources.gpu):
            return False

        # Check job count limits
        if quota.current_jobs >= quota.max_concurrent_jobs:
            return False

        # Check per-type limits
        if job_type == JobTypeEnum.TRAINING and quota.max_training_jobs:
            if quota.current_training_jobs >= quota.max_training_jobs:
                return False
        elif job_type == JobTypeEnum.INFERENCE and quota.max_inference_jobs:
            if quota.current_inference_jobs >= quota.max_inference_jobs:
                return False
        elif job_type == JobTypeEnum.WORKFLOW and quota.max_workflow_jobs:
            if quota.current_workflow_jobs >= quota.max_workflow_jobs:
                return False

        return True

    def allocate_quota(
        self,
        project_id: UUID,
        resources: Resources,
        job_type: JobTypeEnum
    ) -> bool:
        """Allocate quota."""
        from app.repositories.job_queue_repository import ProjectQuotaRepository

        quota_repo = ProjectQuotaRepository(self.db)
        quota = quota_repo.get_or_create(project_id)

        return quota_repo.allocate_resources(
            quota,
            resources.cpu,
            resources.memory,
            resources.gpu,
            job_type
        )

    def release_quota(
        self,
        project_id: UUID,
        resources: Resources,
        job_type: JobTypeEnum
    ) -> None:
        """Release quota."""
        from app.repositories.job_queue_repository import ProjectQuotaRepository

        quota_repo = ProjectQuotaRepository(self.db)
        quota = quota_repo.get_by_project(project_id)

        if quota:
            quota_repo.release_resources(
                quota,
                resources.cpu,
                resources.memory,
                resources.gpu,
                job_type
            )


class K8sQuotaProvider(QuotaProvider):
    """
    Kubernetes ResourceQuota-based provider.

    Integrates with K8s ResourceQuota objects.
    """

    def __init__(self, namespace: str = "wanllmdb-jobs", create_quotas: bool = True):
        """
        Initialize K8s quota provider.

        Args:
            namespace: K8s namespace to manage quotas in
            create_quotas: Whether to create ResourceQuota objects
        """
        self.namespace = namespace
        self.create_quotas = create_quotas

        try:
            from kubernetes import client, config
            try:
                config.load_incluster_config()
            except:
                config.load_kube_config()

            self.core_v1 = client.CoreV1Api()
        except Exception as e:
            logger.error(f"Failed to initialize K8s client: {e}")
            raise

    def get_quota(self, project_id: UUID) -> Optional[QuotaInfo]:
        """Get quota from K8s ResourceQuota."""
        quota_name = f"project-{project_id}"

        try:
            quota = self.core_v1.read_namespaced_resource_quota(
                name=quota_name,
                namespace=self.namespace
            )

            # Parse quota spec and status
            hard = quota.spec.hard or {}
            used = quota.status.used or {}

            return QuotaInfo(
                limits=Resources(
                    cpu=self._parse_cpu(hard.get('requests.cpu', '0')),
                    memory=self._parse_memory(hard.get('requests.memory', '0')),
                    gpu=int(hard.get('requests.nvidia.com/gpu', 0))
                ),
                used=Resources(
                    cpu=self._parse_cpu(used.get('requests.cpu', '0')),
                    memory=self._parse_memory(used.get('requests.memory', '0')),
                    gpu=int(used.get('requests.nvidia.com/gpu', 0))
                )
            )

        except Exception as e:
            logger.warning(f"Failed to get K8s quota for project {project_id}: {e}")
            return None

    def check_quota(self, project_id: UUID, resources: Resources, job_type: JobTypeEnum) -> bool:
        """Check if quota is available in K8s."""
        quota_info = self.get_quota(project_id)

        if not quota_info:
            # No quota defined, allow job
            return True

        return quota_info.has_capacity(resources)

    def allocate_quota(
        self,
        project_id: UUID,
        resources: Resources,
        job_type: JobTypeEnum
    ) -> bool:
        """
        Allocate quota in K8s.

        Note: K8s automatically tracks quota usage when pods are created.
        This method just checks availability.
        """
        return self.check_quota(project_id, resources, job_type)

    def release_quota(
        self,
        project_id: UUID,
        resources: Resources,
        job_type: JobTypeEnum
    ) -> None:
        """
        Release quota.

        Note: K8s automatically releases quota when pods are deleted.
        """
        pass

    def create_resource_quota(
        self,
        project_id: UUID,
        cpu_limit: float,
        memory_limit: float,
        gpu_limit: int
    ) -> None:
        """
        Create a K8s ResourceQuota object for a project.

        Args:
            project_id: Project ID
            cpu_limit: CPU limit in cores
            memory_limit: Memory limit in GB
            gpu_limit: GPU limit in cards
        """
        from kubernetes import client

        quota_name = f"project-{project_id}"

        quota = client.V1ResourceQuota(
            metadata=client.V1ObjectMeta(
                name=quota_name,
                labels={"project-id": str(project_id)}
            ),
            spec=client.V1ResourceQuotaSpec(
                hard={
                    "requests.cpu": f"{cpu_limit}",
                    "requests.memory": f"{memory_limit}Gi",
                    "requests.nvidia.com/gpu": str(gpu_limit),
                    "limits.cpu": f"{cpu_limit * 2}",  # Allow 2x for bursting
                    "limits.memory": f"{memory_limit * 2}Gi",
                }
            )
        )

        try:
            self.core_v1.create_namespaced_resource_quota(
                namespace=self.namespace,
                body=quota
            )
            logger.info(f"Created K8s ResourceQuota for project {project_id}")
        except Exception as e:
            logger.error(f"Failed to create K8s ResourceQuota: {e}")

    def sync_quota_state(self) -> None:
        """Sync quota state from K8s to local DB."""
        # TODO: Implement bidirectional sync
        pass

    @staticmethod
    def _parse_cpu(cpu_str: str) -> float:
        """Parse K8s CPU format (e.g., '2', '2000m')."""
        if not cpu_str:
            return 0.0

        cpu_str = str(cpu_str)
        if cpu_str.endswith('m'):
            return float(cpu_str[:-1]) / 1000
        return float(cpu_str)

    @staticmethod
    def _parse_memory(mem_str: str) -> float:
        """Parse K8s memory format (e.g., '2Gi', '2048Mi') to GB."""
        if not mem_str:
            return 0.0

        mem_str = str(mem_str)
        if mem_str.endswith('Gi'):
            return float(mem_str[:-2])
        elif mem_str.endswith('Mi'):
            return float(mem_str[:-2]) / 1024
        elif mem_str.endswith('Ki'):
            return float(mem_str[:-2]) / (1024 * 1024)
        else:
            # Assume bytes
            return float(mem_str) / (1024 ** 3)


class SlurmQuotaProvider(QuotaProvider):
    """
    Slurm QOS/Association-based quota provider.

    Integrates with Slurm's Quality of Service (QOS) and Account Associations.
    """

    def __init__(self, rest_api_url: str, auth_token: str, account_prefix: str = "project-"):
        """
        Initialize Slurm quota provider.

        Args:
            rest_api_url: Slurm REST API URL
            auth_token: Authentication token
            account_prefix: Prefix for Slurm account names
        """
        self.rest_api_url = rest_api_url
        self.auth_token = auth_token
        self.account_prefix = account_prefix

        import requests
        self.session = requests.Session()
        self.session.headers.update({
            "X-SLURM-USER-TOKEN": auth_token,
            "Content-Type": "application/json",
        })

    def get_quota(self, project_id: UUID) -> Optional[QuotaInfo]:
        """Get quota from Slurm association."""
        account = f"{self.account_prefix}{project_id}"

        try:
            # Get association info
            response = self.session.get(
                f"{self.rest_api_url}/slurm/v0.0.40/accounts/{account}"
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("accounts"):
                return None

            account_info = data["accounts"][0]

            # Extract limits (this depends on Slurm configuration)
            # Slurm uses GrpTRES for group resource limits
            grp_tres = account_info.get("grp_tres", "")

            limits = self._parse_tres(grp_tres)
            # TODO: Get current usage from sacct

            return QuotaInfo(
                limits=limits,
                used=Resources()  # Would need to query job history
            )

        except Exception as e:
            logger.warning(f"Failed to get Slurm quota for project {project_id}: {e}")
            return None

    def check_quota(self, project_id: UUID, resources: Resources, job_type: JobTypeEnum) -> bool:
        """
        Check quota availability.

        For Slurm, this is primarily handled by the scheduler itself.
        We just verify the account exists.
        """
        quota_info = self.get_quota(project_id)
        return quota_info is not None

    def allocate_quota(
        self,
        project_id: UUID,
        resources: Resources,
        job_type: JobTypeEnum
    ) -> bool:
        """
        Allocate quota.

        Slurm handles quota enforcement automatically when jobs are submitted.
        """
        return True

    def release_quota(
        self,
        project_id: UUID,
        resources: Resources,
        job_type: JobTypeEnum
    ) -> None:
        """
        Release quota.

        Slurm automatically tracks this.
        """
        pass

    @staticmethod
    def _parse_tres(tres_str: str) -> Resources:
        """
        Parse Slurm TRES (Trackable RESources) string.

        Example: "cpu=1000,mem=500G,gres/gpu=10"
        """
        resources = Resources()

        if not tres_str:
            return resources

        for item in tres_str.split(','):
            if '=' in item:
                key, value = item.split('=', 1)
                key = key.strip()
                value = value.strip()

                if key == 'cpu':
                    resources.cpu = float(value)
                elif key == 'mem':
                    # Parse memory (could be in G, M, K)
                    if value.endswith('G'):
                        resources.memory = float(value[:-1])
                    elif value.endswith('M'):
                        resources.memory = float(value[:-1]) / 1024
                    else:
                        resources.memory = float(value) / (1024 ** 3)
                elif key == 'gres/gpu':
                    resources.gpu = int(value)

        return resources
