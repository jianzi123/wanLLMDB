# wanLLMDB 技术架构设计文档

## 目录
1. [系统架构概览](#系统架构概览)
2. [前端架构](#前端架构)
3. [后端架构](#后端架构)
4. [数据库设计](#数据库设计)
5. [API设计](#api设计)
6. [安全设计](#安全设计)
7. [性能优化](#性能优化)
8. [部署架构](#部署架构)

---

## 系统架构概览

### 架构原则
- **微服务架构**: 松耦合、高内聚的服务设计
- **API优先**: 前后端分离，API作为核心契约
- **可扩展性**: 水平扩展，支持大规模并发
- **高可用性**: 无单点故障，故障自动恢复
- **数据一致性**: 强一致性与最终一致性的平衡

### 技术栈总览

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 前端框架 | React 18 + TypeScript | 类型安全的现代化前端 |
| UI组件 | Ant Design + Recharts | 企业级UI + 数据可视化 |
| 状态管理 | Redux Toolkit | 可预测的状态管理 |
| 后端语言 | Python 3.11 + Go | Python主服务 + Go高性能服务 |
| Web框架 | FastAPI + Gin | 异步高性能 |
| 关系数据库 | PostgreSQL 15 | 主数据存储 |
| 时序数据库 | TimescaleDB | 指标数据 |
| 缓存 | Redis 7 | 会话和热数据 |
| 对象存储 | MinIO | Artifacts存储 |
| 搜索引擎 | Elasticsearch 8 | 全文搜索 |
| 消息队列 | RabbitMQ | 异步任务 |
| 容器化 | Docker + K8s | 部署和编排 |

---

## 前端架构

### 1. 项目结构

```
frontend/
├── public/                  # 静态资源
├── src/
│   ├── assets/             # 图片、字体等
│   ├── components/         # 可复用组件
│   │   ├── common/        # 通用组件
│   │   ├── charts/        # 图表组件
│   │   ├── layout/        # 布局组件
│   │   └── forms/         # 表单组件
│   ├── features/          # 功能模块
│   │   ├── auth/          # 认证
│   │   ├── runs/          # 实验运行
│   │   ├── artifacts/     # Artifacts
│   │   ├── sweeps/        # 超参数优化
│   │   ├── reports/       # 报告
│   │   └── registry/      # 模型注册
│   ├── pages/             # 页面组件
│   ├── hooks/             # 自定义Hooks
│   ├── services/          # API服务
│   ├── store/             # Redux store
│   ├── utils/             # 工具函数
│   ├── types/             # TypeScript类型
│   ├── App.tsx
│   └── main.tsx
├── tests/                 # 测试文件
├── package.json
└── vite.config.ts
```

### 2. 核心技术选型详解

#### 2.1 React 18 关键特性
- **并发渲染**: 提升大数据列表渲染性能
- **Suspense**: 优雅的加载状态处理
- **Automatic Batching**: 减少重渲染次数
- **Transitions**: 区分紧急和非紧急更新

#### 2.2 状态管理架构
```typescript
// Redux Store结构
{
  auth: {
    user: User | null,
    token: string | null,
    loading: boolean
  },
  projects: {
    items: Project[],
    selected: Project | null,
    loading: boolean
  },
  runs: {
    items: Run[],
    selected: Run[],
    filters: FilterState,
    pagination: PaginationState
  },
  metrics: {
    data: MetricData,
    loading: boolean,
    realtime: boolean
  },
  ui: {
    sidebarCollapsed: boolean,
    theme: 'light' | 'dark',
    workspaceLayout: Layout[]
  }
}
```

#### 2.3 路由设计
```typescript
// 路由结构
/                           # 首页/仪表板
/login                      # 登录
/register                   # 注册
/projects                   # 项目列表
/projects/:id               # 项目详情
/projects/:id/runs          # 运行列表
/runs/:id                   # 运行详情
/runs/:id/workspace         # 工作区
/runs/:id/overview          # 概览
/runs/:id/files             # 文件
/runs/:id/logs              # 日志
/artifacts                  # Artifacts浏览器
/artifacts/:id              # Artifact详情
/sweeps/:id                 # Sweep详情
/registry                   # 模型注册表
/registry/:model/:version   # 模型版本详情
/reports                    # 报告列表
/reports/:id                # 报告详情
/settings                   # 设置
```

### 3. 关键组件设计

#### 3.1 图表系统
```typescript
// 图表组件架构
interface ChartProps {
  data: MetricData;
  config: ChartConfig;
  realtime?: boolean;
  interactive?: boolean;
}

// 支持的图表类型
- LineChart: 折线图（多系列）
- ScatterChart: 散点图
- BarChart: 柱状图
- HistogramChart: 直方图
- HeatmapChart: 热力图
- ParallelCoordinatesChart: 平行坐标图
- CustomChart: 自定义图表
```

#### 3.2 工作区系统
```typescript
// 工作区布局
interface WorkspaceLayout {
  panels: Panel[];
  layout: GridLayout;
  filters: Filter[];
}

interface Panel {
  id: string;
  type: 'chart' | 'table' | 'media' | 'custom';
  config: PanelConfig;
  position: GridPosition;
}
```

#### 3.3 实时数据更新
```typescript
// WebSocket连接管理
class MetricsStreamManager {
  private socket: WebSocket;
  private subscribers: Map<string, Callback>;

  subscribe(runId: string, callback: Callback): void;
  unsubscribe(runId: string): void;
  reconnect(): void;
}
```

### 4. 性能优化策略

#### 4.1 代码分割
```typescript
// 路由级代码分割
const RunDetail = lazy(() => import('./pages/RunDetail'));
const Artifacts = lazy(() => import('./pages/Artifacts'));
const Sweeps = lazy(() => import('./pages/Sweeps'));
```

#### 4.2 虚拟化列表
```typescript
// 使用react-window处理大列表
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={800}
  itemCount={runs.length}
  itemSize={50}
>
  {RunRow}
</FixedSizeList>
```

#### 4.3 数据缓存
```typescript
// React Query缓存配置
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5分钟
      cacheTime: 10 * 60 * 1000, // 10分钟
      refetchOnWindowFocus: false,
    }
  }
});
```

---

## 后端架构

### 1. 微服务划分

```
services/
├── api-gateway/           # API网关 (Go)
├── auth-service/          # 认证服务 (Python/FastAPI)
├── run-service/           # Run管理服务 (Python/FastAPI)
├── metric-service/        # 指标服务 (Go)
├── artifact-service/      # Artifact服务 (Python/FastAPI)
├── sweep-service/         # Sweep服务 (Python/FastAPI)
├── registry-service/      # Registry服务 (Python/FastAPI)
├── report-service/        # 报告服务 (Python/FastAPI)
├── notification-service/  # 通知服务 (Go)
└── storage-service/       # 存储服务 (Go)
```

### 2. 服务职责

#### 2.1 API Gateway (Go/Gin)
- 路由转发
- 负载均衡
- 认证验证
- 限流控制
- 请求日志
- 响应缓存

#### 2.2 Run Service (Python/FastAPI)
```python
# 核心API
POST   /runs                  # 创建Run
GET    /runs/:id              # 获取Run详情
PATCH  /runs/:id              # 更新Run
DELETE /runs/:id              # 删除Run
POST   /runs/:id/finish       # 结束Run
POST   /runs/:id/config       # 更新配置
POST   /runs/:id/tags         # 添加标签
```

#### 2.3 Metric Service (Go)
```go
// 高性能指标写入
POST   /metrics/batch         // 批量写入
GET    /metrics/query         // 查询指标
GET    /metrics/stream        // 实时订阅 (WebSocket)
GET    /metrics/aggregate     // 聚合查询
```

#### 2.4 Artifact Service (Python/FastAPI)
```python
POST   /artifacts              # 创建Artifact
POST   /artifacts/:id/files   # 上传文件
GET    /artifacts/:id/download # 下载Artifact
GET    /artifacts/:id/manifest # 获取清单
POST   /artifacts/:id/commit   # 提交版本
```

### 3. 核心服务实现

#### 3.1 Run Service架构
```python
# services/run_service/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── runs.py        # Run API
│   │   │   ├── configs.py     # 配置API
│   │   │   └── tags.py        # 标签API
│   ├── core/
│   │   ├── config.py          # 配置
│   │   ├── security.py        # 安全
│   │   └── dependencies.py    # 依赖注入
│   ├── models/
│   │   ├── run.py
│   │   ├── config.py
│   │   └── tag.py
│   ├── schemas/
│   │   ├── run.py
│   │   ├── config.py
│   │   └── tag.py
│   ├── services/
│   │   ├── run_service.py
│   │   └── git_service.py
│   ├── repositories/
│   │   └── run_repository.py
│   └── main.py
├── tests/
├── requirements.txt
└── Dockerfile
```

#### 3.2 数据访问层
```python
# Repository模式
class RunRepository:
    def __init__(self, db: Session):
        self.db = db

    async def create(self, run: RunCreate) -> Run:
        pass

    async def get(self, run_id: str) -> Optional[Run]:
        pass

    async def update(self, run_id: str, update: RunUpdate) -> Run:
        pass

    async def list(self, filters: RunFilters) -> List[Run]:
        pass

    async def delete(self, run_id: str) -> bool:
        pass
```

#### 3.3 服务层
```python
# Business Logic
class RunService:
    def __init__(
        self,
        run_repo: RunRepository,
        metric_client: MetricClient,
        event_bus: EventBus
    ):
        self.run_repo = run_repo
        self.metric_client = metric_client
        self.event_bus = event_bus

    async def create_run(self, run_data: RunCreate) -> Run:
        # 业务逻辑
        run = await self.run_repo.create(run_data)
        await self.event_bus.publish('run.created', run)
        return run

    async def finish_run(self, run_id: str) -> Run:
        run = await self.run_repo.get(run_id)
        run.state = RunState.FINISHED
        run.finished_at = datetime.utcnow()
        await self.run_repo.update(run_id, run)
        await self.event_bus.publish('run.finished', run)
        return run
```

### 4. 异步任务处理

#### 4.1 Celery任务
```python
# tasks/metric_aggregation.py
from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379/0')

@app.task
def aggregate_metrics(run_id: str):
    """聚合运行指标"""
    pass

@app.task
def cleanup_old_runs(days: int = 30):
    """清理旧运行数据"""
    pass

@app.task
def generate_report(report_id: str):
    """生成报告"""
    pass
```

### 5. 事件驱动架构

#### 5.1 事件定义
```python
# events/run_events.py
class RunCreatedEvent(Event):
    run_id: str
    project_id: str
    user_id: str

class RunFinishedEvent(Event):
    run_id: str
    duration: timedelta
    final_metrics: Dict[str, float]

class MetricLoggedEvent(Event):
    run_id: str
    metric_name: str
    value: float
    step: int
```

#### 5.2 事件处理器
```python
# handlers/notification_handler.py
class NotificationHandler:
    async def handle_run_finished(self, event: RunFinishedEvent):
        # 发送通知
        await notification_service.send(
            user_id=event.user_id,
            title=f"Run {event.run_id} finished",
            body=f"Duration: {event.duration}"
        )
```

---

## 数据库设计

### 1. PostgreSQL主数据库

#### 1.1 核心表结构

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 组织表
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 团队表
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(organization_id, name)
);

-- 成员关系表
CREATE TABLE memberships (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'member', 'viewer')),
    joined_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, team_id)
);

-- 项目表
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    description TEXT,
    visibility VARCHAR(20) DEFAULT 'private' CHECK (visibility IN ('public', 'private')),
    settings JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(organization_id, slug)
);

-- Run表
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    state VARCHAR(50) DEFAULT 'running' CHECK (state IN ('running', 'finished', 'crashed', 'killed')),

    -- Git信息
    git_commit VARCHAR(40),
    git_remote TEXT,
    git_branch VARCHAR(255),

    -- 环境信息
    host VARCHAR(255),
    os VARCHAR(100),
    python_version VARCHAR(50),

    -- 时间信息
    started_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP,
    heartbeat_at TIMESTAMP DEFAULT NOW(),

    -- 其他元数据
    notes TEXT,
    tags JSONB DEFAULT '[]',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_runs_project_id ON runs(project_id);
CREATE INDEX idx_runs_user_id ON runs(user_id);
CREATE INDEX idx_runs_state ON runs(state);
CREATE INDEX idx_runs_started_at ON runs(started_at DESC);

-- 配置表
CREATE TABLE run_configs (
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    PRIMARY KEY (run_id, key)
);

-- 汇总表（冗余存储，优化查询）
CREATE TABLE run_summaries (
    run_id UUID PRIMARY KEY REFERENCES runs(id) ON DELETE CASCADE,
    metrics JSONB DEFAULT '{}',  -- 最终指标值
    system_metrics JSONB DEFAULT '{}',  -- 系统指标统计
    duration INTERVAL,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Artifacts表
CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,  -- dataset, model, result, etc.
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, name)
);

-- Artifact版本表
CREATE TABLE artifact_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID REFERENCES artifacts(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,
    aliases JSONB DEFAULT '[]',  -- ["latest", "v1.0"]
    digest VARCHAR(64) NOT NULL,  -- 内容哈希
    size BIGINT,
    metadata JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(artifact_id, version)
);

-- Artifact文件表
CREATE TABLE artifact_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID REFERENCES artifact_versions(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    size BIGINT NOT NULL,
    digest VARCHAR(64) NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Artifact依赖关系
CREATE TABLE artifact_dependencies (
    source_version_id UUID REFERENCES artifact_versions(id) ON DELETE CASCADE,
    target_version_id UUID REFERENCES artifact_versions(id) ON DELETE CASCADE,
    run_id UUID REFERENCES runs(id),
    dependency_type VARCHAR(50) DEFAULT 'uses',  -- uses, produces
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (source_version_id, target_version_id)
);

-- Sweeps表
CREATE TABLE sweeps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255),
    config JSONB NOT NULL,  -- 搜索配置
    state VARCHAR(50) DEFAULT 'running',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Sweep与Run关联表
CREATE TABLE sweep_runs (
    sweep_id UUID REFERENCES sweeps(id) ON DELETE CASCADE,
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    PRIMARY KEY (sweep_id, run_id)
);

-- 模型注册表
CREATE TABLE registered_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tags JSONB DEFAULT '[]',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, name)
);

