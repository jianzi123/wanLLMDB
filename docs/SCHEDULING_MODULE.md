# Scheduling Module Documentation

## Overview

The scheduling module provides a pluggable, modular architecture for job queue management and resource quota enforcement. It supports multiple scheduling policies and quota backends (local DB, Kubernetes ResourceQuota, Slurm QOS).

## Architecture

```
┌──────────────────────────────────────────────────┐
│              JobScheduler Core                   │
│  (Orchestrates job lifecycle and scheduling)     │
└───────────┬─────────────────────┬────────────────┘
            │                     │
    ┌───────▼──────────┐   ┌──────▼────────────┐
    │ SchedulingPolicy │   │  QuotaProvider    │
    │   (Interface)    │   │   (Interface)     │
    └───────┬──────────┘   └──────┬────────────┘
            │                     │
     ┌──────┴──────┐       ┌──────┴──────────────┐
     │             │       │          │           │
┌────▼───┐  ┌─────▼────┐ │    ┌─────▼────┐ ┌────▼──────┐
│  FIFO  │  │ Priority │ │    │ Local DB │ │    K8s    │
│ Policy │  │  Policy  │ │    │ Provider │ │  Provider │
└────────┘  └──────────┘ │    └──────────┘ └───────────┘
                         │
                    ┌────▼──────┐
                    │  Slurm    │
                    │ Provider  │
                    └───────────┘
```

## Components

### 1. SchedulingPolicy

Determines which job to schedule next from a queue.

**Available Policies:**

- **FIFOPolicy**: First-In-First-Out (default)
- **PriorityPolicy**: Priority-based with preemption support
- **FairSharePolicy**: Fair-share based on historical usage
- **BackfillPolicy**: Backfill smaller jobs while larger jobs wait

**Interface:**
```python
class SchedulingPolicy(ABC):
    @abstractmethod
    def select_next_job(self, queue: JobQueue, pending_jobs: List[Job]) -> Optional[Job]:
        """Select the next job to schedule."""
        pass

    def should_preempt(self, running_jobs: List[Job], new_job: Job) -> Optional[Job]:
        """Determine if preemption is needed."""
        pass
```

### 2. QuotaProvider

Manages resource quotas and can integrate with different backends.

**Available Providers:**

- **LocalQuotaProvider**: Database-based (default)
- **K8sQuotaProvider**: Kubernetes ResourceQuota integration
- **SlurmQuotaProvider**: Slurm QOS/Association integration

**Interface:**
```python
class QuotaProvider(ABC):
    @abstractmethod
    def get_quota(self, project_id: UUID) -> Optional[QuotaInfo]:
        """Get quota information."""
        pass

    @abstractmethod
    def check_quota(self, project_id: UUID, resources: Resources, job_type: JobTypeEnum) -> bool:
        """Check quota availability."""
        pass

    @abstractmethod
    def allocate_quota(self, project_id: UUID, resources: Resources, job_type: JobTypeEnum) -> bool:
        """Allocate quota."""
        pass

    @abstractmethod
    def release_quota(self, project_id: UUID, resources: Resources, job_type: JobTypeEnum) -> None:
        """Release quota."""
        pass
```

## Configuration

Add to your `.env` file:

```bash
# Scheduling Policy (fifo, priority, fairshare)
SCHEDULING_POLICY=fifo

# Quota Provider (local, k8s, slurm)
QUOTA_PROVIDER=local

# K8s Quota Provider Settings
K8S_QUOTA_NAMESPACE=wanllmdb-jobs
K8S_CREATE_RESOURCE_QUOTAS=false

# Slurm Quota Provider Settings
SLURM_ACCOUNT_PREFIX=project-
```

## Usage Examples

### 1. Local DB Quota Provider (Default)

```python
# No additional configuration needed
# Uses project_quotas table in PostgreSQL

# Set quota via API
PATCH /api/v1/queues/quota/{project_id}
{
  "cpu_quota": 100.0,
  "memory_quota": 500.0,
  "gpu_quota": 10,
  "enforce_quota": true
}
```

### 2. Kubernetes ResourceQuota Provider

**Configuration:**
```bash
QUOTA_PROVIDER=k8s
K8S_QUOTA_NAMESPACE=wanllmdb-jobs
K8S_CREATE_RESOURCE_QUOTAS=true
```

