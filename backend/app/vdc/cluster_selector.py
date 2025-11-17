"""
Cluster selector for VDC multi-cluster scheduling.
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.job import Job
from app.models.cluster import Cluster, ClusterStatusEnum

logger = logging.getLogger(__name__)


class ClusterSelector:
    """
    集群选择器.

    根据不同的策略从VDC中的多个集群中选择最适合的集群来运行作业。
    """

    def __init__(self, db: Session):
        self.db = db

    def select_cluster(
        self,
        job: Job,
        strategy: str = "load_balancing"
    ) -> Optional[Cluster]:
        """
        根据策略选择最佳集群.

        Args:
            job: 待调度的作业
            strategy: 选择策略

        Returns:
            最佳集群，如果没有合适的集群则返回None
        """
        # 获取候选集群列表
        candidates = self._get_candidate_clusters(job)

        if not candidates:
            logger.warning(f"No candidate clusters found for job {job.id}")
            return None

        logger.debug(f"Found {len(candidates)} candidate clusters for job {job.id}")

        # 应用选择策略
        if strategy == "load_balancing":
            return self._select_by_load_balancing(candidates, job)
        elif strategy == "resource_fit":
            return self._select_by_resource_fit(candidates, job)
        elif strategy == "priority":
            return self._select_by_priority(candidates, job)
        elif strategy == "affinity":
            return self._select_by_affinity(candidates, job)
        elif strategy == "cost_optimized":
            return self._select_by_cost(candidates, job)
        else:
            logger.warning(f"Unknown strategy {strategy}, using load_balancing")
            return self._select_by_load_balancing(candidates, job)

    def _get_candidate_clusters(self, job: Job) -> List[Cluster]:
        """
        获取候选集群列表.

        过滤条件：
        1. 集群必须启用且健康
        2. 集群类型必须匹配作业的executor
        3. 集群必须有足够的资源
        4. 集群标签必须匹配（如果有要求）
        """
        if not job.vdc:
            return []

        candidates = []

        for cluster in job.vdc.clusters:
            # 1. 检查集群是否可用
            if not cluster.can_accept_job():
                logger.debug(f"Cluster {cluster.name} cannot accept jobs")
                continue

            # 2. 检查集群类型匹配
            if not self._cluster_type_matches(cluster, job):
                logger.debug(f"Cluster {cluster.name} type mismatch")
                continue

            # 3. 检查资源可用性
            if not cluster.has_available_resources(
                job.cpu_request,
                job.memory_request,
                job.gpu_request
            ):
                logger.debug(f"Cluster {cluster.name} insufficient resources")
                continue

            # 4. 检查标签亲和性
            if job.required_labels and not cluster.labels_match(job.required_labels):
                logger.debug(f"Cluster {cluster.name} labels mismatch")
                continue

            candidates.append(cluster)

        return candidates

    def _cluster_type_matches(self, cluster: Cluster, job: Job) -> bool:
        """检查集群类型是否匹配作业的executor"""
        return cluster.cluster_type.value == job.executor.value

    def _select_by_load_balancing(
        self,
        candidates: List[Cluster],
        job: Job
    ) -> Optional[Cluster]:
        """
        负载均衡策略：选择当前负载最低的集群.

        负载计算基于资源使用率（CPU、Memory、GPU）的加权平均。
        """
        if not candidates:
            return None

        # 计算每个集群的负载分数（越低越好）
        def calculate_load(cluster: Cluster) -> float:
            usage = cluster.get_usage_percentage()
            # 加权平均：CPU(0.3) + Memory(0.3) + GPU(0.4)
            weights = {"cpu": 0.3, "memory": 0.3, "gpu": 0.4}
            load = (
                usage["cpu"] * weights["cpu"] +
                usage["memory"] * weights["memory"] +
                usage["gpu"] * weights["gpu"]
            )
            return load

        # 选择负载最低的集群
        selected = min(candidates, key=calculate_load)
        logger.info(
            f"Selected cluster {selected.name} with load "
            f"{calculate_load(selected):.2f}% for job {job.id}"
        )
        return selected

    def _select_by_resource_fit(
        self,
        candidates: List[Cluster],
        job: Job
    ) -> Optional[Cluster]:
        """
        资源匹配策略：选择能够刚好满足资源需求的集群.

        目标是避免资源浪费，选择剩余资源最接近需求的集群。
        """
        if not candidates:
            return None

        def calculate_fit_score(cluster: Cluster) -> float:
            """
            计算资源匹配分数.
            分数越低表示匹配越好（资源刚好够用，浪费最少）。
            """
            available = cluster.get_available_resources()

            # 计算每种资源的过剩比例
            cpu_excess = (available["cpu"] - job.cpu_request) / max(job.cpu_request, 0.1)
            mem_excess = (available["memory"] - job.memory_request) / max(job.memory_request, 0.1)
            gpu_excess = (available["gpu"] - job.gpu_request) / max(job.gpu_request, 1) if job.gpu_request > 0 else 0

            # 总过剩分数（越低越好）
            score = abs(cpu_excess) + abs(mem_excess) + abs(gpu_excess)
            return score

        selected = min(candidates, key=calculate_fit_score)
        logger.info(f"Selected cluster {selected.name} with best resource fit for job {job.id}")
        return selected

    def _select_by_priority(
        self,
        candidates: List[Cluster],
        job: Job
    ) -> Optional[Cluster]:
        """
        优先级策略：选择优先级和权重最高的集群.

        考虑集群的priority字段和weight字段。
        """
        if not candidates:
            return None

        def calculate_priority_score(cluster: Cluster) -> float:
            """计算优先级分数（越高越好）"""
            return cluster.priority * cluster.weight

        selected = max(candidates, key=calculate_priority_score)
        logger.info(
            f"Selected cluster {selected.name} with priority "
            f"{selected.priority} for job {job.id}"
        )
        return selected

    def _select_by_affinity(
        self,
        candidates: List[Cluster],
        job: Job
    ) -> Optional[Cluster]:
        """
        亲和性策略：优先选择作业指定的preferred_clusters.

        如果preferred_clusters中有可用集群，选择其中优先级最高的。
        否则fallback到负载均衡策略。
        """
        if not candidates:
            return None

        # 检查是否有preferred clusters
        if job.preferred_cluster_ids:
            preferred_candidates = [
                c for c in candidates
                if str(c.id) in job.preferred_cluster_ids
            ]

            if preferred_candidates:
                # 在preferred集群中选择优先级最高的
                selected = max(preferred_candidates, key=lambda c: c.priority)
                logger.info(
                    f"Selected preferred cluster {selected.name} for job {job.id}"
                )
                return selected

        # Fallback到负载均衡
        logger.info(f"No preferred clusters available, using load balancing for job {job.id}")
        return self._select_by_load_balancing(candidates, job)

    def _select_by_cost(
        self,
        candidates: List[Cluster],
        job: Job
    ) -> Optional[Cluster]:
        """
        成本优化策略：选择运行成本最低的集群.

        基于集群的cost_per_cpu_hour、cost_per_memory_gb_hour、cost_per_gpu_hour计算。
        """
        if not candidates:
            return None

        def calculate_cost(cluster: Cluster) -> float:
            """计算作业在该集群上的预估成本"""
            cost = 0.0

            if cluster.cost_per_cpu_hour:
                cost += job.cpu_request * cluster.cost_per_cpu_hour
            if cluster.cost_per_memory_gb_hour:
                cost += job.memory_request * cluster.cost_per_memory_gb_hour
            if cluster.cost_per_gpu_hour and job.gpu_request > 0:
                cost += job.gpu_request * cluster.cost_per_gpu_hour

            return cost

        # 过滤掉没有成本信息的集群
        clusters_with_cost = [
            c for c in candidates
            if c.cost_per_cpu_hour is not None
        ]

        if not clusters_with_cost:
            # 如果没有集群有成本信息，fallback到负载均衡
            logger.warning("No clusters with cost information, using load balancing")
            return self._select_by_load_balancing(candidates, job)

        selected = min(clusters_with_cost, key=calculate_cost)
        logger.info(
            f"Selected cluster {selected.name} with lowest cost "
            f"${calculate_cost(selected):.2f}/hour for job {job.id}"
        )
        return selected
