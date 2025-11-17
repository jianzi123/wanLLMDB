"""
Cluster model for managing physical compute clusters (K8s, Slurm).
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Boolean, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.db.database import Base


class ClusterTypeEnum(str, enum.Enum):
    """集群类型"""
    KUBERNETES = "kubernetes"
    SLURM = "slurm"


class ClusterStatusEnum(str, enum.Enum):
    """集群状态"""
    HEALTHY = "healthy"          # 健康
    DEGRADED = "degraded"        # 降级（部分功能受损）
    UNAVAILABLE = "unavailable"  # 不可用
    MAINTENANCE = "maintenance"  # 维护中


class Cluster(Base):
    """
    物理计算集群（Kubernetes或Slurm）.

    每个集群属于一个VDC，提供实际的计算资源。
    """
    __tablename__ = "clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vdc_id = Column(UUID(as_uuid=True), ForeignKey("vdcs.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    cluster_type = Column(Enum(ClusterTypeEnum), nullable=False, index=True)

    # 连接配置
    endpoint = Column(String(500), nullable=True)  # API endpoint
    config = Column(JSON, nullable=False, default=dict)  # 连接配置（加密存储）
    """
    config structure for Kubernetes:
    {
        "kubeconfig_path": "/path/to/kubeconfig",  # or
        "kubeconfig": "base64_encoded_kubeconfig",
        "namespace": "wanllmdb-jobs",
        "service_account": "job-runner"
    }

    config structure for Slurm:
    {
        "rest_api_url": "http://slurm-controller:6820",
        "auth_token": "encrypted_token",
        "partition": "gpu",
        "account": "ml_team"
    }
    """
    namespace = Column(String(255), nullable=True)  # K8s namespace 或 Slurm partition

    # 资源容量
    total_cpu = Column(Float, nullable=False, default=0.0)
    total_memory = Column(Float, nullable=False, default=0.0)  # GB
    total_gpu = Column(Integer, nullable=False, default=0)

    # 当前资源使用（实时更新）
    used_cpu = Column(Float, nullable=False, default=0.0)
    used_memory = Column(Float, nullable=False, default=0.0)
    used_gpu = Column(Integer, nullable=False, default=0)
    current_jobs = Column(Integer, nullable=False, default=0)

    # 状态
    status = Column(Enum(ClusterStatusEnum), nullable=False, default=ClusterStatusEnum.HEALTHY, index=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)  # 最后健康检查时间
    status_message = Column(Text, nullable=True)  # 状态描述信息

    # 调度配置
    enabled = Column(Boolean, nullable=False, default=True)  # 是否接受新作业
    priority = Column(Integer, nullable=False, default=0)  # 集群优先级（越高越优先）
    weight = Column(Float, nullable=False, default=1.0)  # 调度权重
    labels = Column(JSON, nullable=False, default=dict)  # 集群标签（用于亲和性调度）
    """
    labels examples:
    {
        "region": "us-west-1",
        "gpu_type": "a100",
        "node_type": "spot",
        "cost_tier": "low"
    }
    """

    # 限制
    max_jobs_per_user = Column(Integer, nullable=True)  # 每用户最大作业数
    max_total_jobs = Column(Integer, nullable=True)  # 集群最大总作业数

    # 成本（可选，用于成本优化调度）
    cost_per_cpu_hour = Column(Float, nullable=True)
    cost_per_memory_gb_hour = Column(Float, nullable=True)
    cost_per_gpu_hour = Column(Float, nullable=True)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    vdc = relationship("VDC", back_populates="clusters")
    jobs = relationship("Job", back_populates="cluster", foreign_keys="[Job.cluster_id]")

    def get_available_resources(self) -> dict:
        """获取可用资源"""
        return {
            "cpu": self.total_cpu - self.used_cpu,
            "memory": self.total_memory - self.used_memory,
            "gpu": self.total_gpu - self.used_gpu
        }

    def get_usage_percentage(self) -> dict:
        """获取资源使用率"""
        return {
            "cpu": (self.used_cpu / self.total_cpu * 100) if self.total_cpu > 0 else 0,
            "memory": (self.used_memory / self.total_memory * 100) if self.total_memory > 0 else 0,
            "gpu": (self.used_gpu / self.total_gpu * 100) if self.total_gpu > 0 else 0
        }

    def has_available_resources(self, cpu: float, memory: float, gpu: int) -> bool:
        """检查是否有足够的可用资源"""
        available = self.get_available_resources()
        return (
            available["cpu"] >= cpu and
            available["memory"] >= memory and
            available["gpu"] >= gpu
        )

    def can_accept_job(self) -> bool:
        """检查集群是否可以接受新作业"""
        if not self.enabled:
            return False
        if self.status != ClusterStatusEnum.HEALTHY:
            return False
        if self.max_total_jobs and self.current_jobs >= self.max_total_jobs:
            return False
        return True

    def labels_match(self, required_labels: dict) -> bool:
        """检查集群标签是否匹配要求"""
        if not required_labels:
            return True
        for key, value in required_labels.items():
            if key not in self.labels or self.labels[key] != value:
                return False
        return True

    def __repr__(self):
        return f"<Cluster(id={self.id}, name={self.name}, type={self.cluster_type}, status={self.status})>"
