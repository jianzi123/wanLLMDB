# Cluster Integration Guide

This guide explains how to use the K8s and Slurm cluster integration features for running training, inference, and workflow jobs.

## Overview

WanLLMDB supports running jobs on two types of clusters:
- **Kubernetes**: Container-based orchestration
- **Slurm**: HPC cluster workload manager

Three job types are supported:
1. **Training**: ML model training jobs
2. **Inference**: Model serving/inference jobs
3. **Workflow**: Multi-step DAG-based workflows

## Configuration

### Kubernetes Executor

Add these environment variables to your `.env` file:

```bash
# Enable Kubernetes executor
EXECUTOR_KUBERNETES_ENABLED=true

# Optional: Path to kubeconfig (uses in-cluster config if not specified)
EXECUTOR_KUBERNETES_KUBECONFIG=/path/to/kubeconfig

# Default namespace for jobs
EXECUTOR_KUBERNETES_NAMESPACE=wanllmdb-jobs

# Service account for jobs
EXECUTOR_KUBERNETES_SERVICE_ACCOUNT=job-runner
```

#### Prerequisites

1. Create namespace:
```bash
kubectl create namespace wanllmdb-jobs
```

2. Create service account with permissions:
```bash
kubectl create serviceaccount job-runner -n wanllmdb-jobs

kubectl create clusterrole job-runner --verb=get,list,watch,create,delete --resource=jobs,deployments,services,pods,configmaps

kubectl create clusterrolebinding job-runner --clusterrole=job-runner --serviceaccount=wanllmdb-jobs:job-runner
```

3. (Optional) Create image pull secrets:
```bash
kubectl create secret docker-registry regcred \
  --docker-server=your-registry.com \
  --docker-username=your-username \
  --docker-password=your-password \
  --docker-email=your-email \
  -n wanllmdb-jobs
```

### Slurm Executor

Add these environment variables:

```bash
# Enable Slurm executor
EXECUTOR_SLURM_ENABLED=true

# Slurm REST API endpoint
EXECUTOR_SLURM_REST_API_URL=http://slurm-controller:6820

# Authentication token (format: username:token or JWT token)
EXECUTOR_SLURM_AUTH_TOKEN=wanllmdb:your-slurm-token

# Default partition
EXECUTOR_SLURM_PARTITION=gpu

# Default account (optional)
EXECUTOR_SLURM_ACCOUNT=ml_team
```

#### Prerequisites

1. Install and configure Slurm REST API (slurmrestd)
2. Generate authentication token for your user
3. Ensure backend can access Slurm REST API URL

## Usage Examples

### 1. Training Job on Kubernetes

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "bert-finetuning",
    "job_type": "training",
    "executor": "kubernetes",
    "project_id": "your-project-id",
    "description": "Fine-tune BERT on custom dataset",
    "tags": ["nlp", "bert"],
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
        {
          "name": "WANDB_API_KEY",
          "valueFrom": {
            "secretKeyRef": {
              "name": "secrets",
              "key": "wandb_key"
            }
          }
        }
      ],
      "nodeSelector": {
        "node-type": "gpu"
      },
      "volumes": [
        {
          "name": "data",
          "persistentVolumeClaim": {
            "claimName": "training-data"
          }
        }
      ],
      "volumeMounts": [
        {
          "name": "data",
          "mountPath": "/data"
        }
      ],
      "restartPolicy": "OnFailure",
      "backoffLimit": 3,
      "ttlSecondsAfterFinished": 86400
    }
  }'
```

### 2. Training Job on Slurm

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "distributed-training",
    "job_type": "training",
    "executor": "slurm",
    "project_id": "your-project-id",
    "description": "Multi-node distributed training",
    "executor_config": {
      "partition": "gpu",
      "nodes": 4,
      "ntasks_per_node": 8,
      "cpus_per_task": 4,
      "gpus_per_node": 8,
      "time": "24:00:00",
      "mem": "256GB",
      "script": "#!/bin/bash\\nmodule load cuda/11.8\\nmodule load python/3.10\\nsrun python train.py --distributed",
      "modules": ["cuda/11.8", "python/3.10"],
      "env": {
        "WANDB_API_KEY": "xxx",
        "MASTER_PORT": "29500"
      },
      "working_dir": "/scratch/user/project"
    }
  }'
```

