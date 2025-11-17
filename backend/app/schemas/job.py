"""
Job schemas for API requests and responses.
"""

from pydantic import BaseModel, Field, UUID4
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class JobType(str, Enum):
    """Job type enumeration."""
    TRAINING = "training"
    INFERENCE = "inference"
    WORKFLOW = "workflow"


class JobExecutor(str, Enum):
    """Job executor type."""
    KUBERNETES = "kubernetes"
    SLURM = "slurm"


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class JobCreate(BaseModel):
    """Schema for creating a new job."""
    name: str = Field(..., min_length=1, max_length=255, description="Job name")
    job_type: JobType = Field(..., description="Type of job: training, inference, or workflow")
    executor: JobExecutor = Field(..., description="Executor: kubernetes or slurm")
    project_id: UUID4 = Field(..., description="Project ID")
    run_id: Optional[UUID4] = Field(None, description="Optional run ID to link this job to")
    description: Optional[str] = Field(None, description="Job description")
    tags: List[str] = Field(default_factory=list, description="Job tags")
    executor_config: Dict[str, Any] = Field(..., description="Executor-specific configuration")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "bert-fine-tuning",
                "job_type": "training",
                "executor": "kubernetes",
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "description": "Fine-tune BERT on custom dataset",
                "tags": ["nlp", "bert", "production"],
                "executor_config": {
                    "image": "huggingface/transformers-pytorch-gpu:latest",
                    "command": ["python", "train.py"],
                    "args": ["--model", "bert-base-uncased", "--epochs", "10"],
                    "resources": {
                        "requests": {
                            "cpu": "8",
                            "memory": "32Gi",
                            "nvidia.com/gpu": "2"
                        },
                        "limits": {
                            "cpu": "16",
                            "memory": "64Gi",
                            "nvidia.com/gpu": "2"
                        }
                    },
                    "env": [
                        {"name": "WANDB_API_KEY", "valueFrom": {"secretKeyRef": {"name": "secrets", "key": "wandb_key"}}}
                    ],
                    "nodeSelector": {"node-type": "gpu"},
                    "restartPolicy": "OnFailure",
                    "backoffLimit": 3
                }
            }
        }


class JobUpdate(BaseModel):
    """Schema for updating a job."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[JobStatus] = None
    error_message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    """Schema for job response."""
    id: UUID4
    name: str
    job_type: JobType
    executor: JobExecutor
    status: JobStatus
    project_id: UUID4
    user_id: UUID4
    run_id: Optional[UUID4]
    description: Optional[str]
    tags: List[str]
    executor_config: Dict[str, Any]
    external_id: Optional[str]
    namespace: Optional[str]
    exit_code: Optional[int]
    error_message: Optional[str]
    submitted_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    metrics: Dict[str, Any]
    outputs: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Schema for job list response."""
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int


class JobStatsResponse(BaseModel):
    """Schema for job statistics."""
    total: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    by_executor: Dict[str, int]
