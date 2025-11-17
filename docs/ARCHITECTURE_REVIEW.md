# Queue and Quota System Architecture Review

## Current Implementation Analysis

### Strengths ✅

1. **Comprehensive Data Model**
   - Well-designed JobQueue and ProjectQuota models
   - Proper tracking of resource usage
   - Support for per-type job limits

2. **Complete API Coverage**
   - Full CRUD operations for queues and quotas
   - Detailed job information endpoints
   - Good separation of concerns

3. **Resource Extraction**
   - Automatic resource requirement parsing from executor configs
   - Support for both K8s and Slurm formats

### Issues and Improvements Needed ❌

1. **Tight Coupling**
   ```python
   # JobScheduler directly uses ExecutorFactory
   executor = ExecutorFactory.get_executor(job.executor)
   external_id = executor.submit_job(job)
   ```
   - **Problem**: Scheduler is tightly coupled to executors
   - **Impact**: Hard to test, difficult to extend

2. **No Native Integration**
   - Current quota system is custom implementation
   - Doesn't leverage K8s ResourceQuotas
   - Doesn't use Slurm QOS/Associations
   - **Problem**: Duplicate resource management
   - **Impact**: Can get out of sync with actual cluster state

3. **Single Scheduling Strategy**
   - Only supports FIFO scheduling
   - No support for priority queues, fair-share, backfill
   - **Problem**: Not flexible enough for real-world use
   - **Impact**: Limited scheduling policies

4. **Missing Features**
   - No preemption support
   - No job priorities within queue
   - No resource reservations
   - No gang scheduling

## Proposed Architecture

### 1. Modular Design

```
┌─────────────────────────────────────────────────────┐
│                 Job Submission API                  │
└────────────────────┬────────────────────────────────┘
                     │
         ┌───────────▼────────────┐
         │   JobScheduler Core    │  ← Orchestrator
         └───────────┬────────────┘
                     │
         ┌───────────┴────────────┐
         │                        │
┌────────▼─────────┐    ┌────────▼──────────┐
│ SchedulingPolicy │    │  QuotaProvider    │  ← Abstractions
└────────┬─────────┘    └────────┬──────────┘
         │                        │
    ┌────┴────┐            ┌──────┴──────┐
    │         │            │             │
┌───▼──┐ ┌───▼──┐    ┌────▼───┐   ┌────▼────┐
│ FIFO │ │Priority│  │ K8s    │   │ Slurm   │  ← Implementations
│Policy│ │ Policy │  │ Quota  │   │ QOS     │
└──────┘ └────────┘  └────────┘   └─────────┘
```

### 2. Key Components

#### SchedulingPolicy (Abstract)
```python
class SchedulingPolicy(ABC):
    @abstractmethod
    def select_next_job(self, queue: JobQueue) -> Optional[Job]:
        """Select next job to schedule from queue."""
        pass

    @abstractmethod
    def should_preempt(self, running_jobs: List[Job], new_job: Job) -> Optional[Job]:
        """Determine if a running job should be preempted."""
        pass
```

#### QuotaProvider (Abstract)
```python
class QuotaProvider(ABC):
    @abstractmethod
    def check_quota(self, project_id: UUID, resources: Resources) -> bool:
        """Check if quota is available."""
        pass

    @abstractmethod
    def allocate_quota(self, project_id: UUID, resources: Resources) -> bool:
        """Allocate quota for a job."""
        pass

    @abstractmethod
    def release_quota(self, project_id: UUID, resources: Resources) -> None:
        """Release quota when job completes."""
        pass

    @abstractmethod
    def sync_quota_state(self) -> None:
        """Sync quota state with backend (K8s/Slurm)."""
        pass
```

### 3. Integration Strategies

#### Kubernetes Integration