### 3. Inference Job on Kubernetes

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "model-serving",
    "job_type": "inference",
    "executor": "kubernetes",
    "project_id": "your-project-id",
    "description": "Serve BERT model for inference",
    "executor_config": {
      "image": "myregistry/bert-serve:latest",
      "replicas": 3,
      "port": 8080,
      "resources": {
        "requests": {
          "cpu": "2",
          "memory": "4Gi",
          "nvidia.com/gpu": "1"
        },
        "limits": {
          "cpu": "4",
          "memory": "8Gi",
          "nvidia.com/gpu": "1"
        }
      },
      "env": [
        {
          "name": "MODEL_PATH",
          "value": "/models/best.pth"
        }
      ],
      "service": {
        "type": "LoadBalancer",
        "port": 80,
        "targetPort": 8080
      }
    }
  }'
```

### 4. Workflow Job on Kubernetes

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ml-pipeline",
    "job_type": "workflow",
    "executor": "kubernetes",
    "project_id": "your-project-id",
    "description": "End-to-end ML pipeline",
    "executor_config": {
      "entrypoint": "main",
      "templates": [
        {
          "name": "main",
          "dag": {
            "tasks": [
              {
                "name": "preprocess",
                "template": "preprocess-data"
              },
              {
                "name": "train",
                "template": "train-model",
                "dependencies": ["preprocess"]
              },
              {
                "name": "evaluate",
                "template": "eval-model",
                "dependencies": ["train"]
              }
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
      ]
    }
  }'
```

## API Endpoints

### List Jobs

```bash
GET /api/v1/jobs?project_id={id}&status=running&job_type=training
```

Query parameters:
- `project_id`: Filter by project
- `run_id`: Filter by experiment run
- `job_type`: Filter by training/inference/workflow
- `executor`: Filter by kubernetes/slurm
- `status`: Filter by pending/queued/running/succeeded/failed/cancelled/timeout
- `search`: Search in name and description
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

### Get Job Details

```bash
GET /api/v1/jobs/{job_id}
```

### Cancel Job

```bash
POST /api/v1/jobs/{job_id}/cancel
```

### Get Job Logs

```bash
GET /api/v1/jobs/{job_id}/logs
```

### Get Job Metrics

```bash
GET /api/v1/jobs/{job_id}/metrics
```

### Refresh Job Status

```bash
POST /api/v1/jobs/{job_id}/refresh-status
```

### Get Job Statistics

```bash
GET /api/v1/jobs/stats?project_id={id}
```

### Delete Job

```bash
DELETE /api/v1/jobs/{job_id}
```

Note: Can only delete finished jobs (succeeded/failed/cancelled)

## Job Status Lifecycle

```
PENDING → QUEUED → RUNNING → SUCCEEDED/FAILED/TIMEOUT
                           ↓
                       CANCELLED
```

- **PENDING**: Job created but not yet submitted to executor
- **QUEUED**: Job submitted and waiting in queue
- **RUNNING**: Job is currently executing
- **SUCCEEDED**: Job completed successfully
- **FAILED**: Job failed with error
- **CANCELLED**: Job was cancelled by user
- **TIMEOUT**: Job exceeded time limit

## Monitoring

### Automatic Status Sync

To keep job statuses up-to-date, you can run a background task that periodically syncs status from executors:

```python
# backend/app/tasks/job_sync.py (to be implemented)
async def sync_active_jobs():
    """Sync status for all active jobs."""
    job_repo = JobRepository(db)
    active_jobs = job_repo.get_active_jobs()

    for job in active_jobs:
        try:
            executor = ExecutorFactory.get_executor(job.executor)
            current_status = executor.get_job_status(job.external_id)

            if current_status != job.status:
                job_repo.update_status(job, current_status)
        except Exception as e:
            logger.error(f"Failed to sync job {job.id}: {e}")
```