-- 模型版本表
CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID REFERENCES registered_models(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,
    artifact_version_id UUID REFERENCES artifact_versions(id),
    run_id UUID REFERENCES runs(id),
    stage VARCHAR(50) DEFAULT 'none' CHECK (stage IN ('none', 'staging', 'production', 'archived')),
    description TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(model_id, version)
);

-- 报告表
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content JSONB NOT NULL,  -- 报告内容（富文本+组件）
    visibility VARCHAR(20) DEFAULT 'private',
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 报告协作者表
CREATE TABLE report_collaborators (
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    permission VARCHAR(20) CHECK (permission IN ('view', 'edit')),
    PRIMARY KEY (report_id, user_id)
);
```

### 2. TimescaleDB时序数据库

```sql
-- 指标数据表（超表）
CREATE TABLE metrics (
    time TIMESTAMPTZ NOT NULL,
    run_id UUID NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    step INTEGER,
    value DOUBLE PRECISION,
    metadata JSONB
);

-- 创建超表
SELECT create_hypertable('metrics', 'time');

-- 创建索引
CREATE INDEX idx_metrics_run_id ON metrics(run_id, time DESC);
CREATE INDEX idx_metrics_name ON metrics(run_id, metric_name, time DESC);

-- 系统指标表
CREATE TABLE system_metrics (
    time TIMESTAMPTZ NOT NULL,
    run_id UUID NOT NULL,
    cpu_percent DOUBLE PRECISION,
    memory_percent DOUBLE PRECISION,
    gpu_utilization JSONB,  -- 支持多GPU
    disk_io JSONB,
    network_io JSONB
);