**Option A: Use K8s ResourceQuota (Recommended)**
```python
class K8sQuotaProvider(QuotaProvider):
    def __init__(self, namespace: str):
        self.core_v1 = client.CoreV1Api()
        self.namespace = namespace

    def check_quota(self, project_id: UUID, resources: Resources) -> bool:
        # Read K8s ResourceQuota
        quota = self.core_v1.read_namespaced_resource_quota(
            name=f"project-{project_id}",
            namespace=self.namespace
        )
        # Compare requested vs available
        return self._has_capacity(quota, resources)

    def sync_quota_state(self):
        # Sync DB quota with K8s ResourceQuota status
        quotas = self.core_v1.list_namespaced_resource_quota(self.namespace)
        for quota in quotas.items:
            self._update_db_quota(quota)
```

**Option B: Hybrid Approach**
- Use custom DB quota for tracking
- Create K8s ResourceQuota objects to enforce
- Sync both ways

#### Slurm Integration

**Use Slurm QOS and Associations**
```python
class SlurmQuotaProvider(QuotaProvider):
    def __init__(self, rest_api_url: str):
        self.api = SlurmRestClient(rest_api_url)

    def check_quota(self, project_id: UUID, resources: Resources) -> bool:
        # Query Slurm association for project
        assoc = self.api.get_association(account=f"project-{project_id}")

        # Check QOS limits
        qos = self.api.get_qos(assoc.qos)
        return qos.has_capacity(resources)

    def allocate_quota(self, project_id: UUID, resources: Resources) -> bool:
        # Slurm handles this automatically via sacctmgr
        # We just record the allocation in DB
        return True
```

### 4. Scheduling Strategies

#### FIFO Policy (Current)
```python
class FIFOSchedulingPolicy(SchedulingPolicy):
    def select_next_job(self, queue: JobQueue) -> Optional[Job]:
        return queue.jobs.filter(status='QUEUED').order_by('queue_position').first()
```

#### Priority Policy
```python
class PrioritySchedulingPolicy(SchedulingPolicy):
    def select_next_job(self, queue: JobQueue) -> Optional[Job]:
        return queue.jobs.filter(status='QUEUED').order_by('priority DESC', 'submitted_at').first()
```

#### Fair-Share Policy
```python
class FairShareSchedulingPolicy(SchedulingPolicy):
    def select_next_job(self, queue: JobQueue) -> Optional[Job]:
        # Calculate fair-share scores
        user_usage = self._calculate_user_usage()
        jobs = queue.jobs.filter(status='QUEUED').all()

        # Sort by fair-share score
        return min(jobs, key=lambda j: user_usage[j.user_id])
```

## Recommendations

### Phase 1: Refactor (Priority: High)
1. Extract QuotaProvider interface
2. Extract SchedulingPolicy interface
3. Implement LocalQuotaProvider (current DB-based)
4. Implement FIFOSchedulingPolicy

### Phase 2: K8s Integration (Priority: Medium)
1. Implement K8sQuotaProvider
2. Add K8s ResourceQuota creation
3. Add bidirectional sync

### Phase 3: Slurm Integration (Priority: Medium)
1. Implement SlurmQuotaProvider
2. Integrate with sacctmgr
3. Support Slurm Associations

### Phase 4: Advanced Features (Priority: Low)
1. Add PrioritySchedulingPolicy
2. Add FairShareSchedulingPolicy
3. Add preemption support
4. Add gang scheduling

## Migration Path

1. **Keep backward compatibility**: Current API should continue working
2. **Add provider configuration**: Allow choosing quota provider
3. **Gradual migration**: Start with LocalQuotaProvider, then add K8s/Slurm
4. **Testing**: Comprehensive tests for each provider

## Configuration Example

```python
# settings.py
QUOTA_PROVIDER = "local"  # or "kubernetes" or "slurm"
SCHEDULING_POLICY = "fifo"  # or "priority" or "fairshare"

# For K8s
K8S_QUOTA_NAMESPACE = "wanllmdb-jobs"
K8S_CREATE_RESOURCE_QUOTAS = True

# For Slurm
SLURM_DEFAULT_QOS = "normal"
SLURM_ACCOUNT_PREFIX = "project-"
```
