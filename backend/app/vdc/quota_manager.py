"""
VDC Quota Manager for managing resource quotas at VDC and project levels.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.job import Job, JobTypeEnum
from app.models.vdc import VDC
from app.models.project_vdc_quota import ProjectVDCQuota
from app.repositories.vdc_repository import ProjectVDCQuotaRepository

logger = logging.getLogger(__name__)


class VDCQuotaManager:
    """
    VDC配额管理器.

    管理VDC级别和项目级别的资源配额。
    """

    def __init__(self, db: Session):
        self.db = db
        self.quota_repo = ProjectVDCQuotaRepository(db)

    def check_vdc_quota(self, job: Job) -> bool:
        """
        检查VDC是否有足够的配额.

        Args:
            job: 待检查的作业

        Returns:
            True if quota is available
        """
        vdc = job.vdc
        if not vdc:
            logger.error(f"Job {job.id} has no VDC assigned")
            return False

        if not vdc.enabled:
            logger.warning(f"VDC {vdc.name} is disabled")
            return False

        # 获取VDC的有效配额
        effective_quota = vdc.get_effective_quota()
        available = vdc.get_available_resources()

        # 检查资源是否足够
        has_quota = (
            available["cpu"] >= job.cpu_request and
            available["memory"] >= job.memory_request and
            available["gpu"] >= job.gpu_request
        )

        if not has_quota:
            logger.warning(
                f"VDC {vdc.name} has insufficient quota for job {job.id}. "
                f"Required: CPU={job.cpu_request}, Memory={job.memory_request}, GPU={job.gpu_request}. "
                f"Available: CPU={available['cpu']}, Memory={available['memory']}, GPU={available['gpu']}"
            )

        return has_quota

    def check_project_quota(self, job: Job) -> bool:
        """
        检查项目在VDC中是否有足够的配额.

        Args:
            job: 待检查的作业

        Returns:
            True if quota is available
        """
        if not job.vdc_id or not job.project_id:
            logger.error(f"Job {job.id} missing VDC or project")
            return False

        # 获取项目在VDC中的配额
        quota = self.quota_repo.get_by_project_and_vdc(
            job.project_id,
            job.vdc_id
        )

        if not quota:
            logger.error(
                f"No quota found for project {job.project_id} in VDC {job.vdc_id}"
            )
            return False

        # 检查资源配额
        has_resource_quota = quota.has_available_quota(
            job.cpu_request,
            job.memory_request,
            job.gpu_request
        )

        if not has_resource_quota:
            available = quota.get_available_resources()
            logger.warning(
                f"Project {job.project_id} has insufficient quota in VDC. "
                f"Required: CPU={job.cpu_request}, Memory={job.memory_request}, GPU={job.gpu_request}. "
                f"Available: CPU={available['cpu']}, Memory={available['memory']}, GPU={available['gpu']}"
            )
            return False

        # 检查作业类型限制
        if not quota.can_run_job_type(job.job_type.value):
            logger.warning(
                f"Project {job.project_id} has reached max {job.job_type.value} jobs limit"
            )
            return False

        return True

    def allocate_quota(self, job: Job) -> bool:
        """
        分配配额给作业.

        更新VDC和项目的资源使用量。

        Args:
            job: 要分配配额的作业

        Returns:
            True if allocation succeeded
        """
        try:
            # 分配VDC配额
            vdc = job.vdc
            vdc.used_cpu += job.cpu_request
            vdc.used_memory += job.memory_request
            vdc.used_gpu += job.gpu_request
            vdc.current_jobs += 1

            # 分配项目配额
            quota = self.quota_repo.get_by_project_and_vdc(
                job.project_id,
                job.vdc_id
            )

            if not quota:
                logger.error(f"No quota found for project {job.project_id}")
                return False

            quota.used_cpu += job.cpu_request
            quota.used_memory += job.memory_request
            quota.used_gpu += job.gpu_request
            quota.current_jobs += 1

            # 更新作业类型计数
            if job.job_type == JobTypeEnum.TRAINING:
                quota.current_training_jobs += 1
            elif job.job_type == JobTypeEnum.INFERENCE:
                quota.current_inference_jobs += 1
            elif job.job_type == JobTypeEnum.WORKFLOW:
                quota.current_workflow_jobs += 1

            self.db.commit()

            logger.info(
                f"Allocated quota for job {job.id}: "
                f"CPU={job.cpu_request}, Memory={job.memory_request}, GPU={job.gpu_request}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to allocate quota for job {job.id}: {e}")
            self.db.rollback()
            return False

    def release_quota(self, job: Job) -> bool:
        """
        释放作业的配额.

        Args:
            job: 要释放配额的作业

        Returns:
            True if release succeeded
        """
        try:
            # 释放VDC配额
            vdc = job.vdc
            if vdc:
                vdc.used_cpu = max(0, vdc.used_cpu - job.cpu_request)
                vdc.used_memory = max(0, vdc.used_memory - job.memory_request)
                vdc.used_gpu = max(0, vdc.used_gpu - job.gpu_request)
                vdc.current_jobs = max(0, vdc.current_jobs - 1)

            # 释放项目配额
            quota = self.quota_repo.get_by_project_and_vdc(
                job.project_id,
                job.vdc_id
            )

            if quota:
                quota.used_cpu = max(0, quota.used_cpu - job.cpu_request)
                quota.used_memory = max(0, quota.used_memory - job.memory_request)
                quota.used_gpu = max(0, quota.used_gpu - job.gpu_request)
                quota.current_jobs = max(0, quota.current_jobs - 1)

                # 更新作业类型计数
                if job.job_type == JobTypeEnum.TRAINING:
                    quota.current_training_jobs = max(0, quota.current_training_jobs - 1)
                elif job.job_type == JobTypeEnum.INFERENCE:
                    quota.current_inference_jobs = max(0, quota.current_inference_jobs - 1)
                elif job.job_type == JobTypeEnum.WORKFLOW:
                    quota.current_workflow_jobs = max(0, quota.current_workflow_jobs - 1)

            self.db.commit()

            logger.info(
                f"Released quota for job {job.id}: "
                f"CPU={job.cpu_request}, Memory={job.memory_request}, GPU={job.gpu_request}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to release quota for job {job.id}: {e}")
            self.db.rollback()
            return False

    def get_project_quota_usage(
        self,
        project_id: UUID,
        vdc_id: UUID
    ) -> Optional[dict]:
        """
        获取项目的配额使用情况.

        Returns:
            配额使用信息字典
        """
        quota = self.quota_repo.get_by_project_and_vdc(project_id, vdc_id)
        if not quota:
            return None

        return {
            "quota": {
                "cpu": quota.cpu_quota,
                "memory": quota.memory_quota,
                "gpu": quota.gpu_quota,
                "max_jobs": quota.max_concurrent_jobs
            },
            "used": {
                "cpu": quota.used_cpu,
                "memory": quota.used_memory,
                "gpu": quota.used_gpu,
                "jobs": quota.current_jobs
            },
            "available": quota.get_available_resources(),
            "usage_percentage": quota.get_usage_percentage()
        }