SELECT create_hypertable('system_metrics', 'time');
CREATE INDEX idx_system_metrics_run_id ON system_metrics(run_id, time DESC);

-- 数据保留策略（自动清理旧数据）
SELECT add_retention_policy('metrics', INTERVAL '90 days');
SELECT add_retention_policy('system_metrics', INTERVAL '30 days');

-- 连续聚合（加速查询）
CREATE MATERIALIZED VIEW metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    run_id,
    metric_name,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    COUNT(*) as count
FROM metrics
GROUP BY bucket, run_id, metric_name;
```

### 3. Redis缓存设计

```
# Key命名规范
session:{user_id}                    # 用户会话
run:{run_id}:config                  # Run配置缓存
run:{run_id}:summary                 # Run摘要缓存
project:{project_id}:runs            # 项目Run列表缓存
user:{user_id}:projects              # 用户项目列表
metrics:{run_id}:latest              # 最新指标值
sweep:{sweep_id}:state               # Sweep状态
```

---

## API设计

### 1. API版本控制
- URL路径版本: `/api/v1/`, `/api/v2/`
- 向后兼容至少2个版本
- 废弃警告：响应头 `X-API-Deprecation-Warning`

### 2. 统一响应格式

```json
// 成功响应
{
  "data": { ... },
  "meta": {
    "timestamp": "2025-01-01T00:00:00Z",
    "version": "v1"
  }
}

