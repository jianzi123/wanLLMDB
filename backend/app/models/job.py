"""
Job model for managing training, inference, and workflow jobs on K8s/Slurm clusters.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum, JSON, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.db.database import Base


class JobTypeEnum(str, enum.Enum):
    """Job type enumeration."""
    TRAINING = "training"
    INFERENCE = "inference"
    WORKFLOW = "workflow"


class JobExecutorEnum(str, enum.Enum):
    """Job executor type."""
    KUBERNETES = "kubernetes"
    SLURM = "slurm"


class JobStatusEnum(str, enum.Enum):
    """Job status enumeration."""
    PENDING = "pending"          # Job submitted but not started
    QUEUED = "queued"           # Job queued in scheduler
    RUNNING = "running"         # Job is running
    SUCCEEDED = "succeeded"     # Job completed successfully
    FAILED = "failed"           # Job failed
    CANCELLED = "cancelled"     # Job was cancelled by user
    TIMEOUT = "timeout"         # Job exceeded time limit


class Job(Base):
    """
    Job model for cluster job management.

    Supports three job types:
    - Training: ML model training jobs
    - Inference: Model inference/serving jobs
    - Workflow: Multi-step workflow jobs (DAG)
    """
    __tablename__ = "jobs"

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    job_type = Column(Enum(JobTypeEnum), nullable=False, index=True)
    executor = Column(Enum(JobExecutorEnum), nullable=False, index=True)
    status = Column(Enum(JobStatusEnum), default=JobStatusEnum.PENDING, nullable=False, index=True)

    # Relationships
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=True, index=True)  # Link to experiment run
    queue_id = Column(UUID(as_uuid=True), ForeignKey("job_queues.id"), nullable=True, index=True)  # Queue assignment

    # Job description
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=False)

    # Resource requirements (for quota management)
    cpu_request = Column(Float, nullable=False, default=1.0)  # CPU cores
    memory_request = Column(Float, nullable=False, default=2.0)  # GB
    gpu_request = Column(Integer, nullable=False, default=0)  # GPU cards

    # Queue management
    queue_position = Column(Integer, nullable=True)  # Position in queue
    enqueued_at = Column(DateTime(timezone=True), nullable=True)  # When job was enqueued

    # Executor-specific configuration
    executor_config = Column(JSON, nullable=False)
    """
    Example executor_config for Kubernetes Training Job:
    {
        "image": "pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime",
        "command": ["python", "train.py"],
        "args": ["--epochs", "100", "--lr", "0.001"],
        "resources": {
            "requests": {"cpu": "4", "memory": "16Gi", "nvidia.com/gpu": "2"},
            "limits": {"cpu": "8", "memory": "32Gi", "nvidia.com/gpu": "2"}
        },
        "volumes": [
            {"name": "data", "persistentVolumeClaim": {"claimName": "training-data"}}
        ],
        "volumeMounts": [
            {"name": "data", "mountPath": "/data"}
        ],
        "env": [
            {"name": "WANDB_API_KEY", "valueFrom": {"secretKeyRef": {"name": "secrets", "key": "wandb_key"}}}
        ],
        "nodeSelector": {"node-type": "gpu"},
        "tolerations": [],
        "restartPolicy": "OnFailure",
        "backoffLimit": 3,
        "ttlSecondsAfterFinished": 86400
    }

    Example executor_config for Slurm Training Job:
    {
        "partition": "gpu",
        "nodes": 4,
        "ntasks_per_node": 8,
        "cpus_per_task": 4,
        "gpus_per_node": 8,
        "time": "24:00:00",
        "mem": "256GB",
        "job_name": "training-job",
        "script": "#!/bin/bash\\nsrun python train.py",
        "modules": ["cuda/11.8", "python/3.10"],
        "env": {"WANDB_API_KEY": "xxx"},
        "working_dir": "/scratch/user/project"
    }

    Example executor_config for Kubernetes Inference Job:
    {
        "image": "mymodel:latest",
        "replicas": 3,
        "port": 8080,
        "resources": {"requests": {"cpu": "2", "memory": "4Gi"}},
        "env": [{"name": "MODEL_PATH", "value": "/models/best.pth"}],
        "service": {
            "type": "LoadBalancer",
            "port": 80,
            "targetPort": 8080
        }
    }

    Example executor_config for Kubernetes Workflow Job (Argo-style):
    {
        "entrypoint": "main",
        "templates": [
            {
                "name": "main",
                "dag": {
                    "tasks": [
                        {"name": "preprocess", "template": "preprocess-data"},
                        {"name": "train", "template": "train-model", "dependencies": ["preprocess"]},
                        {"name": "evaluate", "template": "eval-model", "dependencies": ["train"]}
                    ]
                }
            },
            {
                "name": "preprocess-data",
                "container": {
                    "image": "python:3.10",
                    "command": ["python", "preprocess.py"]
                }
            },
            {
                "name": "train-model",
                "container": {
                    "image": "pytorch/pytorch:2.1.0",
                    "command": ["python", "train.py"]
                }
            },
            {
                "name": "eval-model",
                "container": {
                    "image": "python:3.10",
                    "command": ["python", "evaluate.py"]
                }
            }
        ],
        "volumeClaimTemplates": [
            {
                "metadata": {"name": "workdir"},
                "spec": {"accessModes": ["ReadWriteOnce"], "resources": {"requests": {"storage": "10Gi"}}}
            }
        ]
    }
    """

    # Execution tracking
    external_id = Column(String(255), nullable=True, index=True)  # K8s Job name or Slurm job ID
    namespace = Column(String(255), nullable=True)  # K8s namespace or Slurm cluster name
    exit_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    metrics = Column(JSON, default=dict, nullable=False)  # Job-level metrics (e.g., GPU utilization)
    outputs = Column(JSON, default=dict, nullable=False)  # Output artifacts/results

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", backref="jobs")
    user = relationship("User", backref="jobs")
    run = relationship("Run", backref="jobs", foreign_keys=[run_id])
    queue = relationship("JobQueue", backref="jobs", foreign_keys=[queue_id])

    def __repr__(self):
        return f"<Job(id={self.id}, name={self.name}, type={self.job_type}, status={self.status})>"
