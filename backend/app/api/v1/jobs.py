"""
Jobs API endpoints for cluster job management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import logging

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.job import Job, JobStatusEnum, JobTypeEnum, JobExecutorEnum
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobResponse,
    JobListResponse,
    JobStatsResponse,
    JobStatus,
    JobType,
    JobExecutor,
)
from app.schemas.job_details import (
    JobDetailedResponse,
    TrainingJobDetails,
    InferenceJobDetails,
    WorkflowJobDetails,
)
from app.repositories.job_repository import JobRepository
from app.repositories.project_repository import ProjectRepository
from app.executors import ExecutorFactory
from app.services.job_scheduler import extract_resource_requirements  # Keep for backward compat
from app.scheduling.scheduler import create_scheduler
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """
    Create and submit a new job to the cluster.

    Supports three job types:
    - **training**: ML model training jobs
    - **inference**: Model inference/serving jobs
    - **workflow**: Multi-step workflow jobs (DAG)

    And two executors:
    - **kubernetes**: Run on Kubernetes cluster
    - **slurm**: Run on Slurm cluster
    """
    job_repo = JobRepository(db)
    project_repo = ProjectRepository(db)

    # Verify project exists and user has access
    project = project_repo.get_by_id(job_data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if user owns the project (future: check team membership)
    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create jobs in this project")

    # Check if executor is configured
    executor_type = JobExecutorEnum(job_data.executor.value)
    if not ExecutorFactory.is_configured(executor_type):
        raise HTTPException(
            status_code=400,
            detail=f"Executor {job_data.executor} is not configured. Please contact administrator."
        )

    # Create job in database
    job_dict = job_data.model_dump()
    job_dict["user_id"] = current_user.id
    job_dict["status"] = JobStatusEnum.PENDING

    # Extract resource requirements from config
    job = job_repo.create(job_dict)  # Create temporarily to parse config
    cpu, memory, gpu = extract_resource_requirements(job)

    # Update job with resource requirements
    job.cpu_request = cpu
    job.memory_request = memory
    job.gpu_request = gpu
    db.commit()
    db.refresh(job)

    # Enqueue job using scheduler
    try:
        # Create scheduler with configured policy and quota provider
        scheduler = create_scheduler(
            db,
            policy_type=settings.SCHEDULING_POLICY,
            quota_provider_type=settings.QUOTA_PROVIDER,
            k8s_namespace=settings.K8S_QUOTA_NAMESPACE,
            slurm_api_url=settings.EXECUTOR_SLURM_REST_API_URL,
            slurm_auth_token=settings.EXECUTOR_SLURM_AUTH_TOKEN,
            slurm_account_prefix=settings.SLURM_ACCOUNT_PREFIX
        )

        # Enqueue the job
        if not scheduler.enqueue_job(job):
            raise HTTPException(status_code=500, detail="Failed to enqueue job")

        # Try to schedule immediately if quota available
        scheduler.schedule_pending_jobs(project_id=job.project_id)

        logger.info(
            f"Job {job.id} created and enqueued successfully using "
            f"policy={settings.SCHEDULING_POLICY}, quota_provider={settings.QUOTA_PROVIDER}"
        )

    except Exception as e:
        # Update job status to failed
        job_repo.update(job, {
            "status": JobStatusEnum.FAILED,
            "error_message": f"Failed to enqueue job: {str(e)}",
        })
        logger.error(f"Failed to enqueue job {job.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enqueue job: {str(e)}")

    db.refresh(job)
    return JobResponse.model_validate(job)


@router.get("", response_model=JobListResponse)
def list_jobs(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    run_id: Optional[UUID] = Query(None, description="Filter by run ID"),
    job_type: Optional[JobType] = Query(None, description="Filter by job type"),
    executor: Optional[JobExecutor] = Query(None, description="Filter by executor"),
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobListResponse:
    """
    List jobs with filtering and pagination.

    Filters:
    - project_id: Filter by project
    - run_id: Filter by experiment run
    - job_type: Filter by training/inference/workflow
    - executor: Filter by kubernetes/slurm
    - status: Filter by job status
    - search: Search in job name and description
    """
    job_repo = JobRepository(db)

    skip = (page - 1) * page_size

    # Build filters
    filters = {
        "skip": skip,
        "limit": page_size,
        "search": search,
    }

    if project_id:
        filters["project_id"] = project_id
    if run_id:
        filters["run_id"] = run_id
    if job_type:
        filters["job_type"] = JobTypeEnum(job_type.value)
    if executor:
        filters["executor"] = JobExecutorEnum(executor.value)
    if status:
        filters["status"] = JobStatusEnum(status.value)

    # TODO: Add permission check - only show jobs user has access to
    # For now, show all jobs (in production, filter by user or team)
    filters["user_id"] = current_user.id

    jobs, total = job_repo.list(**filters)

    return JobListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=JobStatsResponse)
def get_job_stats(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobStatsResponse:
    """Get job statistics."""
    job_repo = JobRepository(db)

    stats = job_repo.get_stats(
        project_id=project_id,
        user_id=current_user.id,
    )

    return JobStatsResponse(**stats)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Get job details by ID."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    return JobResponse.model_validate(job)


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: UUID,
    job_update: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Update job metadata (name, description, tags, etc.)."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this job")

    # Update job
    update_data = job_update.model_dump(exclude_unset=True)
    updated_job = job_repo.update(job, update_data)

    return JobResponse.model_validate(updated_job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Cancel a running job."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this job")

    # Check if job can be cancelled
    if job.status not in [JobStatusEnum.PENDING, JobStatusEnum.QUEUED, JobStatusEnum.RUNNING]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job in {job.status} state")

    # Cancel job via executor
    try:
        executor = ExecutorFactory.get_executor(job.executor)
        executor.cancel_job(job.external_id)

        # Update job status
        updated_job = job_repo.update_status(job, JobStatusEnum.CANCELLED)

        logger.info(f"Job {job.id} cancelled successfully")
        return JobResponse.model_validate(updated_job)
    except Exception as e:
        logger.error(f"Failed to cancel job {job.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.get("/{job_id}/logs")
def get_job_logs(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get job logs."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    # Get logs from executor
    try:
        executor = ExecutorFactory.get_executor(job.executor)
        logs = executor.get_job_logs(job.external_id)

        return {
            "job_id": str(job.id),
            "external_id": job.external_id,
            "logs": logs,
        }
    except Exception as e:
        logger.error(f"Failed to get logs for job {job.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")


@router.get("/{job_id}/metrics")
def get_job_metrics(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get job resource usage metrics."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    # Get metrics from executor
    try:
        executor = ExecutorFactory.get_executor(job.executor)
        metrics = executor.get_job_metrics(job.external_id)

        return {
            "job_id": str(job.id),
            "external_id": job.external_id,
            "metrics": metrics,
            "stored_metrics": job.metrics,
        }
    except Exception as e:
        logger.error(f"Failed to get metrics for job {job.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.post("/{job_id}/refresh-status", response_model=JobResponse)
def refresh_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Manually refresh job status from executor."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to refresh this job")

    # Get status from executor
    try:
        executor = ExecutorFactory.get_executor(job.executor)
        current_status = executor.get_job_status(job.external_id)

        # Update job status if changed
        if current_status != job.status:
            updated_job = job_repo.update_status(job, current_status)
            logger.info(f"Job {job.id} status updated: {job.status} -> {current_status}")
            return JobResponse.model_validate(updated_job)

        return JobResponse.model_validate(job)
    except Exception as e:
        logger.error(f"Failed to refresh status for job {job.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh status: {str(e)}")


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a job record (does not cancel running job)."""
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this job")

    # Warn if job is still running
    if job.status in [JobStatusEnum.PENDING, JobStatusEnum.QUEUED, JobStatusEnum.RUNNING]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete running job. Please cancel it first."
        )

    job_repo.delete(job)
    logger.info(f"Job {job.id} deleted")