// 分页响应
{
  "data": [ ... ],
  "meta": {
    "total": 100,
    "page": 1,
    "pageSize": 20,
    "totalPages": 5
  },
  "links": {
    "first": "/api/v1/runs?page=1",
    "prev": null,
    "next": "/api/v1/runs?page=2",
    "last": "/api/v1/runs?page=5"
  }
}

// 错误响应
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  },
  "meta": {
    "timestamp": "2025-01-01T00:00:00Z",
    "requestId": "abc-123-def"
  }
}
```

### 3. 核心API详细设计

#### 3.1 Run API

```yaml
# 创建Run
POST /api/v1/projects/{projectId}/runs
Request:
  {
    "name": "experiment-1",
    "config": {
      "learning_rate": 0.001,
      "batch_size": 32
    },
    "tags": ["baseline", "v1"],
    "notes": "Initial experiment"
  }
Response: 201
  {
    "data": {
      "id": "uuid",
      "name": "experiment-1",
      "state": "running",
      "url": "/runs/uuid",
      "config": { ... },
      "createdAt": "..."
    }
  }

# 记录指标
POST /api/v1/runs/{runId}/metrics
Request:
  {
    "metrics": [
      {"name": "loss", "step": 1, "value": 0.5},
      {"name": "accuracy", "step": 1, "value": 0.85}
    ]
  }
