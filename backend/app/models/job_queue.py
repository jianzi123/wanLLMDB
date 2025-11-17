"""
Job Queue model for managing job scheduling queues.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.database import Base


class JobQueue(Base):
    """
    Job queue for a project.

    Each project can have one or more queues for organizing jobs.
    Queues can have priority levels and concurrency limits.
    """
    __tablename__ = "job_queues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)

    # Queue configuration
    priority = Column(Integer, default=0, nullable=False)  # Higher = higher priority
    max_concurrent_jobs = Column(Integer, default=10, nullable=False)  # Max jobs running simultaneously
    enabled = Column(Boolean, default=True, nullable=False)

    # Statistics
    total_jobs = Column(Integer, default=0, nullable=False)
    running_jobs = Column(Integer, default=0, nullable=False)
    pending_jobs = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", backref="job_queues")

    def __repr__(self):
        return f"<JobQueue(id={self.id}, name={self.name}, project_id={self.project_id})>"


class ProjectQuota(Base):
    """
    Resource quota for a project.

    Tracks available and used resources (CPU, memory, GPU) for a project.
    Jobs are only scheduled if quota is available.
    """
    __tablename__ = "project_quotas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Quota limits (total available)
    cpu_quota = Column(Float, nullable=False, default=100.0)  # CPU cores
    memory_quota = Column(Float, nullable=False, default=500.0)  # GB
    gpu_quota = Column(Integer, nullable=False, default=10)  # GPU cards
    max_concurrent_jobs = Column(Integer, nullable=False, default=50)  # Max total jobs

    # Current usage
    used_cpu = Column(Float, nullable=False, default=0.0)
    used_memory = Column(Float, nullable=False, default=0.0)
    used_gpu = Column(Integer, nullable=False, default=0)
    current_jobs = Column(Integer, nullable=False, default=0)

    # Job limits per type
    max_training_jobs = Column(Integer, nullable=True)  # Optional limit on training jobs
    max_inference_jobs = Column(Integer, nullable=True)
    max_workflow_jobs = Column(Integer, nullable=True)

    # Current counts per type
    current_training_jobs = Column(Integer, nullable=False, default=0)
    current_inference_jobs = Column(Integer, nullable=False, default=0)
    current_workflow_jobs = Column(Integer, nullable=False, default=0)

    # Quota enforcement
    enforce_quota = Column(Boolean, default=True, nullable=False)  # Enable/disable quota checks

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", backref="quota", uselist=False)

    def has_available_quota(self, cpu_request: float, memory_request: float, gpu_request: int) -> bool:
        """Check if quota is available for the requested resources."""
        if not self.enforce_quota:
            return True

        return (
            self.used_cpu + cpu_request <= self.cpu_quota and
            self.used_memory + memory_request <= self.memory_quota and
            self.used_gpu + gpu_request <= self.gpu_quota and
            self.current_jobs < self.max_concurrent_jobs
        )

    def get_available_resources(self) -> dict:
        """Get available resources."""
        return {
            "cpu": self.cpu_quota - self.used_cpu,
            "memory": self.memory_quota - self.used_memory,
            "gpu": self.gpu_quota - self.used_gpu,
            "jobs": self.max_concurrent_jobs - self.current_jobs,
        }

    def get_usage_percentage(self) -> dict:
        """Get resource usage percentage."""
        return {
            "cpu": (self.used_cpu / self.cpu_quota * 100) if self.cpu_quota > 0 else 0,
            "memory": (self.used_memory / self.memory_quota * 100) if self.memory_quota > 0 else 0,
            "gpu": (self.used_gpu / self.gpu_quota * 100) if self.gpu_quota > 0 else 0,
            "jobs": (self.current_jobs / self.max_concurrent_jobs * 100) if self.max_concurrent_jobs > 0 else 0,
        }

    def __repr__(self):
        return f"<ProjectQuota(project_id={self.project_id}, cpu={self.used_cpu}/{self.cpu_quota})>"