"""
Job detailed information endpoint.
This will be appended to jobs.py
"""


@router.get("/{job_id}/details", response_model=JobDetailedResponse)
def get_job_details(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobDetailedResponse:
    """
    Get detailed job information.

    Returns type-specific details based on job type:
    - Training jobs: epoch info, learning rate, model paths
    - Inference jobs: replicas, endpoints, model info
    - Workflow jobs: DAG structure, step details
    """
    from app.repositories.job_queue_repository import JobQueueRepository

    job_repo = JobRepository(db)
    queue_repo = JobQueueRepository(db)

    job = job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check permission
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    # Build base response
    response_data = {
        **job.__dict__,
        "queue_name": None,
        "training_details": None,
        "inference_details": None,
        "workflow_details": None,
        "progress_percentage": None,
        "current_epoch": None,
        "average_loss": None,
        "cpu_usage": None,
        "memory_usage": None,
        "gpu_usage": None,
    }

    # Add queue information
    if job.queue_id:
        queue = queue_repo.get_by_id(job.queue_id)
        if queue:
            response_data["queue_name"] = queue.name

    # Parse executor config for type-specific details
    config = job.executor_config

    if job.job_type == JobTypeEnum.TRAINING:
        # Extract training-specific details
        training_details = {
            "image": config.get("image"),
            "command": config.get("command"),
            "args": config.get("args"),
            "cpu_cores": job.cpu_request,
            "memory_gb": job.memory_request,
            "gpu_count": job.gpu_request,
            "epochs": None,
            "batch_size": None,
            "learning_rate": None,
            "num_nodes": config.get("nodes", 1),
            "distributed": config.get("nodes", 1) > 1,
            "model_output_path": None,
            "checkpoint_path": None,
        }

        # Try to extract hyperparameters from args
        args = config.get("args", [])
        for i, arg in enumerate(args):
            if arg == "--epochs" and i + 1 < len(args):
                try:
                    training_details["epochs"] = int(args[i + 1])
                except:
                    pass
            elif arg == "--batch-size" and i + 1 < len(args):
                try:
                    training_details["batch_size"] = int(args[i + 1])
                except:
                    pass
            elif arg in ["--lr", "--learning-rate"] and i + 1 < len(args):
                try:
                    training_details["learning_rate"] = float(args[i + 1])
                except:
                    pass

        # Check metrics for progress
        if job.metrics and "current_epoch" in job.metrics:
            response_data["current_epoch"] = job.metrics["current_epoch"]
            if training_details["epochs"]:
                response_data["progress_percentage"] = (
                    job.metrics["current_epoch"] / training_details["epochs"] * 100
                )

        if job.metrics and "average_loss" in job.metrics:
            response_data["average_loss"] = job.metrics["average_loss"]

        response_data["training_details"] = TrainingJobDetails(**training_details)

    elif job.job_type == JobTypeEnum.INFERENCE:
        # Extract inference-specific details
        inference_details = {
            "image": config.get("image"),
            "replicas": config.get("replicas", 1),
            "port": config.get("port", 8080),
            "cpu_cores": job.cpu_request,
            "memory_gb": job.memory_request,
            "gpu_count": job.gpu_request,
            "model_name": None,
            "model_version": None,
            "model_path": None,
            "service_url": None,
            "health_endpoint": None,
            "max_batch_size": None,
            "timeout_seconds": None,
        }

        # Extract from env
        env = config.get("env", [])
        for env_var in env:
            if env_var.get("name") == "MODEL_PATH":
                inference_details["model_path"] = env_var.get("value")
            elif env_var.get("name") == "MODEL_NAME":
                inference_details["model_name"] = env_var.get("value")
            elif env_var.get("name") == "MODEL_VERSION":
                inference_details["model_version"] = env_var.get("value")

        # Service URL (if available)
        if job.external_id and job.status == JobStatusEnum.RUNNING:
            if job.executor == JobExecutorEnum.KUBERNETES:
                service_config = config.get("service", {})
                if service_config.get("type") == "LoadBalancer":
                    # Would need to query K8s to get actual external IP
                    inference_details["service_url"] = f"http://{job.external_id}.{job.namespace}.svc.cluster.local"

        response_data["inference_details"] = InferenceJobDetails(**inference_details)

    elif job.job_type == JobTypeEnum.WORKFLOW:
        # Extract workflow-specific details
        templates = config.get("templates", [])
        entrypoint = config.get("entrypoint", "main")

        # Find DAG structure
        dag_structure = {}
        total_steps = 0
        steps = []

        for template in templates:
            if template.get("name") == entrypoint and "dag" in template:
                dag_structure = template["dag"]
                if "tasks" in dag_structure:
                    total_steps = len(dag_structure["tasks"])
                    steps = [
                        {
                            "name": task.get("name"),
                            "template": task.get("template"),
                            "dependencies": task.get("dependencies", []),
                            "status": "pending",  # Would need to track this
                        }
                        for task in dag_structure["tasks"]
                    ]

        workflow_details = {
            "entrypoint": entrypoint,
            "total_steps": total_steps,
            "completed_steps": job.metrics.get("completed_steps", 0) if job.metrics else 0,
            "dag_structure": dag_structure,
            "steps": steps,
            "total_cpu_cores": job.cpu_request,
            "total_memory_gb": job.memory_request,
            "total_gpu_count": job.gpu_request,
            "parallel_steps": 0,
            "failed_steps": [],
        }

        # Calculate progress
        if total_steps > 0:
            response_data["progress_percentage"] = (
                workflow_details["completed_steps"] / total_steps * 100
            )

        response_data["workflow_details"] = WorkflowJobDetails(**workflow_details)

    # Add resource usage from metrics
    if job.metrics:
        response_data["cpu_usage"] = job.metrics.get("cpu_usage")
        response_data["memory_usage"] = job.metrics.get("memory_usage")
        response_data["gpu_usage"] = job.metrics.get("gpu_utilization")

    return JobDetailedResponse(**response_data)