Response: 200

# 批量记录指标（优化）
POST /api/v1/metrics/batch
Request:
  {
    "runId": "uuid",
    "metrics": {
      "loss": [
        {"step": 1, "value": 0.5},
        {"step": 2, "value": 0.4}
      ],
      "accuracy": [
        {"step": 1, "value": 0.85},
        {"step": 2, "value": 0.87}
      ]
    }
  }

# 查询指标
GET /api/v1/runs/{runId}/metrics?names=loss,accuracy&minStep=0&maxStep=100
Response:
  {
    "data": {
      "loss": [
        {"step": 1, "value": 0.5, "timestamp": "..."},
        ...
      ],
      "accuracy": [ ... ]
    }
  }

# 完成Run
POST /api/v1/runs/{runId}/finish
Request:
  {
    "exitCode": 0,
    "summary": {
      "best_loss": 0.1,
      "best_accuracy": 0.95
    }
  }
```

#### 3.2 Artifact API

```yaml
# 创建Artifact
POST /api/v1/projects/{projectId}/artifacts
Request:
  {
    "name": "mnist-dataset",
    "type": "dataset",
    "description": "MNIST training dataset"
  }
Response: 201

# 添加文件到Artifact
POST /api/v1/artifacts/{artifactId}/files
Request: multipart/form-data
  - file: binary
  - path: "train/images/001.png"

# 提交版本
POST /api/v1/artifacts/{artifactId}/commit
Request:
  {
    "aliases": ["latest", "v1.0"]
  }
Response:
  {
    "data": {
      "version": "v0",
      "digest": "sha256:...",
      "size": 1024000
    }
  }

# 下载Artifact
GET /api/v1/artifacts/{artifactId}/versions/{version}/download
Response: 302 Redirect to presigned URL
```

#### 3.3 Sweep API

```yaml
# 创建Sweep
POST /api/v1/projects/{projectId}/sweeps
Request:
  {
    "name": "hyperparameter-search",
    "method": "bayes",
    "metric": {
      "name": "accuracy",
      "goal": "maximize"
    },
    "parameters": {
      "learning_rate": {
        "distribution": "log_uniform",
        "min": 0.0001,
        "max": 0.1
      },
      "batch_size": {
        "values": [16, 32, 64, 128]
      }
    },
    "early_terminate": {
      "type": "hyperband",
      "min_iter": 3
    }
  }

