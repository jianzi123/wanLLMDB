# VDC (Virtual Data Center) 设计方案

## 1. 概述

VDC（Virtual Data Center，虚拟数据中心）是一个资源池抽象层，用于统一管理多个物理计算集群（Kubernetes、Slurm），为多个项目提供资源隔离、配额管理和智能调度能力。

## 2. 架构层级

```
┌─────────────────────────────────────────────────────────┐
│                    Organization (未来)                   │
└─────────────────────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────┐
│                  VDC (Virtual Data Center)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Cluster 1   │  │  Cluster 2   │  │  Cluster 3   │ │
│  │ (K8s-GPU)    │  │ (K8s-CPU)    │  │ (Slurm-HPC)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                         │
│  Total Resources: 1000 CPU, 2TB RAM, 100 GPU           │
└─────────────────────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │Project A │   │Project B │   │Project C │
        │ Quota:   │   │ Quota:   │   │ Quota:   │
        │ 300 CPU  │   │ 400 CPU  │   │ 300 CPU  │
        └──────────┘   └──────────┘   └──────────┘
              │              │              │
              ↓              ↓              ↓
           Jobs          Jobs          Jobs
```

## 3. 核心概念

### 3.1 VDC (Virtual Data Center)
- **定义**：虚拟数据中心，包含多个物理集群的资源池
- **功能**：
  - 聚合多个集群的资源
  - 提供统一的资源视图
  - 管理总配额和项目配额分配
  - 支持多租户隔离

### 3.2 Cluster（物理集群）
- **定义**：实际的计算集群（K8s或Slurm）
- **属性**：
  - 集群类型（kubernetes/slurm）
  - 连接配置（API endpoint、认证信息）
  - 资源容量（CPU、Memory、GPU）
  - 健康状态
  - 标签（用于调度亲和性）

### 3.3 VDC Quota（VDC配额）
- **定义**：VDC级别的总资源配额
- **层级**：
  - VDC总配额 = 所有集群资源之和（或手动设置上限）
  - Project配额 ≤ VDC总配额
  - 所有Project配额之和可以超过VDC配额（超卖）

## 4. 数据模型设计

### 4.1 VDC Model

```python
class VDC(Base):
    """Virtual Data Center - 虚拟数据中心"""
    __tablename__ = "vdcs"

    id: UUID
    name: str                    # VDC名称，如 "gpu-cluster-pool"
    description: str             # 描述

    # 总资源配额（可选，None表示使用集群资源总和）
    total_cpu_quota: float       # 总CPU核心数
    total_memory_quota: float    # 总内存 (GB)
    total_gpu_quota: int         # 总GPU卡数

    # 当前使用量
    used_cpu: float
    used_memory: float
    used_gpu: int

    # 配置
    enabled: bool                # 是否启用
    allow_overcommit: bool       # 是否允许项目配额超卖
    overcommit_ratio: float      # 超卖比例，如 1.5 表示允许150%超卖

    # 调度策略
    default_scheduling_policy: str  # 默认调度策略
    cluster_selection_strategy: str # 集群选择策略

    # 关系
    clusters: List[Cluster]      # VDC包含的集群
    projects: List[Project]      # 使用此VDC的项目

    created_at: datetime
    updated_at: datetime
```

### 4.2 Cluster Model

```python
class ClusterTypeEnum(str, enum.Enum):
    KUBERNETES = "kubernetes"
    SLURM = "slurm"

class ClusterStatusEnum(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    MAINTENANCE = "maintenance"

class Cluster(Base):
    """物理计算集群"""
    __tablename__ = "clusters"

    id: UUID
    vdc_id: UUID                 # 所属VDC
    name: str                    # 集群名称，如 "k8s-gpu-01"
    description: str
    cluster_type: ClusterTypeEnum

    # 连接配置
    endpoint: str                # API endpoint
    config: dict                 # 连接配置（kubeconfig、认证信息等）
    namespace: str               # K8s namespace 或 Slurm partition

    # 资源容量
    total_cpu: float
    total_memory: float
    total_gpu: int

    # 当前资源使用
    used_cpu: float
    used_memory: float
    used_gpu: int

    # 状态
    status: ClusterStatusEnum
    last_heartbeat: datetime     # 最后健康检查时间

    # 调度配置
    enabled: bool                # 是否接受新作业
    priority: int                # 集群优先级
    weight: float                # 调度权重
    labels: dict                 # 集群标签（用于亲和性）

    # 限制
    max_jobs_per_user: int       # 每用户最大作业数
    max_total_jobs: int          # 集群最大总作业数

    created_at: datetime
    updated_at: datetime
```

### 4.3 ProjectVDCQuota Model

