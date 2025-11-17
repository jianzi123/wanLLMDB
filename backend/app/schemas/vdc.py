"""
VDC, Cluster, and ProjectVDCQuota schemas for API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
from enum import Enum


# Enums
class ClusterType(str, Enum):
    KUBERNETES = "kubernetes"
    SLURM = "slurm"


class ClusterStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    MAINTENANCE = "maintenance"


# VDC Schemas
class VDCCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    total_cpu_quota: Optional[float] = Field(None, ge=0)
    total_memory_quota: Optional[float] = Field(None, ge=0)
    total_gpu_quota: Optional[int] = Field(None, ge=0)
    enabled: bool = True
    allow_overcommit: bool = False
    overcommit_ratio: float = Field(1.0, ge=1.0, le=5.0)
    default_scheduling_policy: str = Field("fifo", pattern="^(fifo|priority|fairshare)$")
    cluster_selection_strategy: str = Field(
        "load_balancing",
        pattern="^(load_balancing|resource_fit|priority|affinity|cost_optimized)$"
    )


class VDCUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    total_cpu_quota: Optional[float] = Field(None, ge=0)
    total_memory_quota: Optional[float] = Field(None, ge=0)
    total_gpu_quota: Optional[int] = Field(None, ge=0)
    enabled: Optional[bool] = None
    allow_overcommit: Optional[bool] = None
    overcommit_ratio: Optional[float] = Field(None, ge=1.0, le=5.0)
    default_scheduling_policy: Optional[str] = Field(
        None, pattern="^(fifo|priority|fairshare)$"
    )
    cluster_selection_strategy: Optional[str] = Field(
        None, pattern="^(load_balancing|resource_fit|priority|affinity|cost_optimized)$"
    )


class VDCResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    total_cpu_quota: Optional[float]
    total_memory_quota: Optional[float]
    total_gpu_quota: Optional[int]
    used_cpu: float
    used_memory: float
    used_gpu: int
    current_jobs: int
    enabled: bool
    allow_overcommit: bool
    overcommit_ratio: float
    default_scheduling_policy: str
    cluster_selection_strategy: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VDCStats(BaseModel):
    total_clusters: int
    healthy_clusters: int
    total_capacity: Dict[str, float]
    effective_quota: Dict[str, float]
    used_resources: Dict[str, float]
    available_resources: Dict[str, float]
    usage_percentage: Dict[str, float]
    total_projects: int
    current_jobs: int


# Cluster Schemas
class ClusterCreate(BaseModel):
    vdc_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    cluster_type: ClusterType
    endpoint: Optional[str] = Field(None, max_length=500)
    config: Dict = Field(default_factory=dict)
    namespace: Optional[str] = Field(None, max_length=255)
    total_cpu: float = Field(..., ge=0)
    total_memory: float = Field(..., ge=0)
    total_gpu: int = Field(..., ge=0)
    enabled: bool = True
    priority: int = Field(0, ge=0)
    weight: float = Field(1.0, ge=0)
    labels: Dict = Field(default_factory=dict)
    max_jobs_per_user: Optional[int] = Field(None, ge=1)
    max_total_jobs: Optional[int] = Field(None, ge=1)
    cost_per_cpu_hour: Optional[float] = Field(None, ge=0)
    cost_per_memory_gb_hour: Optional[float] = Field(None, ge=0)
    cost_per_gpu_hour: Optional[float] = Field(None, ge=0)


class ClusterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    endpoint: Optional[str] = Field(None, max_length=500)
    config: Optional[Dict] = None
    namespace: Optional[str] = Field(None, max_length=255)
    total_cpu: Optional[float] = Field(None, ge=0)
    total_memory: Optional[float] = Field(None, ge=0)
    total_gpu: Optional[int] = Field(None, ge=0)
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0)
    weight: Optional[float] = Field(None, ge=0)
    labels: Optional[Dict] = None
    max_jobs_per_user: Optional[int] = Field(None, ge=1)
    max_total_jobs: Optional[int] = Field(None, ge=1)
    cost_per_cpu_hour: Optional[float] = Field(None, ge=0)
    cost_per_memory_gb_hour: Optional[float] = Field(None, ge=0)
    cost_per_gpu_hour: Optional[float] = Field(None, ge=0)


class ClusterResponse(BaseModel):
    id: UUID
    vdc_id: UUID
    name: str
    description: Optional[str]
    cluster_type: ClusterType
    endpoint: Optional[str]
    namespace: Optional[str]
    total_cpu: float
    total_memory: float
    total_gpu: int
    used_cpu: float
    used_memory: float
    used_gpu: int
    current_jobs: int
    status: ClusterStatus
    last_heartbeat: Optional[datetime]
    status_message: Optional[str]
    enabled: bool
    priority: int
    weight: float
    labels: Dict
    max_jobs_per_user: Optional[int]
    max_total_jobs: Optional[int]
    cost_per_cpu_hour: Optional[float]
    cost_per_memory_gb_hour: Optional[float]
    cost_per_gpu_hour: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClusterStats(BaseModel):
    available_resources: Dict[str, float]
    usage_percentage: Dict[str, float]
    current_jobs: int
    status: ClusterStatus


# ProjectVDCQuota Schemas
class ProjectVDCQuotaCreate(BaseModel):
    project_id: UUID
    vdc_id: UUID
    cpu_quota: float = Field(..., ge=0)
    memory_quota: float = Field(..., ge=0)
    gpu_quota: int = Field(..., ge=0)
    max_concurrent_jobs: int = Field(..., ge=1)
    priority: int = Field(0, ge=0)
    max_training_jobs: Optional[int] = Field(None, ge=1)
    max_inference_jobs: Optional[int] = Field(None, ge=1)
    max_workflow_jobs: Optional[int] = Field(None, ge=1)
    enforce_quota: bool = True


class ProjectVDCQuotaUpdate(BaseModel):
    cpu_quota: Optional[float] = Field(None, ge=0)
    memory_quota: Optional[float] = Field(None, ge=0)
    gpu_quota: Optional[int] = Field(None, ge=0)
    max_concurrent_jobs: Optional[int] = Field(None, ge=1)
    priority: Optional[int] = Field(None, ge=0)
    max_training_jobs: Optional[int] = Field(None, ge=1)
    max_inference_jobs: Optional[int] = Field(None, ge=1)
    max_workflow_jobs: Optional[int] = Field(None, ge=1)
    enforce_quota: Optional[bool] = None


class ProjectVDCQuotaResponse(BaseModel):
    id: UUID
    project_id: UUID
    vdc_id: UUID
    cpu_quota: float
    memory_quota: float
    gpu_quota: int
    max_concurrent_jobs: int
    used_cpu: float
    used_memory: float
    used_gpu: int
    current_jobs: int
    priority: int
    max_training_jobs: Optional[int]
    max_inference_jobs: Optional[int]
    max_workflow_jobs: Optional[int]
    current_training_jobs: int
    current_inference_jobs: int
    current_workflow_jobs: int
    enforce_quota: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuotaUsage(BaseModel):
    quota: Dict[str, float]
    used: Dict[str, float]
    available: Dict[str, float]
    usage_percentage: Dict[str, float]


# List responses
class VDCListResponse(BaseModel):
    items: List[VDCResponse]
    total: int


class ClusterListResponse(BaseModel):
    items: List[ClusterResponse]
    total: int


class ProjectVDCQuotaListResponse(BaseModel):
    items: List[ProjectVDCQuotaResponse]
    total: int
