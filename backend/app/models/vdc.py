"""
VDC (Virtual Data Center) model for managing resource pools.
"""

from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.db.database import Base


class VDC(Base):
    """
    Virtual Data Center - 虚拟数据中心.

    VDC是一个资源池抽象，包含多个物理集群，为多个项目提供资源。
    """
    __tablename__ = "vdcs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # 总资源配额（可选，None表示使用集群资源总和）
    total_cpu_quota = Column(Float, nullable=True)  # 总CPU核心数
    total_memory_quota = Column(Float, nullable=True)  # 总内存 (GB)
    total_gpu_quota = Column(Integer, nullable=True)  # 总GPU卡数

    # 当前使用量
    used_cpu = Column(Float, nullable=False, default=0.0)
    used_memory = Column(Float, nullable=False, default=0.0)
    used_gpu = Column(Integer, nullable=False, default=0)
    current_jobs = Column(Integer, nullable=False, default=0)

    # 配置
    enabled = Column(Boolean, nullable=False, default=True)
    allow_overcommit = Column(Boolean, nullable=False, default=False)  # 是否允许项目配额超卖
    overcommit_ratio = Column(Float, nullable=False, default=1.0)  # 超卖比例

    # 调度策略
    default_scheduling_policy = Column(String(50), nullable=False, default="fifo")
    cluster_selection_strategy = Column(String(50), nullable=False, default="load_balancing")
    # Strategies: load_balancing, resource_fit, priority, affinity, cost_optimized

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    clusters = relationship("Cluster", back_populates="vdc", cascade="all, delete-orphan")
    project_quotas = relationship("ProjectVDCQuota", back_populates="vdc", cascade="all, delete-orphan")

    def get_total_cluster_resources(self) -> dict:
        """获取所有集群的资源总和"""
        total_cpu = sum(c.total_cpu for c in self.clusters if c.enabled)
        total_memory = sum(c.total_memory for c in self.clusters if c.enabled)
        total_gpu = sum(c.total_gpu for c in self.clusters if c.enabled)

        return {
            "cpu": total_cpu,
            "memory": total_memory,
            "gpu": total_gpu
        }

    def get_effective_quota(self) -> dict:
        """获取有效配额（手动设置的或集群总和）"""
        if self.total_cpu_quota is not None:
            return {
                "cpu": self.total_cpu_quota,
                "memory": self.total_memory_quota,
                "gpu": self.total_gpu_quota
            }
        return self.get_total_cluster_resources()

    def get_available_resources(self) -> dict:
        """获取可用资源"""
        quota = self.get_effective_quota()
        return {
            "cpu": quota["cpu"] - self.used_cpu,
            "memory": quota["memory"] - self.used_memory,
            "gpu": quota["gpu"] - self.used_gpu
        }

    def get_usage_percentage(self) -> dict:
        """获取资源使用率"""
        quota = self.get_effective_quota()
        return {
            "cpu": (self.used_cpu / quota["cpu"] * 100) if quota["cpu"] > 0 else 0,
            "memory": (self.used_memory / quota["memory"] * 100) if quota["memory"] > 0 else 0,
            "gpu": (self.used_gpu / quota["gpu"] * 100) if quota["gpu"] > 0 else 0
        }

    def __repr__(self):
        return f"<VDC(id={self.id}, name={self.name}, clusters={len(self.clusters)})>"