```python
class ProjectVDCQuota(Base):
    """项目在VDC中的配额"""
    __tablename__ = "project_vdc_quotas"

    id: UUID
    project_id: UUID
    vdc_id: UUID

    # 配额限制
    cpu_quota: float
    memory_quota: float
    gpu_quota: int
    max_concurrent_jobs: int

    # 当前使用
    used_cpu: float
    used_memory: float
    used_gpu: int
    current_jobs: int

    # 优先级
    priority: int                # 项目在VDC中的优先级

    # 作业类型限制
    max_training_jobs: int
    max_inference_jobs: int
    max_workflow_jobs: int

    enforce_quota: bool

    created_at: datetime
    updated_at: datetime
```

### 4.4 Job Model 更新

```python
class Job(Base):
    """作业模型 - 添加VDC和Cluster字段"""
    # ... 现有字段 ...

    vdc_id: UUID                 # 提交到的VDC
    cluster_id: UUID             # 实际执行的集群（调度后分配）

    # 集群亲和性
    preferred_clusters: List[UUID]  # 优先调度到这些集群
    required_labels: dict           # 必需的集群标签
```

## 5. 调度策略

### 5.1 集群选择策略

#### 1. **Load Balancing（负载均衡）**
- 选择当前负载最低的集群
- 基于资源使用率（CPU、Memory、GPU）
- 适用于通用作业

#### 2. **Resource Fit（资源匹配）**
- 选择资源最匹配的集群
- 优先选择能刚好满足资源需求的集群
- 避免资源浪费

#### 3. **Priority Based（优先级）**
- 根据集群优先级和权重选择
- 高优先级集群优先使用
- 支持集群降级策略

#### 4. **Affinity Based（亲和性）**
- 根据作业的集群亲和性要求选择
- 支持必需标签匹配
- 支持优先集群列表

#### 5. **Cost Optimized（成本优化）**
- 为每个集群配置成本权重
- 优先选择成本较低的集群
- 适用于有成本考虑的场景

### 5.2 调度流程

```
1. 用户提交Job到VDC
   ↓
2. VDC Scheduler检查项目配额
   ↓
3. 应用集群选择策略，获取候选集群列表
   ↓
4. 对每个候选集群：
   - 检查集群健康状态
   - 检查集群资源可用性
   - 检查集群作业数限制
   - 计算匹配分数
   ↓
5. 选择分数最高的集群
   ↓
6. 分配cluster_id，提交到集群executor
   ↓
7. 更新VDC和Project配额使用量
```

## 6. VDC调度器设计

### 6.1 VDCScheduler类

```python
class VDCScheduler:
    """VDC级别的调度器"""

    def __init__(
        self,
        db: Session,
        cluster_selector: ClusterSelector,
        quota_manager: VDCQuotaManager
    ):
        self.db = db
        self.cluster_selector = cluster_selector
        self.quota_manager = quota_manager

    def schedule_job(self, job: Job) -> bool:
        """调度作业到VDC中的某个集群"""

        # 1. 检查VDC配额
        if not self.quota_manager.check_vdc_quota(job):
            return False

        # 2. 检查项目配额
        if not self.quota_manager.check_project_quota(job):
            return False

        # 3. 选择目标集群
        cluster = self.cluster_selector.select_cluster(job)
        if not cluster:
            return False

        # 4. 分配集群并提交
        job.cluster_id = cluster.id

        # 5. 分配配额
        self.quota_manager.allocate_quota(job)

        # 6. 提交到集群executor
        executor = self._get_cluster_executor(cluster)
        external_id = executor.submit_job(job)
        job.external_id = external_id
        job.status = JobStatusEnum.RUNNING

        return True
```

### 6.2 ClusterSelector类

```python
class ClusterSelector:
    """集群选择器"""

    def select_cluster(
        self,
        job: Job,
        strategy: str = "load_balancing"
    ) -> Optional[Cluster]:
        """根据策略选择最佳集群"""

        # 获取候选集群
        candidates = self._get_candidate_clusters(job)

        if not candidates:
            return None

        # 应用选择策略
        if strategy == "load_balancing":
            return self._select_by_load(candidates, job)
        elif strategy == "resource_fit":
            return self._select_by_resource_fit(candidates, job)
        elif strategy == "priority":
            return self._select_by_priority(candidates, job)
        elif strategy == "affinity":
            return self._select_by_affinity(candidates, job)
        else:
            return self._select_by_load(candidates, job)

    def _get_candidate_clusters(self, job: Job) -> List[Cluster]:
        """获取候选集群列表"""
        vdc = job.vdc
        clusters = []

        for cluster in vdc.clusters:
            # 检查集群是否可用
            if not cluster.enabled or cluster.status != ClusterStatusEnum.HEALTHY:
                continue

            # 检查集群类型匹配
            if not self._cluster_type_matches(cluster, job):
                continue

            # 检查资源可用性
            if not self._has_available_resources(cluster, job):
                continue

            # 检查标签亲和性
            if job.required_labels and not self._labels_match(cluster, job):
                continue

            clusters.append(cluster)

        return clusters
```

