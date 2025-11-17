"""
VDC Scheduler for multi-cluster job scheduling.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.job import Job, JobStatusEnum
from app.models.cluster import Cluster
from app.vdc.cluster_selector import ClusterSelector
from app.vdc.quota_manager import VDCQuotaManager
from app.executors import ExecutorFactory

logger = logging.getLogger(__name__)


class VDCScheduler:
    """
    VDC调度器.

    负责在VDC的多个集群间调度作业：
    1. 检查VDC和项目配额
    2. 选择最佳集群
    3. 分配配额
    4. 提交作业到集群executor
    """

    def __init__(
        self,
        db: Session,
        cluster_selector: Optional[ClusterSelector] = None,
        quota_manager: Optional[VDCQuotaManager] = None
    ):
        self.db = db
        self.cluster_selector = cluster_selector or ClusterSelector(db)
        self.quota_manager = quota_manager or VDCQuotaManager(db)

    def schedule_job(self, job: Job) -> bool:
        """
        调度作业到VDC中的某个集群.

        Args:
            job: 待调度的作业

        Returns:
            True if job was successfully scheduled
        """
        try:
            # 1. 检查VDC配额
            if not self.quota_manager.check_vdc_quota(job):
                logger.warning(f"Insufficient VDC quota for job {job.id}")
                return False

            # 2. 检查项目配额
            if not self.quota_manager.check_project_quota(job):
                logger.warning(f"Insufficient project quota for job {job.id}")
                return False

            # 3. 选择目标集群
            vdc = job.vdc
            strategy = vdc.cluster_selection_strategy if vdc else "load_balancing"

            cluster = self.cluster_selector.select_cluster(job, strategy=strategy)
            if not cluster:
                logger.warning(f"No suitable cluster found for job {job.id}")
                return False

            # 4. 分配集群
            job.cluster_id = cluster.id
            logger.info(f"Assigned job {job.id} to cluster {cluster.name}")

            # 5. 分配配额
            if not self.quota_manager.allocate_quota(job):
                logger.error(f"Failed to allocate quota for job {job.id}")
                return False

            # 6. 更新集群资源使用
            cluster.used_cpu += job.cpu_request
            cluster.used_memory += job.memory_request
            cluster.used_gpu += job.gpu_request
            cluster.current_jobs += 1

            # 7. 提交作业到集群executor
            executor = self._get_cluster_executor(cluster)
            external_id = executor.submit_job(job)

            # 8. 更新作业状态
            job.external_id = external_id
            job.status = JobStatusEnum.RUNNING
            job.started_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(job)

            logger.info(
                f"Job {job.id} successfully scheduled to cluster {cluster.name} "
                f"with external ID {external_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to schedule job {job.id}: {e}")
            self.db.rollback()
            # 释放已分配的配额
            if job.cluster_id:
                self.quota_manager.release_quota(job)
            return False

    def on_job_completed(self, job: Job) -> None:
        """
        处理作业完成事件，释放配额和集群资源.

        Args:
            job: 已完成的作业
        """
        try:
            # 1. 释放VDC和项目配额
            self.quota_manager.release_quota(job)

            # 2. 释放集群资源
            if job.cluster:
                cluster = job.cluster
                cluster.used_cpu = max(0, cluster.used_cpu - job.cpu_request)
                cluster.used_memory = max(0, cluster.used_memory - job.memory_request)
                cluster.used_gpu = max(0, cluster.used_gpu - job.gpu_request)
                cluster.current_jobs = max(0, cluster.current_jobs - 1)

            self.db.commit()

            logger.info(f"Released resources for completed job {job.id}")

        except Exception as e:
            logger.error(f"Error releasing resources for job {job.id}: {e}")
            self.db.rollback()

    def sync_job_status(self, job: Job) -> bool:
        """
        从executor同步作业状态.

        Args:
            job: 要同步的作业

        Returns:
            True if status was updated
        """
        if not job.cluster or not job.external_id:
            return False

        try:
            executor = self._get_cluster_executor(job.cluster)
            current_status = executor.get_job_status(job.external_id)

            if current_status != job.status:
                old_status = job.status
                job.status = current_status

                # 处理作业完成
                if current_status in [
                    JobStatusEnum.SUCCEEDED,
                    JobStatusEnum.FAILED,
                    JobStatusEnum.CANCELLED,
                    JobStatusEnum.TIMEOUT
                ]:
                    if not job.finished_at:
                        job.finished_at = datetime.utcnow()

                    # 释放配额和资源
                    self.on_job_completed(job)

                    # 同步Run状态（如果有关联）
                    self._sync_run_status(job, current_status)

                self.db.commit()
                logger.info(f"Job {job.id} status updated: {old_status} -> {current_status}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to sync job {job.id} status: {e}")
            return False

    def _sync_run_status(self, job: Job, job_status: JobStatusEnum) -> None:
        """同步Run状态（复用现有逻辑）"""
        if not job.run_id:
            return

        try:
            from app.models.run import Run, RunStateEnum

            run = self.db.query(Run).filter(Run.id == job.run_id).first()
            if not run:
                logger.warning(f"Run {job.run_id} not found for job {job.id}")
                return

            # Map Job status to Run state
            status_mapping = {
                JobStatusEnum.PENDING: None,
                JobStatusEnum.QUEUED: None,
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

                if new_run_state in [RunStateEnum.FINISHED, RunStateEnum.CRASHED, RunStateEnum.KILLED]:
                    if not run.finished_at:
                        run.finished_at = datetime.utcnow()

                logger.info(f"Run {run.id} state synced: {old_state} -> {new_run_state}")

        except Exception as e:
            logger.error(f"Failed to sync run status for job {job.id}: {e}")

    def _get_cluster_executor(self, cluster: Cluster):
        """
        获取集群的executor实例.

        根据集群配置创建相应的executor（Kubernetes或Slurm）。
        """
        from app.models.cluster import ClusterTypeEnum

        if cluster.cluster_type == ClusterTypeEnum.KUBERNETES:
            from app.executors.kubernetes_executor import KubernetesExecutor
            return KubernetesExecutor(
                kubeconfig_path=cluster.config.get("kubeconfig_path"),
                namespace=cluster.namespace or cluster.config.get("namespace", "default"),
                service_account=cluster.config.get("service_account", "default")
            )
        elif cluster.cluster_type == ClusterTypeEnum.SLURM:
            from app.executors.slurm_executor import SlurmExecutor
            return SlurmExecutor(
                rest_api_url=cluster.config.get("rest_api_url") or cluster.endpoint,
                auth_token=cluster.config.get("auth_token"),
                partition=cluster.namespace or cluster.config.get("partition", "compute"),
                account=cluster.config.get("account")
            )
        else:
            raise ValueError(f"Unsupported cluster type: {cluster.cluster_type}")

    def sync_all_vdc_jobs(self, vdc_id=None) -> int:
        """
        同步所有VDC作业的状态.

        Args:
            vdc_id: 可选，只同步特定VDC的作业

        Returns:
            更新的作业数
        """
        from app.models.job import Job

        query = self.db.query(Job).filter(
            Job.status.in_([JobStatusEnum.RUNNING, JobStatusEnum.QUEUED])
        )

        if vdc_id:
            query = query.filter(Job.vdc_id == vdc_id)

        active_jobs = query.all()
        updated_count = 0

        for job in active_jobs:
            if self.sync_job_status(job):
                updated_count += 1

        logger.info(f"Synced {updated_count} VDC jobs")
        return updated_count
