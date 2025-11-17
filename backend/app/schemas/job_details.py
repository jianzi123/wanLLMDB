"""
Job details schemas for different job types.
"""

from pydantic import BaseModel, Field, UUID4
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.schemas.job import JobResponse, JobType


class TrainingJobDetails(BaseModel):
    """详细信息 for training jobs."""
    # Training configuration
    image: Optional[str] = Field(None, description="Container image")
    command: Optional[List[str]] = Field(None, description="Training command")
    args: Optional[List[str]] = Field(None, description="Command arguments")

    # Resources
    cpu_cores: float = Field(..., description="CPU cores requested")
    memory_gb: float = Field(..., description="Memory in GB")
    gpu_count: int = Field(..., description="GPU cards requested")

    # Training specific
    epochs: Optional[int] = Field(None, description="Number of epochs")
    batch_size: Optional[int] = Field(None, description="Batch size")
    learning_rate: Optional[float] = Field(None, description="Learning rate")

    # Distributed training
    num_nodes: int = Field(1, description="Number of nodes")
    distributed: bool = Field(False, description="Is distributed training")

    # Output
    model_output_path: Optional[str] = Field(None, description="Where model will be saved")
    checkpoint_path: Optional[str] = Field(None, description="Checkpoint directory")


class InferenceJobDetails(BaseModel):
    """Detailed information for inference jobs."""
    # Service configuration
    image: Optional[str] = Field(None, description="Container image")
    replicas: int = Field(1, description="Number of replicas")
    port: int = Field(8080, description="Service port")

    # Resources per replica
    cpu_cores: float = Field(..., description="CPU cores per replica")
    memory_gb: float = Field(..., description="Memory in GB per replica")
    gpu_count: int = Field(..., description="GPUs per replica")

    # Model information
    model_name: Optional[str] = Field(None, description="Model name")
    model_version: Optional[str] = Field(None, description="Model version")
    model_path: Optional[str] = Field(None, description="Path to model file")

    # Service endpoints
    service_url: Optional[str] = Field(None, description="Service URL (if exposed)")
    health_endpoint: Optional[str] = Field(None, description="Health check endpoint")

    # Performance
    max_batch_size: Optional[int] = Field(None, description="Maximum batch size")
    timeout_seconds: Optional[int] = Field(None, description="Request timeout")


class WorkflowJobDetails(BaseModel):
    """Detailed information for workflow jobs."""
    # Workflow structure
    entrypoint: str = Field(..., description="Entrypoint template name")
    total_steps: int = Field(..., description="Total number of steps")
    completed_steps: int = Field(0, description="Completed steps")

    # DAG information
    dag_structure: Dict[str, Any] = Field(..., description="DAG structure")

    # Step details
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="List of steps with status")

    # Resources (aggregate)
    total_cpu_cores: float = Field(..., description="Total CPU across all steps")
    total_memory_gb: float = Field(..., description="Total memory across all steps")
    total_gpu_count: int = Field(..., description="Total GPUs across all steps")

    # Execution
    parallel_steps: int = Field(0, description="Steps running in parallel")
    failed_steps: List[str] = Field(default_factory=list, description="Names of failed steps")


class JobDetailedResponse(JobResponse):
    """Extended job response with type-specific details."""
    # Queue and quota information
    queue_name: Optional[str] = Field(None, description="Queue name")
    queue_position: Optional[int] = Field(None, description="Position in queue")
    enqueued_at: Optional[datetime] = Field(None, description="When job was enqueued")

    # Resource requirements
    cpu_request: float = Field(..., description="CPU cores requested")
    memory_request: float = Field(..., description="Memory in GB requested")
    gpu_request: int = Field(..., description="GPU cards requested")

    # Type-specific details
    training_details: Optional[TrainingJobDetails] = Field(None, description="Training job details")
    inference_details: Optional[InferenceJobDetails] = Field(None, description="Inference job details")
    workflow_details: Optional[WorkflowJobDetails] = Field(None, description="Workflow job details")

    # Progress and metrics
    progress_percentage: Optional[float] = Field(None, description="Progress percentage (0-100)")
    current_epoch: Optional[int] = Field(None, description="Current epoch (for training)")
    average_loss: Optional[float] = Field(None, description="Average loss (for training)")

    # Resource usage (from metrics)
    cpu_usage: Optional[float] = Field(None, description="Current CPU usage")
    memory_usage: Optional[float] = Field(None, description="Current memory usage GB")
    gpu_usage: Optional[float] = Field(None, description="Current GPU utilization %")

    class Config:
        from_attributes = True


class QueueResponse(BaseModel):
    """Queue information response."""
    id: UUID4
    project_id: UUID4
    name: str
    description: Optional[str]
    priority: int
    max_concurrent_jobs: int
    enabled: bool
    total_jobs: int
    running_jobs: int
    pending_jobs: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuotaResponse(BaseModel):
    """Project quota response."""
    id: UUID4
    project_id: UUID4

    # Limits
    cpu_quota: float
    memory_quota: float
    gpu_quota: int
    max_concurrent_jobs: int

    # Usage
    used_cpu: float
    used_memory: float
    used_gpu: int
    current_jobs: int

    # Per-type limits
    max_training_jobs: Optional[int]
    max_inference_jobs: Optional[int]
    max_workflow_jobs: Optional[int]

    # Per-type usage
    current_training_jobs: int
    current_inference_jobs: int
    current_workflow_jobs: int

    # Computed fields
    available_cpu: float
    available_memory: float
    available_gpu: int
    available_jobs: int

    cpu_usage_percent: float
    memory_usage_percent: float
    gpu_usage_percent: float
    jobs_usage_percent: float

    enforce_quota: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuotaUpdate(BaseModel):
    """Update quota limits."""
    cpu_quota: Optional[float] = Field(None, ge=0)
    memory_quota: Optional[float] = Field(None, ge=0)
    gpu_quota: Optional[int] = Field(None, ge=0)
    max_concurrent_jobs: Optional[int] = Field(None, ge=1)
    max_training_jobs: Optional[int] = Field(None, ge=0)
    max_inference_jobs: Optional[int] = Field(None, ge=0)
    max_workflow_jobs: Optional[int] = Field(None, ge=0)
    enforce_quota: Optional[bool] = None


class QueueCreate(BaseModel):
    """Create a new queue."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    priority: int = Field(0, description="Higher = higher priority")
    max_concurrent_jobs: int = Field(10, ge=1)
    enabled: bool = Field(True)


class QueueUpdate(BaseModel):
    """Update queue configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    priority: Optional[int] = None
    max_concurrent_jobs: Optional[int] = Field(None, ge=1)
    enabled: Optional[bool] = None