## 7. API设计

### 7.1 VDC Management APIs

```
POST   /api/v1/vdcs                    # 创建VDC
GET    /api/v1/vdcs                    # 列出VDC
GET    /api/v1/vdcs/{vdc_id}           # 获取VDC详情
PUT    /api/v1/vdcs/{vdc_id}           # 更新VDC
DELETE /api/v1/vdcs/{vdc_id}           # 删除VDC

GET    /api/v1/vdcs/{vdc_id}/stats     # VDC统计信息
GET    /api/v1/vdcs/{vdc_id}/resources # VDC资源使用情况
```

### 7.2 Cluster Management APIs

```
POST   /api/v1/vdcs/{vdc_id}/clusters           # 添加集群到VDC
GET    /api/v1/vdcs/{vdc_id}/clusters           # 列出VDC的集群
GET    /api/v1/clusters/{cluster_id}            # 获取集群详情
PUT    /api/v1/clusters/{cluster_id}            # 更新集群
DELETE /api/v1/clusters/{cluster_id}            # 从VDC移除集群

POST   /api/v1/clusters/{cluster_id}/health     # 健康检查
GET    /api/v1/clusters/{cluster_id}/stats      # 集群统计
GET    /api/v1/clusters/{cluster_id}/jobs       # 集群上的作业
```

### 7.3 Project VDC Quota APIs

```
POST   /api/v1/vdcs/{vdc_id}/quotas                      # 为项目分配VDC配额
GET    /api/v1/vdcs/{vdc_id}/quotas                      # 列出VDC的所有项目配额
GET    /api/v1/projects/{project_id}/vdc-quotas         # 项目的VDC配额
PUT    /api/v1/vdc-quotas/{quota_id}                    # 更新配额
DELETE /api/v1/vdc-quotas/{quota_id}                    # 删除配额
```

### 7.4 Job Submission (更新)

```
POST   /api/v1/jobs
{
    "name": "training-job",
    "project_id": "...",
    "vdc_id": "...",              # 指定VDC（新增）
    "job_type": "training",
    "executor_config": {...},
    "preferred_clusters": ["..."], # 优先集群（可选）
    "required_labels": {           # 必需标签（可选）
        "gpu_type": "a100",
        "region": "us-west"
    }
}
```

## 8. 实现阶段

### Phase 1: 基础设施（第1周）
- [ ] 创建VDC、Cluster、ProjectVDCQuota数据模型
- [ ] 数据库迁移
- [ ] 基础CRUD API

### Phase 2: 集群管理（第2周）
- [ ] 集群注册和配置
- [ ] 集群健康检查服务
- [ ] 集群资源监控

### Phase 3: VDC调度器（第3周）
- [ ] VDCScheduler实现
- [ ] ClusterSelector实现
- [ ] 多种集群选择策略
- [ ] VDC配额管理

### Phase 4: 集成和优化（第4周）
- [ ] 集成到现有Job提交流程
- [ ] 向后兼容（支持不使用VDC的场景）
- [ ] 监控和告警
- [ ] 文档和测试

## 9. 向后兼容

为了不破坏现有系统，采用以下兼容策略：

1. **可选VDC**：Job的vdc_id字段可为空
   - 如果vdc_id为空，使用原有的直接executor提交方式
   - 如果vdc_id不为空，使用VDC调度

2. **默认VDC**：可以创建一个默认VDC，包含现有的executor配置
   - 自动迁移现有配置到默认VDC

3. **渐进式迁移**：
   - 先支持单集群VDC
   - 再支持多集群VDC
   - 最后支持高级调度策略

## 10. 监控指标

### VDC级别
- 总资源容量和使用率
- 项目配额分配和使用情况
- 集群健康状态
- 作业分布（按集群）

### Cluster级别
- 资源使用率趋势
- 作业成功率
- 平均作业等待时间
- 集群可用性（uptime）

### Project级别
- 配额使用率
- 作业分布（按集群）
- 资源浪费率

## 11. 安全考虑

1. **集群凭证管理**：
   - 加密存储集群连接配置
   - 支持Secret引用，不直接存储敏感信息

2. **权限控制**：
   - VDC管理员权限
   - 项目级别的VDC访问控制

3. **资源隔离**：
   - K8s namespace隔离
   - Slurm account隔离

## 12. 未来扩展

1. **跨VDC调度**：支持作业在多个VDC间迁移
2. **自动扩缩容**：集群资源自动扩展
3. **成本分析**：资源使用成本统计和优化建议
4. **预留资源**：支持资源预留和提前分配
5. **作业迁移**：支持运行中作业的集群间迁移
