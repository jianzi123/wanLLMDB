# wanLLMDB 架构设计文档

完整的系统架构、组件关系和技术栈说明。

**版本**: 1.0
**更新日期**: 2025-11-16

---

## 📋 目录

- [系统概述](#系统概述)
- [技术栈](#技术栈)
- [项目组件](#项目组件)
- [目录结构](#目录结构)
- [API 路由映射](#api-路由映射)
- [组件交互](#组件交互)
- [数据流](#数据流)
- [安全架构](#安全架构)
- [扩展性设计](#扩展性设计)

---

## 系统概述

wanLLMDB 是一个**机器学习实验管理平台**，提供实验跟踪、模型版本管理、超参数优化等功能，类似于 Weights & Biases (W&B) 和 MLflow。

### 核心功能

```
wanLLMDB = MLflow + Weights & Biases + DVC (精简版)
```

- **实验管理**: 项目、运行、日志、文件跟踪
- **模型治理**: 模型注册、版本管理、阶段流转
- **超参数优化**: Sweep（网格搜索、贝叶斯优化、随机搜索）
- **Artifact 管理**: 版本控制、别名系统、血缘追踪
- **安全审计**: 完整的操作审计日志

---

## 技术栈

### 后端 (Backend)

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 主要编程语言 |
| **FastAPI** | 0.104+ | Web 框架 |
| **SQLAlchemy** | 2.0+ | ORM 框架 |
| **Pydantic** | 2.0+ | 数据验证 |
| **Alembic** | 1.12+ | 数据库迁移 |
| **Poetry** | 1.6+ | 依赖管理 |
| **Uvicorn** | 0.24+ | ASGI 服务器 |
| **Passlib** | 1.7+ | 密码加密 |
| **Python-Jose** | 3.3+ | JWT 处理 |

### 前端 (Frontend)

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18+ | UI 框架 |
| **Next.js** | 13+ | React 框架 |
| **TypeScript** | 5+ | 类型系统 |
| **Tailwind CSS** | 3+ | 样式框架 |
| **Axios** | 1.6+ | HTTP 客户端 |

### 数据库

| 技术 | 版本 | 用途 |
|------|------|------|
| **PostgreSQL** | 15+ | 主数据库 |
| **TimescaleDB** | 2.11+ | 时序数据（可选） |
| **Redis** | 7+ | 缓存、JWT 黑名单 |

### 存储

| 技术 | 版本 | 用途 |
|------|------|------|
| **MinIO** | Latest | S3 兼容对象存储 |

### 基础设施

| 技术 | 版本 | 用途 |
|------|------|------|
| **Docker** | 20.10+ | 容器化 |
| **Docker Compose** | 2.0+ | 本地编排 |
| **Kubernetes** | 1.24+ | 生产编排 |
| **Nginx Ingress** | Latest | 流量入口 |

---

## 项目组件

wanLLMDB 采用**微服务架构**，由以下核心组件组成：

### 1. Frontend（前端服务）

**职责**:
- 提供 Web 用户界面
- 用户交互和数据可视化
- 与后端 API 通信

**技术**: React + Next.js + TypeScript
**端口**: 3000
**路径**: `/home/user/wanLLMDB/frontend/`

**关键模块**:
```
frontend/
├── src/
│   ├── pages/              # 页面路由
│   │   ├── index.tsx       # 首页
│   │   ├── projects/       # 项目管理
│   │   ├── runs/           # 运行记录
│   │   ├── models/         # 模型注册表
│   │   └── sweeps/         # 超参数优化
│   ├── components/         # React 组件
│   ├── hooks/              # 自定义 Hooks
│   ├── lib/                # 工具函数
│   └── styles/             # 样式文件
```

---

### 2. Backend（后端服务）

**职责**:
- RESTful API 服务
- 业务逻辑处理
- 数据持久化
- 认证和授权

**技术**: FastAPI + SQLAlchemy
**端口**: 8000
**路径**: `/home/user/wanLLMDB/backend/`

**关键模块**:
```
backend/
├── app/
│   ├── api/                # API 路由
│   │   ├── v1/             # API v1 版本
│   │   │   ├── auth.py            # 认证 /api/v1/auth
│   │   │   ├── projects.py        # 项目 /api/v1/projects
│   │   │   ├── runs.py            # 运行 /api/v1/runs
│   │   │   ├── artifacts.py       # Artifact /api/v1/artifacts
│   │   │   ├── sweeps.py          # Sweep /api/v1/sweeps
│   │   │   ├── run_files.py       # 文件 /api/v1/runs/{id}/files
│   │   │   ├── run_logs.py        # 日志 /api/v1/runs/{id}/logs
│   │   │   ├── model_registry.py  # 模型 /api/v1/registry/models
│   │   │   └── audit.py           # 审计 /api/v1/audit
│   │   └── monitoring.py          # 监控 /health, /metrics
│   ├── core/               # 核心功能
│   │   ├── config.py       # 配置管理
│   │   ├── security.py     # JWT、密码加密
│   │   ├── audit.py        # 审计日志
│   │   └── security_utils.py  # 安全工具
│   ├── db/                 # 数据库
│   │   └── database.py     # 数据库连接
│   ├── models/             # ORM 模型
│   │   ├── user.py         # 用户
│   │   ├── project.py      # 项目
│   │   ├── run.py          # 运行
│   │   ├── artifact.py     # Artifact
│   │   ├── sweep.py        # Sweep
│   │   ├── model_registry.py  # 模型注册
│   │   └── audit_log.py    # 审计日志
│   ├── schemas/            # Pydantic 模式
│   ├── services/           # 业务逻辑
│   │   └── storage_service.py  # MinIO 存储
│   └── repositories/       # 数据访问层
│       ├── project_repository.py
│       ├── artifact_repository.py
│       └── model_registry_repository.py
```

---

### 3. PostgreSQL（主数据库）

**职责**:
- 存储结构化数据
- 事务管理
- 数据一致性

**技术**: PostgreSQL 15
**端口**: 5432
**存储**: PersistentVolume (10-100GB)

**数据表**:
```
users              # 用户表
projects           # 项目表
runs               # 运行记录
run_metrics        # 运行指标（时序）
run_logs           # 运行日志
run_files          # 运行文件元数据
artifacts          # Artifact 元数据
artifact_versions  # Artifact 版本
artifact_aliases   # Artifact 别名 (新增)
sweeps             # Sweep 配置
model_registry     # 模型注册表
model_versions     # 模型版本
audit_logs         # 审计日志
```

---

### 4. Redis（缓存服务）

**职责**:
- 会话缓存
- JWT Token 黑名单
- 临时数据存储
- 速率限制

**技术**: Redis 7
**端口**: 6379
**存储**: PersistentVolume (5-10GB)

**数据结构**:
```
jwt_blacklist:<token>    # JWT 黑名单 (TTL: token 过期时间)
session:<user_id>        # 用户会话
rate_limit:<ip>          # IP 速率限制
cache:*                  # 通用缓存
```

---

### 5. MinIO（对象存储）

**职责**:
- 存储 Artifact 文件
- 存储运行文件
- 存储模型文件
- S3 兼容 API

**技术**: MinIO (S3-compatible)
**端口**: 9000 (API), 9001 (Console)
**存储**: PersistentVolume (50-500GB)

**存储桶结构**:
```
wanllmdb-artifacts/
├── projects/<project_id>/
│   ├── runs/<run_id>/
│   │   ├── files/               # 运行文件
│   │   └── artifacts/           # 运行 Artifact
│   └── artifacts/<artifact_name>/<version>/  # 项目 Artifact
└── models/<model_name>/<version>/  # 模型文件
```

---

### 6. SDK（Python 客户端）

**职责**:
- 提供 Python API
- 简化实验跟踪
- 集成到训练脚本

**路径**: `/home/user/wanLLMDB/sdk/`

**使用示例**:
```python
import wanllmdb

# 初始化项目
project = wanllmdb.init(project="my-project", name="experiment-1")

# 记录参数
project.log_params({"lr": 0.001, "epochs": 10})

# 记录指标
project.log_metrics({"accuracy": 0.95}, step=10)

# 保存 Artifact
project.log_artifact("/path/to/model.pkl", name="model", type="model")
```

---

## 目录结构

### 根目录

```
wanLLMDB/
├── backend/                    # 后端服务
│   ├── app/                    # 应用代码
│   ├── alembic/                # 数据库迁移
│   ├── tests/                  # 测试代码
│   ├── scripts/                # 运维脚本
│   ├── pyproject.toml          # Poetry 配置
│   ├── Dockerfile              # Docker 镜像
│   └── .env.example            # 环境变量模板
├── frontend/                   # 前端服务
│   ├── src/                    # 源代码
│   ├── public/                 # 静态资源
│   ├── package.json            # NPM 配置
│   ├── Dockerfile              # Docker 镜像
│   └── .env.example            # 环境变量模板
├── sdk/                        # Python SDK
│   ├── wanllmdb/               # SDK 代码
│   ├── examples/               # 使用示例
│   └── pyproject.toml          # Poetry 配置
├── k8s/                        # Kubernetes 配置
│   ├── base/                   # 基础配置
│   ├── overlays/               # 环境覆盖
│   │   ├── development/        # 开发环境
│   │   └── production/         # 生产环境
│   └── scripts/                # 部署脚本
├── docs/                       # 文档
│   ├── architecture/           # 架构文档
│   └── api/                    # API 文档
├── docker-compose.yml          # Docker Compose 配置
├── .env.example                # 环境变量模板
├── .env.production.example     # 生产环境模板
├── ARCHITECTURE.md             # 本文档
├── OPERATIONS.md               # 运维指南
├── GETTING_STARTED.md          # 快速开始
├── PRODUCT_FEATURES.md         # 产品功能
└── README.md                   # 项目说明
```

---

## API 路由映射

### 路径与服务对应关系

| URL 路径 | 后端模块 | 功能描述 | 代码位置 |
|----------|----------|----------|----------|
| **认证与用户** |
| `POST /api/v1/auth/register` | `auth.py` | 用户注册 | `backend/app/api/v1/auth.py:register()` |
| `POST /api/v1/auth/login` | `auth.py` | 用户登录 | `backend/app/api/v1/auth.py:login()` |
| `POST /api/v1/auth/logout` | `auth.py` | 用户登出 | `backend/app/api/v1/auth.py:logout()` |
| `POST /api/v1/auth/refresh` | `auth.py` | 刷新 Token | `backend/app/api/v1/auth.py:refresh_token()` |
| `GET /api/v1/auth/me` | `auth.py` | 获取当前用户 | `backend/app/api/v1/auth.py:get_current_user_info()` |
| **项目管理** |
| `POST /api/v1/projects` | `projects.py` | 创建项目 | `backend/app/api/v1/projects.py:create_project()` |
| `GET /api/v1/projects` | `projects.py` | 获取项目列表 | `backend/app/api/v1/projects.py:list_projects()` |
| `GET /api/v1/projects/{id}` | `projects.py` | 获取项目详情 | `backend/app/api/v1/projects.py:get_project()` |
| `PUT /api/v1/projects/{id}` | `projects.py` | 更新项目 | `backend/app/api/v1/projects.py:update_project()` |
| `DELETE /api/v1/projects/{id}` | `projects.py` | 删除项目 | `backend/app/api/v1/projects.py:delete_project()` |
| **运行管理** |
| `POST /api/v1/runs` | `runs.py` | 创建运行 | `backend/app/api/v1/runs.py:create_run()` |
| `GET /api/v1/runs` | `runs.py` | 获取运行列表 | `backend/app/api/v1/runs.py:list_runs()` |
| `GET /api/v1/runs/{id}` | `runs.py` | 获取运行详情 | `backend/app/api/v1/runs.py:get_run()` |
| `PATCH /api/v1/runs/{id}` | `runs.py` | 更新运行 | `backend/app/api/v1/runs.py:update_run()` |
| `POST /api/v1/runs/{id}/logs` | `run_logs.py` | 添加日志 | `backend/app/api/v1/run_logs.py:add_log()` |
| `GET /api/v1/runs/{id}/logs` | `run_logs.py` | 获取日志 | `backend/app/api/v1/run_logs.py:get_logs()` |
| `POST /api/v1/runs/{id}/files` | `run_files.py` | 上传文件 | `backend/app/api/v1/run_files.py:upload_file()` |
| `GET /api/v1/runs/{id}/files` | `run_files.py` | 获取文件列表 | `backend/app/api/v1/run_files.py:list_files()` |
| **Artifact 管理** |
| `POST /api/v1/artifacts` | `artifacts.py` | 创建 Artifact | `backend/app/api/v1/artifacts.py:create_artifact()` |
| `GET /api/v1/artifacts` | `artifacts.py` | 获取 Artifact 列表 | `backend/app/api/v1/artifacts.py:list_artifacts()` |
| `GET /api/v1/artifacts/{id}` | `artifacts.py` | 获取 Artifact 详情 | `backend/app/api/v1/artifacts.py:get_artifact()` |
| `POST /api/v1/artifacts/{id}/versions` | `artifacts.py` | 创建新版本 | `backend/app/api/v1/artifacts.py:create_version()` |
| `POST /api/v1/artifacts/{id}/aliases` | `artifacts.py` | 设置别名 | `backend/app/api/v1/artifacts.py:set_alias()` |
| `POST /api/v1/artifacts/{id}/download` | `artifacts.py` | 下载 Artifact | `backend/app/api/v1/artifacts.py:download()` |
| **Sweep (超参数优化)** |
| `POST /api/v1/sweeps` | `sweeps.py` | 创建 Sweep | `backend/app/api/v1/sweeps.py:create_sweep()` |
| `GET /api/v1/sweeps/{id}` | `sweeps.py` | 获取 Sweep 详情 | `backend/app/api/v1/sweeps.py:get_sweep()` |
| `POST /api/v1/sweeps/{id}/runs` | `sweeps.py` | 添加 Sweep 运行 | `backend/app/api/v1/sweeps.py:add_run()` |
| **模型注册表** |
| `POST /api/v1/registry/models` | `model_registry.py` | 注册模型 | `backend/app/api/v1/model_registry.py:register_model()` |
| `GET /api/v1/registry/models` | `model_registry.py` | 获取模型列表 | `backend/app/api/v1/model_registry.py:list_models()` |
| `GET /api/v1/registry/models/{name}` | `model_registry.py` | 获取模型详情 | `backend/app/api/v1/model_registry.py:get_model()` |
| `POST /api/v1/registry/models/{name}/versions` | `model_registry.py` | 创建模型版本 | `backend/app/api/v1/model_registry.py:create_version()` |
| `PATCH /api/v1/registry/models/{name}/versions/{version}` | `model_registry.py` | 更新版本阶段 | `backend/app/api/v1/model_registry.py:update_stage()` |
| **审计日志 (仅管理员)** |
| `GET /api/v1/audit/logs` | `audit.py` | 获取审计日志 | `backend/app/api/v1/audit.py:get_audit_logs()` |
| `GET /api/v1/audit/logs/{id}` | `audit.py` | 获取日志详情 | `backend/app/api/v1/audit.py:get_audit_log()` |
| `GET /api/v1/audit/stats/summary` | `audit.py` | 获取统计摘要 | `backend/app/api/v1/audit.py:get_audit_stats()` |
| **健康检查与监控** |
| `GET /health` | `monitoring.py` | 基本健康检查 | `backend/app/api/monitoring.py:basic_health_check()` |
| `GET /health/ready` | `monitoring.py` | 就绪检查 | `backend/app/api/monitoring.py:readiness_check()` |
| `GET /health/live` | `monitoring.py` | 存活检查 | `backend/app/api/monitoring.py:liveness_check()` |
| `GET /metrics` | `monitoring.py` | 系统指标 | `backend/app/api/monitoring.py:get_metrics()` |
| `GET /info` | `monitoring.py` | 应用信息 | `backend/app/api/monitoring.py:get_info()` |

### API 版本控制

- **当前版本**: v1
- **Base Path**: `/api/v1`
- **未来版本**: `/api/v2` (向后兼容)

---

## 组件交互

### 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    浏览器/客户端                          │
└────────────┬──────────────────────────┬─────────────────┘
             │                          │
             │ HTTP/HTTPS               │ SDK API
             │                          │
┌────────────▼──────────┐     ┌─────────▼──────────┐
│    Frontend (React)   │     │   Python SDK       │
│    Port: 3000         │     │   (wanllmdb)       │
└────────────┬──────────┘     └─────────┬──────────┘
             │                          │
             │ REST API                 │
             └──────────┬───────────────┘
                        │
             ┌──────────▼──────────┐
             │  Backend (FastAPI)  │
             │  Port: 8000         │
             └──────────┬──────────┘
                        │
        ┌───────────────┼───────────────┬────────────┐
        │               │               │            │
        │               │               │            │
┌───────▼────┐  ┌───────▼─────┐  ┌─────▼─────┐  ┌──▼────┐
│ PostgreSQL │  │   Redis     │  │   MinIO   │  │ Audit │
│ (主数据库) │  │  (缓存)     │  │  (对象存储)│  │ Logger│
│ Port: 5432 │  │ Port: 6379  │  │ Port: 9000│  │       │
└────────────┘  └─────────────┘  └───────────┘  └───────┘
```

### 请求流程

#### 1. 用户登录流程

```
浏览器
  │
  │ POST /api/v1/auth/login
  │ { username, password }
  ▼
Frontend (React)
  │
  │ Axios HTTP Request
  ▼
Backend (FastAPI)
  │
  ├─► [1] 验证用户名密码 (PostgreSQL)
  │
  ├─► [2] 生成 JWT Token (core/security.py)
  │
  ├─► [3] 记录审计日志 (core/audit.py → PostgreSQL audit_logs)
  │
  └─► [4] 返回 Token
        │
        ▼ { access_token, refresh_token }
      浏览器
        │
        └─► 存储到 localStorage/sessionStorage
```

#### 2. 创建项目流程

```
浏览器/SDK
  │
  │ POST /api/v1/projects
  │ Authorization: Bearer <token>
  │ { name, description }
  ▼
Backend (FastAPI)
  │
  ├─► [1] 验证 JWT Token (core/security.py)
  │       ├─► 检查 Token 签名
  │       ├─► 检查 Token 过期时间
  │       └─► 检查 Redis 黑名单 (jwt_blacklist:*)
  │
  ├─► [2] 获取当前用户 (PostgreSQL users)
  │
  ├─► [3] 创建项目 (repositories/project_repository.py)
  │       └─► 插入 PostgreSQL projects 表
  │
  ├─► [4] 记录审计日志 (core/audit.py)
  │       └─► 插入 PostgreSQL audit_logs 表
  │
  └─► [5] 返回项目信息
        │
        ▼ { id, name, created_at, ... }
      浏览器/SDK
```

#### 3. 上传 Artifact 流程

```
Python Script (SDK)
  │
  │ project.log_artifact("model.pkl")
  ▼
SDK (wanllmdb)
  │
  │ [1] 计算文件哈希 (MD5/SHA256)
  │
  │ [2] POST /api/v1/artifacts
  │     { name, type, file_hash, metadata }
  ▼
Backend (FastAPI)
  │
  ├─► [3] 验证 Token
  │
  ├─► [4] 生成预签名 URL (services/storage_service.py)
  │       └─► MinIO.presigned_put_object()
  │
  ├─► [5] 创建 Artifact 元数据 (repositories/artifact_repository.py)
  │       ├─► 插入 PostgreSQL artifacts 表
  │       └─► 插入 PostgreSQL artifact_versions 表
  │
  └─► [6] 返回上传 URL
        │
        ▼ { upload_url, artifact_id, version }
      SDK
        │
        ├─► [7] 上传文件到 MinIO
        │       PUT <presigned_url>
        │       Body: file content
        │
        └─► [8] 通知后端上传完成
                POST /api/v1/artifacts/{id}/complete
```

#### 4. 查询运行日志流程

```
浏览器
  │
  │ GET /api/v1/runs/123/logs?skip=0&limit=100
  ▼
Frontend (React)
  │
  │ Axios GET Request
  ▼
Backend (FastAPI)
  │
  ├─► [1] 验证 Token
  │
  ├─► [2] 检查权限 (项目所有者或成员)
  │       └─► PostgreSQL: SELECT project_id FROM runs WHERE id=123
  │
  ├─► [3] 查询日志 (repositories/run_repository.py)
  │       └─► PostgreSQL: SELECT * FROM run_logs
  │                       WHERE run_id=123
  │                       ORDER BY timestamp
  │                       LIMIT 100 OFFSET 0
  │
  └─► [4] 返回日志
        │
        ▼ { logs: [...], total: 500 }
      Frontend
        │
        └─► 渲染日志列表
```

---

## 数据流

### 数据存储策略

| 数据类型 | 存储位置 | 原因 |
|---------|---------|------|
| **用户信息** | PostgreSQL `users` | 结构化数据，需要事务 |
| **项目/运行元数据** | PostgreSQL `projects`, `runs` | 结构化数据，需要关系查询 |
| **运行指标** | PostgreSQL `run_metrics` | 时序数据，可选 TimescaleDB 优化 |
| **运行日志** | PostgreSQL `run_logs` | 文本数据，需要搜索 |
| **Artifact 元数据** | PostgreSQL `artifacts` | 结构化数据 |
| **Artifact 文件** | MinIO | 大文件，对象存储 |
| **模型文件** | MinIO | 大文件，对象存储 |
| **JWT 黑名单** | Redis | 临时数据，快速查询 |
| **会话数据** | Redis | 临时数据，快速访问 |
| **审计日志** | PostgreSQL `audit_logs` | 合规要求，长期存储 |

### 数据生命周期

#### Artifact 版本

```
创建 Artifact
  │
  ├─► PostgreSQL: 插入 artifacts 表 (id, name, type)
  │
  └─► 上传文件到 MinIO: projects/{pid}/artifacts/{name}/v1/
        │
        ▼
      设置别名 (latest, production)
        │
        ├─► PostgreSQL: 插入 artifact_aliases 表
        │
        └─► 创建新版本 v2
              │
              ├─► PostgreSQL: 插入 artifact_versions 表
              │
              ├─► 上传文件到 MinIO: .../v2/
              │
              └─► 更新别名 (latest → v2)
```

#### 运行生命周期

```
开始运行 (running)
  │
  ├─► PostgreSQL: INSERT INTO runs (status='running')
  │
  ├─► 记录日志
  │     └─► PostgreSQL: INSERT INTO run_logs
  │
  ├─► 上传文件
  │     ├─► PostgreSQL: INSERT INTO run_files (metadata)
  │     └─► MinIO: 存储文件内容
  │
  ├─► 记录指标
  │     └─► PostgreSQL: INSERT INTO run_metrics
  │
  └─► 完成运行 (completed/failed)
        └─► PostgreSQL: UPDATE runs SET status='completed'
```

---

## 安全架构

### 认证与授权

```
┌─────────────────────────────────────┐
│        认证流程 (Authentication)    │
└─────────────────────────────────────┘

用户登录
  │
  ├─► [1] 密码验证
  │       ├─► 从 PostgreSQL 获取用户
  │       └─► Passlib.verify_password()
  │
  ├─► [2] 生成 JWT Token
  │       ├─► Payload: { user_id, username, exp }
  │       ├─► 签名: HMAC-SHA256 (SECRET_KEY)
  │       └─► 返回: { access_token, refresh_token }
  │
  └─► [3] Token 使用
        ├─► 每次请求携带: Authorization: Bearer <token>
        ├─► 后端验证签名和过期时间
        └─► 提取用户信息


┌─────────────────────────────────────┐
│        授权流程 (Authorization)     │
└─────────────────────────────────────┘

请求资源 (例: DELETE /api/v1/projects/123)
  │
  ├─► [1] 验证 Token (认证)
  │
  ├─► [2] 获取当前用户
  │
  ├─► [3] 检查权限
  │       ├─► 资源所有者检查: project.user_id == current_user.id
  │       ├─► 管理员检查: current_user.username in ADMIN_USERS
  │       └─► 角色检查 (未来): current_user.role in ['admin', 'editor']
  │
  └─► [4] 允许/拒绝操作
```

### JWT Token 黑名单

```
用户登出
  │
  ├─► POST /api/v1/auth/logout
  │
  ├─► 提取 Token
  │
  ├─► 添加到 Redis 黑名单
  │     ├─► Key: jwt_blacklist:<token_jti>
  │     ├─► Value: "revoked"
  │     └─► TTL: Token 剩余有效期
  │
  └─► 后续请求验证
        ├─► 检查 Redis: EXISTS jwt_blacklist:<token_jti>
        └─► 如果存在 → 拒绝 (401 Unauthorized)
```

### 审计日志

```
任何操作 (创建、更新、删除)
  │
  ├─► 执行业务逻辑
  │
  └─► 记录审计日志 (core/audit.py)
        │
        ├─► 提取请求信息
        │     ├─► IP 地址 (X-Forwarded-For)
        │     ├─► User-Agent
        │     ├─► 请求方法和路径
        │     └─► 用户信息
        │
        ├─► 分类事件
        │     ├─► 类别: authentication, authorization, data_modification
        │     └─► 严重性: critical, high, medium, low, info
        │
        └─► 插入 PostgreSQL audit_logs 表
              ├─► event_type: "project.delete"
              ├─► user_id, username
              ├─► resource_type, resource_id
              ├─► event_metadata: {...}
              └─► created_at
```

---

## 扩展性设计

### 水平扩展

#### Backend (FastAPI)

- **无状态设计**: 所有状态存储在数据库/Redis
- **负载均衡**: Nginx Ingress / K8s Service
- **扩展方式**:
  ```bash
  # Kubernetes
  kubectl scale deployment/backend --replicas=10 -n wanllmdb

  # 自动扩缩容 (HPA)
  kubectl autoscale deployment/backend \
    --cpu-percent=70 --min=2 --max=20 -n wanllmdb
  ```

#### Frontend (React)

- **静态资源**: 可通过 CDN 分发
- **扩展方式**:
  ```bash
  kubectl scale deployment/frontend --replicas=5 -n wanllmdb
  ```

#### PostgreSQL

- **主从复制**: PostgreSQL Streaming Replication
- **读写分离**: 读请求分发到从库
- **分片**: 按项目 ID 分片 (未来)

#### MinIO

- **分布式模式**: MinIO 支持多节点分布式部署
- **Erasure Coding**: 数据冗余和容错
- **扩展方式**: 添加新的 MinIO 节点到集群

### 垂直扩展

```yaml
# Kubernetes 资源调整
resources:
  requests:
    memory: "4Gi"
    cpu: "2000m"
  limits:
    memory: "16Gi"
    cpu: "8000m"
```

### 性能优化

1. **数据库优化**:
   - 索引优化 (已在模型中定义)
   - 连接池 (DATABASE_POOL_SIZE=50)
   - 查询优化 (使用 Repository 模式)

2. **缓存策略**:
   - Redis 缓存热点数据
   - HTTP 缓存头 (ETag, Cache-Control)

3. **CDN**:
   - 静态资源缓存
   - 地理分布

4. **异步处理**:
   - 使用 Celery 处理长时间任务 (未来)
   - WebSocket 实时更新 (未来)

---

## 技术决策

### 为什么选择 FastAPI？

- ✅ 高性能 (基于 Starlette 和 Pydantic)
- ✅ 自动生成 API 文档 (OpenAPI/Swagger)
- ✅ 类型提示和数据验证
- ✅ 异步支持 (async/await)
- ✅ 易于测试

### 为什么选择 PostgreSQL？

- ✅ ACID 事务保证
- ✅ 丰富的数据类型 (JSON, Array, UUID)
- ✅ 强大的查询能力
- ✅ 成熟的生态系统
- ✅ TimescaleDB 扩展支持时序数据

### 为什么选择 MinIO？

- ✅ S3 兼容 API (易于迁移)
- ✅ 开源免费
- ✅ 高性能
- ✅ 支持 Kubernetes 原生部署
- ✅ Erasure Coding 数据保护

### 为什么选择 Redis？

- ✅ 极快的读写速度
- ✅ 丰富的数据结构
- ✅ 支持过期时间 (TTL)
- ✅ 持久化选项
- ✅ 低资源消耗

---

## 未来规划

### 短期 (1-3 个月)

- [ ] 实现完整的 RBAC (基于角色的访问控制)
- [ ] 添加 WebSocket 支持 (实时日志推送)
- [ ] 集成 Prometheus + Grafana 监控
- [ ] 添加数据导出功能 (CSV, JSON)

### 中期 (3-6 个月)

- [ ] 实现分布式追踪 (OpenTelemetry)
- [ ] 添加团队协作功能
- [ ] 支持多租户 (Multi-tenancy)
- [ ] 实现 Artifact 去重 (内容寻址)

### 长期 (6-12 个月)

- [ ] 添加数据血缘追踪 (Lineage)
- [ ] 实现联邦学习支持
- [ ] 添加 AutoML 功能
- [ ] 支持自定义插件系统

---

## 附录

### 环境变量完整列表

查看 `backend/.env.example` 和 `.env.production.example`

### 数据库 Schema

查看 `backend/alembic/versions/`

### API 完整文档

访问: http://localhost:8000/docs (运行时)

---

**版权所有 © 2025 wanLLMDB**
