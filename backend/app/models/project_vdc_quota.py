"""
ProjectVDCQuota model for managing project quotas within a VDC.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.database import Base


class ProjectVDCQuota(Base):
    """
    项目在VDC中的配额.

    管理项目在特定VDC中可以使用的资源配额。
    """
    __tablename__ = "project_vdc_quotas"
    __table_args__ = (
        UniqueConstraint('project_id', 'vdc_id', name='uq_project_vdc'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    vdc_id = Column(UUID(as_uuid=True), ForeignKey("vdcs.id", ondelete="CASCADE"), nullable=False, index=True)

    # 配额限制
    cpu_quota = Column(Float, nullable=False, default=100.0)  # CPU核心数
    memory_quota = Column(Float, nullable=False, default=500.0)  # 内存 (GB)
    gpu_quota = Column(Integer, nullable=False, default=10)  # GPU卡数
    max_concurrent_jobs = Column(Integer, nullable=False, default=50)  # 最大并发作业数

    # 当前使用量
    used_cpu = Column(Float, nullable=False, default=0.0)
    used_memory = Column(Float, nullable=False, default=0.0)
    used_gpu = Column(Integer, nullable=False, default=0)
    current_jobs = Column(Integer, nullable=False, default=0)

    # 优先级
    priority = Column(Integer, nullable=False, default=0)  # 项目在VDC中的优先级

    # 作业类型限制（可选）
    max_training_jobs = Column(Integer, nullable=True)  # 最大训练作业数
    max_inference_jobs = Column(Integer, nullable=True)  # 最大推理作业数
    max_workflow_jobs = Column(Integer, nullable=True)  # 最大工作流作业数

    # 当前各类型作业数
    current_training_jobs = Column(Integer, nullable=False, default=0)
    current_inference_jobs = Column(Integer, nullable=False, default=0)
    current_workflow_jobs = Column(Integer, nullable=False, default=0)

    # 配额执行
    enforce_quota = Column(Boolean, nullable=False, default=True)  # 是否强制执行配额

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", backref="vdc_quotas")
    vdc = relationship("VDC", back_populates="project_quotas")

    def has_available_quota(self, cpu: float, memory: float, gpu: int) -> bool:
        """检查是否有足够的配额"""
        if not self.enforce_quota:
            return True

        return (
            self.used_cpu + cpu <= self.cpu_quota and
            self.used_memory + memory <= self.memory_quota and
            self.used_gpu + gpu <= self.gpu_quota and
            self.current_jobs < self.max_concurrent_jobs
        )

    def get_available_resources(self) -> dict:
        """获取可用资源"""
        return {
            "cpu": self.cpu_quota - self.used_cpu,
            "memory": self.memory_quota - self.used_memory,
            "gpu": self.gpu_quota - self.used_gpu,
            "jobs": self.max_concurrent_jobs - self.current_jobs
        }

    def get_usage_percentage(self) -> dict:
        """获取资源使用率"""
        return {
            "cpu": (self.used_cpu / self.cpu_quota * 100) if self.cpu_quota > 0 else 0,
            "memory": (self.used_memory / self.memory_quota * 100) if self.memory_quota > 0 else 0,
            "gpu": (self.used_gpu / self.gpu_quota * 100) if self.gpu_quota > 0 else 0,
            "jobs": (self.current_jobs / self.max_concurrent_jobs * 100) if self.max_concurrent_jobs > 0 else 0
        }

    def can_run_job_type(self, job_type: str) -> bool:
        """检查是否可以运行特定类型的作业"""
        if job_type == "training":
            if self.max_training_jobs is None:
                return True
            return self.current_training_jobs < self.max_training_jobs
        elif job_type == "inference":
            if self.max_inference_jobs is None:
                return True
            return self.current_inference_jobs < self.max_inference_jobs
        elif job_type == "workflow":
            if self.max_workflow_jobs is None:
                return True
            return self.current_workflow_jobs < self.max_workflow_jobs
        return True

    def __repr__(self):
        return f"<ProjectVDCQuota(project_id={self.project_id}, vdc_id={self.vdc_id}, cpu={self.used_cpu}/{self.cpu_quota})>"