**How it works:**
1. When a project quota is created/updated, a K8s ResourceQuota object is created:
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: project-{project_id}
     namespace: wanllmdb-jobs
   spec:
     hard:
       requests.cpu: "100"
       requests.memory: "500Gi"
       requests.nvidia.com/gpu: "10"
   ```

2. When jobs are submitted, K8s ResourceQuota enforces limits automatically

3. Quota usage is synced from K8s ResourceQuota status

**Benefits:**
- Native K8s enforcement
- Prevents resource over-subscription at cluster level
- Integrated with K8s scheduler

### 3. Slurm QOS Provider

**Configuration:**
```bash
QUOTA_PROVIDER=slurm
SLURM_ACCOUNT_PREFIX=project-
EXECUTOR_SLURM_REST_API_URL=http://slurm-controller:6820
EXECUTOR_SLURM_AUTH_TOKEN=your-token
```

**How it works:**
1. Each project maps to a Slurm account: `project-{project_id}`

2. Quotas are enforced via Slurm QOS and Associations:
   ```bash
   # Create Slurm account for project
   sacctmgr add account project-abc123 \
     Description="WanLLMDB Project" \
     Organization=wanllmdb

   # Set QOS limits
   sacctmgr modify qos normal \
     GrpTRES=cpu=1000,mem=500G,gres/gpu=10
   ```

3. Jobs inherit account and QOS automatically

4. Slurm scheduler enforces limits natively

**Benefits:**
- Uses Slurm's built-in fair-share and QOS
- Integrates with existing Slurm accounting
- Supports advanced features (preemption, reservations)

## Scheduling Policies

### FIFO (First-In-First-Out)

```bash
SCHEDULING_POLICY=fifo
```

- Jobs scheduled in submission order
- Simple and predictable
- Best for single-user or small teams

### Priority

```bash
SCHEDULING_POLICY=priority
```

- Jobs have priority levels (0-100)
- Higher priority jobs scheduled first
- Supports preemption of low-priority jobs
- Best for mixed workloads (production vs development)

**Usage:**
```python
# Set job priority (requires schema update)
POST /api/v1/jobs
{
  "priority": 90,  # High priority
  ...
}
```

### Fair-Share

```bash
SCHEDULING_POLICY=fairshare
```

- Calculates fair-share score based on recent usage
- Users with lower usage get higher priority
- Best for multi-user environments
- Promotes fair resource distribution

## Integration Examples

### Example 1: K8s with Priority Scheduling

```bash
# .env
QUOTA_PROVIDER=k8s
SCHEDULING_POLICY=priority
K8S_QUOTA_NAMESPACE=wanllmdb-jobs
```

**Workflow:**
1. Project quota enforced by K8s ResourceQuota
2. High-priority jobs scheduled first
3. K8s handles pod placement and resource allocation

### Example 2: Slurm with Fair-Share

```bash
# .env
QUOTA_PROVIDER=slurm
SCHEDULING_POLICY=fairshare
SLURM_ACCOUNT_PREFIX=project-
```

**Workflow:**
1. Fair-share calculated from Slurm accounting database
2. Jobs submitted to Slurm with appropriate account
3. Slurm's fair-share scheduler handles execution

### Example 3: Hybrid (Local Quota + Priority)

```bash
# .env
QUOTA_PROVIDER=local
SCHEDULING_POLICY=priority
```

**Workflow:**
1. Quota tracked in PostgreSQL
2. Priority-based scheduling
3. Jobs submitted to either K8s or Slurm (configured per job)

## API Usage

### Get Scheduling Info

```bash
# Get current scheduler configuration
GET /api/v1/jobs/scheduler/info

# Response
{
  "policy": "priority",
  "quota_provider": "k8s",
  "active_queues": 5,
  "pending_jobs": 12
}
```

### Manual Scheduling Trigger

```bash
# Manually trigger scheduling for a project
POST /api/v1/jobs/scheduler/trigger
{
  "project_id": "abc-123"
}

# Response
{
  "scheduled_count": 3,
  "remaining_pending": 9
}
```

## Monitoring

### Quota Usage

```bash
GET /api/v1/queues/quota/{project_id}

# Response
{
  "cpu_quota": 100.0,
  "used_cpu": 75.0,
  "available_cpu": 25.0,
  "cpu_usage_percent": 75.0,

  "provider": "k8s",
  "synced_at": "2025-01-17T10:30:00Z"
}
```

### Queue Statistics

```bash
GET /api/v1/queues?project_id={id}

# Response
[
  {
    "id": "...",
    "name": "high-priority",
    "priority": 10,
    "running_jobs": 5,
    "pending_jobs": 3,
    "total_jobs": 150
  }
]
```

## Best Practices

### 1. Choose Right Provider

- **Local**: Simple setups, single cluster
- **K8s**: K8s-native deployments, want ResourceQuota enforcement
- **Slurm**: HPC environments, existing Slurm accounting

### 2. Choose Right Policy

- **FIFO**: Simple, predictable, single-user
- **Priority**: Mixed workloads, need urgent job support
- **Fair-Share**: Multi-user, want fair resource distribution

### 3. Quota Configuration

- Set realistic quotas based on cluster capacity
- Leave headroom for system overhead (10-20%)
- Monitor usage and adjust as needed

### 4. Queue Configuration

- Create separate queues for different priorities
- Set appropriate max_concurrent_jobs
- Use queue priorities to control scheduling order

## Future Enhancements

- [ ] Gang scheduling (all-or-nothing resource allocation)
- [ ] Resource reservations (advance scheduling)
- [ ] Backfill scheduling implementation
- [ ] Multi-cluster scheduling
- [ ] Cost-based scheduling
- [ ] SLA enforcement
- [ ] Quota alerts and notifications
- [ ] Historical usage analytics

## Troubleshooting

### Jobs Stuck in QUEUED

**Check quota:**
```bash
GET /api/v1/queues/quota/{project_id}
```

**Check queue capacity:**
```bash
GET /api/v1/queues?project_id={id}
```

**Manually trigger scheduling:**
```bash
POST /api/v1/jobs/scheduler/trigger
```

### K8s Quota Out of Sync

```bash
# Trigger quota sync
POST /api/v1/queues/quota/{project_id}/sync

# Check K8s ResourceQuota directly
kubectl get resourcequota project-{id} -n wanllmdb-jobs
```

### Slurm Quota Issues

```bash
# Check Slurm association
sacctmgr show association account=project-{id}

# Check QOS limits
sacctmgr show qos format=name,grptres
```