# 获取下一组参数（Agent调用）
POST /api/v1/sweeps/{sweepId}/next
Response:
  {
    "data": {
      "runConfig": {
        "learning_rate": 0.005,
        "batch_size": 32
      }
    }
  }

# 报告结果
POST /api/v1/sweeps/{sweepId}/report
Request:
  {
    "runId": "uuid",
    "metrics": {
      "accuracy": 0.92
    }
  }
```

### 4. WebSocket API

```typescript
// 实时指标订阅
ws://api.example.com/ws/metrics

// 客户端消息
{
  "type": "subscribe",
  "runIds": ["uuid1", "uuid2"]
}

// 服务端推送
{
  "type": "metric_update",
  "runId": "uuid1",
  "metrics": {
    "loss": {"step": 10, "value": 0.3}
  },
  "timestamp": "..."
}
```

---

## 安全设计

### 1. 认证与授权

#### 1.1 JWT认证
```python
# Token结构
{
  "sub": "user_id",
  "exp": 1234567890,
  "iat": 1234567890,
  "scopes": ["read:runs", "write:runs"],
  "org_id": "org_uuid"
}
```

#### 1.2 权限模型(RBAC)
```yaml
Roles:
  - admin:
      - *:*  # 所有权限
  - member:
      - read:*
      - write:runs
      - write:artifacts
  - viewer:
      - read:*
```

### 2. 数据安全
- 密码：bcrypt哈希 + salt
- 敏感数据：AES-256加密
- API密钥：单向哈希存储
- 传输：强制HTTPS (TLS 1.3)

### 3. API安全
- 限流：用户级 + IP级
- CORS配置
- CSRF保护
- SQL注入防护（参数化查询）
- XSS防护（内容安全策略）

---

## 性能优化

### 1. 数据库优化
- 连接池：最小10，最大100
- 索引优化：覆盖索引、复合索引
- 分区表：按时间分区指标数据
- 读写分离：主从复制

### 2. 缓存策略
```python
# 多级缓存
L1: 本地内存缓存 (LRU, 10MB)
L2: Redis缓存 (热数据, 1GB)
L3: 数据库

# 缓存失效策略
- TTL: 根据数据类型设置
- 主动失效：数据更新时清除
- 懒加载：首次访问时缓存
```

### 3. 批量处理
- 指标批量写入：每100条或5秒
- 批量查询：单次最多1000条
- 数据预聚合：定时任务

### 4. CDN加速
- 静态资源：前端资源、图片
- Artifact下载：大文件分发

---

## 部署架构

### 1. Kubernetes部署

```yaml
# 服务部署清单
deployments:
  - api-gateway: 3 replicas
  - run-service: 5 replicas
  - metric-service: 10 replicas  # 高负载
  - artifact-service: 3 replicas
  - frontend: 3 replicas

# 资源配额
resources:
  api-gateway:
    requests: { cpu: 500m, memory: 512Mi }
    limits: { cpu: 1000m, memory: 1Gi }
  metric-service:
    requests: { cpu: 1000m, memory: 2Gi }
    limits: { cpu: 2000m, memory: 4Gi }
```

### 2. 自动扩缩容

```yaml
# HPA配置
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: metric-service
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: metric-service
  minReplicas: 5
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### 3. 监控与告警

```yaml
# Prometheus监控指标
- http_request_duration_seconds
- http_requests_total
- database_connections_active
- cache_hit_rate
- metric_write_latency
- artifact_upload_size

# 告警规则
- API响应时间 > 1s
- 错误率 > 5%
- CPU使用率 > 80%
- 内存使用率 > 85%
- 数据库连接数 > 90%
```

---

## 总结

本技术架构设计文档详细规划了wanLLMDB项目的：
- 前后端技术选型与架构
- 数据库设计与优化
- API接口设计规范
- 安全与性能策略
- 部署与运维方案

该架构支持：
✅ 高并发（支持1000+ 并发用户）
✅ 高可用（99.9% SLA）
✅ 可扩展（水平扩展）
✅ 高性能（API P95 < 200ms）
✅ 安全可靠（企业级安全标准）