Run this task every 30 seconds using a scheduler like APScheduler or Celery.

## Integration with Runs

Link jobs to experiment runs:

```json
{
  "name": "training-job",
  "job_type": "training",
  "executor": "kubernetes",
  "project_id": "...",
  "run_id": "your-run-id",  // Link to experiment run
  "executor_config": { ... }
}
```

This creates a connection between the cluster job and the experiment tracking run, allowing you to see which jobs produced which results.

## Best Practices

### Kubernetes

1. **Resource Requests**: Always set resource requests to help scheduler
2. **Tolerations**: Use tolerations for GPU nodes if needed
3. **Node Selectors**: Target specific node pools (e.g., gpu nodes)
4. **Image Pull Policy**: Use `IfNotPresent` for faster pod startup
5. **TTL**: Set `ttlSecondsAfterFinished` to clean up old jobs
6. **Secrets**: Use Kubernetes secrets for sensitive data

### Slurm

1. **Partition Selection**: Choose appropriate partition (gpu/cpu)
2. **Resource Requests**: Request realistic resources to avoid queue time
3. **Time Limits**: Set appropriate time limits
4. **Output Files**: Specify output/error file paths
5. **Modules**: Load required modules in your script
6. **Working Directory**: Set correct working directory

## Troubleshooting

### Job Stuck in PENDING

**Kubernetes:**
- Check namespace exists
- Verify service account has permissions
- Check resource availability with `kubectl describe node`
- Check pod events: `kubectl describe pod <pod-name> -n wanllmdb-jobs`

**Slurm:**
- Check partition status: `sinfo`
- Check job queue: `squeue -u your-user`
- Check job hold reason: `squeue -j <job-id>`

### Job Failed Immediately

**Kubernetes:**
- Check pod logs: `kubectl logs <pod-name> -n wanllmdb-jobs`
- Check pod events: `kubectl describe pod <pod-name> -n wanllmdb-jobs`
- Verify image exists and is accessible
- Check resource limits

**Slurm:**
- Check job output files
- Use `sacct -j <job-id> -o JobID,State,ExitCode`
- Check slurm logs on controller

### Cannot Submit Jobs

- Verify executor is enabled in configuration
- Check backend logs for initialization errors
- For K8s: verify kubeconfig or in-cluster config
- For Slurm: verify REST API is accessible and token is valid

## Architecture

```
┌─────────────┐
│   Backend   │
│   (FastAPI) │
└──────┬──────┘
       │
       ├─────────────────┬─────────────────┐
       │                 │                 │
┌──────▼──────┐  ┌───────▼──────┐  ┌──────▼──────┐
│ Job Model   │  │ K8s Executor │  │Slurm Executor│
│ (Database)  │  │              │  │              │
└─────────────┘  └───────┬──────┘  └──────┬───────┘
                         │                │
                         │                │
                 ┌───────▼──────┐  ┌──────▼────────┐
                 │ Kubernetes   │  │ Slurm Cluster │
                 │ Cluster      │  │               │
                 └──────────────┘  └───────────────┘
```

## Example: Complete Training Workflow

1. Create project via API
2. Submit training job with K8s executor
3. Monitor job status with `GET /api/v1/jobs/{id}`
4. Check logs with `GET /api/v1/jobs/{id}/logs`
5. Link job to experiment run for tracking
6. Job saves results to shared storage
7. Create inference job using trained model
8. Deploy inference service to production

## Future Enhancements

- [ ] Web UI for job submission
- [ ] Job templates library
- [ ] Auto-scaling based on queue depth
- [ ] Cost tracking and budgets
- [ ] Multi-cluster job distribution
- [ ] Argo Workflows native integration
- [ ] Kubeflow integration
- [ ] Ray cluster integration
