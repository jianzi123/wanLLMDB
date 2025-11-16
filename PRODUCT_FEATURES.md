# wanLLMDB 产品功能详解

**版本**: 1.0
**更新日期**: 2025-11-16

---

## 📚 目录

1. [产品概述](#产品概述)
2. [核心功能模块](#核心功能模块)
3. [功能详解](#功能详解)
4. [使用场景](#使用场景)
5. [与竞品对比](#与竞品对比)
6. [技术架构](#技术架构)
7. [未来规划](#未来规划)

---

## 产品概述

### 什么是wanLLMDB？

**wanLLMDB**是一个**企业级机器学习实验管理平台**，灵感来自Weights & Biases（W&B），旨在帮助AI/ML团队系统化地追踪、管理和优化机器学习实验。

### 核心价值

| 痛点 | wanLLMDB解决方案 |
|------|------------------|
| **实验混乱** 😵 | ✅ 集中式实验追踪，完整记录每次运行 |
| **结果难复现** 🔁 | ✅ 版本化管理代码、数据、模型 |
| **参数调优耗时** ⏱️ | ✅ 自动化超参数优化（Random/Grid/Bayes） |
| **团队协作困难** 👥 | ✅ 项目共享、权限控制、实验对比 |
| **模型部署混乱** 🚀 | ✅ 模型注册中心，阶段化管理（开发→测试→生产） |
| **数据溯源困难** 📊 | ✅ Artifact版本管理，完整的血缘追溯 |

### 产品定位

```
wanLLMDB = MLflow + Weights & Biases + DVC (精简版)
```

- **MLflow**: 模型注册中心、实验追踪
- **Weights & Biases**: 实时可视化、超参数优化
- **DVC**: 数据和模型版本管理

---

## 核心功能模块

### 功能地图

```
wanLLMDB
├── 1. 实验管理 (Experiment Tracking)
│   ├── Projects（项目）
│   ├── Runs（实验运行）
│   ├── Logs（运行日志）
│   └── Files（运行文件）
│
├── 2. 产物管理 (Artifact Management)
│   ├── Artifacts（产物：模型/数据集/代码）
│   ├── Versions（版本控制）
│   ├── Files（文件管理）
│   └── Aliases（别名系统）
│
├── 3. 超参数优化 (Hyperparameter Tuning)
│   ├── Sweeps（扫描配置）
│   ├── Optimization（优化算法）
│   └── Visualization（可视化分析）
│
├── 4. 模型治理 (Model Governance)
│   ├── Model Registry（模型注册）
│   ├── Version Control（版本管理）
│   └── Stage Management（阶段管理）
│
└── 5. 安全与运维 (Security & Ops)
    ├── Authentication（认证）
    ├── Audit Logs（审计日志）
    ├── Monitoring（监控）
    └── Backup（备份）
```

---

## 功能详解

### 1. 实验管理（Experiment Tracking）

#### 1.1 Projects（项目）

**是什么？**
项目是组织实验的顶层容器，类似于Git仓库。一个项目通常对应一个ML任务（如图像分类、NLP情感分析）。

**主要功能**:
- ✅ 创建和管理项目
- ✅ 可见性控制（public/private）
- ✅ 项目统计（运行数、最后活动时间）
- ✅ 搜索和过滤

**使用示例**:
```python
import wanllmdb as wandb

# 创建/加入项目
wandb.init(
    project="image-classification",  # 项目名
    name="resnet50-exp1",            # 实验名
)
```

**适用场景**:
- 团队协作（多人在同一项目下运行实验）
- 组织管理（按业务线或任务类型组织项目）
- 权限控制（私有项目仅团队成员可见）

---

#### 1.2 Runs（实验运行）

**是什么？**
Run代表一次完整的模型训练或实验运行，记录了超参数、指标、产物等所有信息。

**核心字段**:
```python
Run {
    id: UUID,                    # 唯一标识
    name: str,                   # 运行名称（如"resnet50-exp1"）
    project_id: UUID,            # 所属项目

    # 配置
    config: dict,                # 超参数配置

    # 状态
    state: enum,                 # running/finished/crashed/killed
    started_at: datetime,        # 开始时间
    finished_at: datetime,       # 结束时间
    heartbeat_at: datetime,      # 最后心跳时间

    # 环境信息
    git_commit: str,             # Git commit hash
    git_branch: str,             # Git分支
    git_remote: str,             # Git远程地址
    host: str,                   # 运行主机
    os: str,                     # 操作系统
    python_version: str,         # Python版本

    # 组织信息
    tags: list,                  # 标签（如["baseline", "resnet"]）
    notes: str,                  # 备注
}
```

**主要功能**:

1. **创建和配置**
   ```python
   run = wandb.init(
       project="my-project",
       name="experiment-1",
       config={
           "learning_rate": 0.001,
           "batch_size": 64,
           "epochs": 100,
       },
       tags=["baseline", "v1"]
   )
   ```

2. **实时监控**
   ```python
   # 心跳机制（每30秒发送一次）
   wandb.heartbeat()  # 自动调用，标记运行仍在进行
   ```

3. **状态管理**
   ```python
   wandb.finish()       # 正常结束
   wandb.mark_crashed() # 标记为崩溃
   ```

4. **标签系统**
   ```python
   wandb.add_tag("production-ready")
   wandb.remove_tag("baseline")
   ```

**适用场景**:
- 追踪每次训练运行
- 对比不同超参数的效果
- 监控长时间运行的任务
- 记录实验环境信息

---

#### 1.3 Logs（运行日志）

**是什么？**
记录运行过程中的所有日志输出，支持实时流式传输。

**日志级别**:
```python
RunLog {
    level: DEBUG | INFO | WARNING | ERROR,
    message: str,
    timestamp: datetime,
    source: stdout | stderr | sdk | user,
    line_number: int,
}
```

**主要功能**:

1. **自动捕获**
   ```python
   # stdout/stderr自动捕获
   print("Training started...")  # 自动记录
   ```

2. **手动记录**
   ```python
   wandb.log_message("Custom log message", level="INFO")
   ```

3. **实时查看**（WebSocket）
   ```python
   # 前端实时显示日志流
   ws://localhost:8000/api/v1/runs/{run_id}/logs/stream
   ```

4. **批量创建**
   ```python
   # SDK批量发送日志（减少网络请求）
   wandb.log_batch([
       {"level": "INFO", "message": "Epoch 1 started"},
       {"level": "INFO", "message": "Loss: 0.5"},
   ])
   ```

5. **下载导出**
   ```bash
   # 导出为txt/json/csv
   curl http://localhost:8000/api/v1/runs/{run_id}/logs?format=txt
   ```

**适用场景**:
- 调试训练过程
- 监控长时间运行的任务
- 错误追踪
- 生成训练报告

---

#### 1.4 Files（运行文件）

**是什么？**
与运行关联的任意文件（配置文件、脚本、中间结果等）。

**文件类型**:
- 配置文件（config.yaml）
- 训练脚本（train.py）
- 中间输出（predictions.csv）
- 可视化图表（loss_curve.png）
- Checkpoints（model_epoch_10.pth）

**主要功能**:

1. **上传文件**
   ```python
   # 上传单个文件
   wandb.save("config.yaml")

   # 上传目录
   wandb.save("checkpoints/*")
   ```

2. **预签名URL**（直传MinIO）
   ```python
   # 1. 获取上传URL
   url = wandb.get_upload_url("model.pth")

   # 2. 直接上传到MinIO
   requests.put(url, data=open("model.pth", "rb"))

   # 3. 注册文件
   wandb.register_file("model.pth", size=1024000)
   ```

3. **下载文件**
   ```python
   # 获取下载URL
   url = wandb.get_download_url("model.pth")

   # 下载文件
   response = requests.get(url)
   with open("downloaded_model.pth", "wb") as f:
       f.write(response.content)
   ```

4. **文件完整性**
   ```python
   # 自动计算MD5/SHA256
   RunFile {
       md5_hash: "abc123...",
       sha256_hash: "def456...",
   }
   ```

**适用场景**:
- 保存训练配置
- 存储中间结果
- 备份检查点
- 可视化结果

---

### 2. 产物管理（Artifact Management）

#### 2.1 Artifacts（产物）

**是什么？**
Artifact是版本化的数据集、模型或代码的容器。每个artifact可以有多个版本。

**产物类型**:
```python
ArtifactType = "model" | "dataset" | "file" | "code"
```

**示例**:
```python
# 创建模型artifact
model_artifact = wandb.Artifact(
    name="sentiment-classifier",
    type="model",
    description="BERT模型用于情感分类",
    metadata={
        "architecture": "BERT-base",
        "training_samples": 10000,
        "accuracy": 0.92,
    },
    tags=["bert", "nlp", "production"]
)

# 添加文件
model_artifact.add_file("model.pth")
model_artifact.add_dir("tokenizer/")

# 记录artifact
wandb.log_artifact(model_artifact)
```

**主要功能**:

1. **CRUD操作**
   - 创建artifact
   - 查询artifact（按项目、类型、标签）
   - 更新元数据
   - 删除artifact（级联删除所有版本）

2. **版本控制**
   ```python
   # 版本自动递增
   v1 = wandb.Artifact("dataset", type="dataset")  # v1
   v2 = wandb.Artifact("dataset", type="dataset")  # v2
   v3 = wandb.Artifact("dataset", type="dataset")  # v3
   ```

3. **别名系统**（最新功能）
   ```python
   # 创建别名
   wandb.create_alias(
       artifact="sentiment-classifier",
       alias="production",
       version="v3"
   )

   # 使用别名引用
   artifact = wandb.use_artifact("sentiment-classifier:production")
   ```

**适用场景**:
- 数据集版本管理
- 模型版本追踪
- 代码快照
- 实验产物归档

---

#### 2.2 Artifact Versions（版本）

**是什么？**
Artifact的一个不可变快照，包含文件列表和元数据。

**版本字段**:
```python
ArtifactVersion {
    version: str,              # v1, v2, v3...
    description: str,
    file_count: int,
    total_size: int,
    storage_path: str,         # MinIO路径
    digest: str,               # 内容摘要（SHA256）
    run_id: UUID,              # 关联的运行
    is_finalized: bool,        # 是否最终化
    finalized_at: datetime,
}
```

**主要功能**:

1. **创建版本**
   ```python
   # 创建并添加文件
   artifact = wandb.Artifact("dataset", type="dataset")
   artifact.add_file("data.csv")

   # 记录（创建新版本）
   wandb.log_artifact(artifact)
   ```

2. **最终化版本**（不可变）
   ```python
   # 最终化后无法修改
   wandb.finalize_version(artifact_id, version_id)
   ```

3. **查询版本**
   ```python
   # 获取特定版本
   v2 = wandb.use_artifact("dataset:v2")

   # 获取最新版本
   latest = wandb.use_artifact("dataset:latest")
   ```

4. **文件列表**
   ```python
   # 查看版本包含的文件
   files = artifact.files()
   # [
   #   {"path": "data.csv", "size": 1024000},
   #   {"path": "metadata.json", "size": 512},
   # ]
   ```

**适用场景**:
- 数据集迭代（v1→v2→v3）
- 模型演进追踪
- 回滚到历史版本
- 审计和合规

---

#### 2.3 Artifact Files（文件）

**是什么？**
Artifact版本中的单个文件，可以是实际文件或外部引用。

**存储方式**:

1. **本地存储**（MinIO）
   ```python
   ArtifactFile {
       is_reference: false,
       storage_key: "artifacts/abc123/model.pth",
       size: 1024000,
   }
   ```

2. **外部引用**（S3/GCS/HTTP）
   ```python
   ArtifactFile {
       is_reference: true,
       reference_uri: "s3://my-bucket/model.pth",
       size: 1024000,
   }
   ```

**主要功能**:

1. **添加本地文件**
   ```python
   artifact.add_file("model.pth")
   ```

2. **添加外部引用**（防SSRF）
   ```python
   artifact.add_reference(
       uri="s3://my-bucket/large-dataset.tar.gz",
       name="dataset.tar.gz"
   )

   # 自动验证URI安全性：
   # ✅ 允许: s3://, gs://, https://
   # ❌ 拒绝: http://169.254.169.254（AWS元数据）
   # ❌ 拒绝: http://10.0.0.1（私有IP）
   ```

3. **获取下载URL**
   ```python
   url = artifact.get_path("model.pth").download()
   ```

4. **完整性验证**
   ```python
   # 上传时自动计算
   file.md5_hash = "abc123..."
   file.sha256_hash = "def456..."

   # 下载后验证
   assert hashlib.md5(data).hexdigest() == file.md5_hash
   ```

**适用场景**:
- 存储小文件（<100MB）到MinIO
- 引用大文件（>100MB）从S3/GCS
- 多人共享数据集
- 跨项目复用artifact

---

#### 2.4 Artifact Aliases（别名）

**是什么？**
指向特定artifact版本的人类可读标签，如"latest"、"production"、"staging"。

**别名系统**:
```python
ArtifactAlias {
    artifact_id: UUID,
    version_id: UUID,
    alias: str,              # "latest", "production", "v1.0"
    created_by: UUID,
    updated_at: datetime,
}
```

**主要功能**:

1. **创建别名**
   ```python
   # 创建"production"别名
   wandb.create_alias(
       artifact="sentiment-classifier",
       alias="production",
       version="v5"
   )
   ```

2. **更新别名**
   ```python
   # 将"production"指向新版本
   wandb.update_alias(
       artifact="sentiment-classifier",
       alias="production",
       version="v6"  # 从v5升级到v6
   )
   ```

3. **使用别名**
   ```python
   # 总是获取生产环境版本
   model = wandb.use_artifact("sentiment-classifier:production")
   ```

4. **查询别名**
   ```python
   # 查看所有别名
   aliases = wandb.list_aliases("sentiment-classifier")
   # [
   #   {"alias": "latest", "version": "v6"},
   #   {"alias": "production", "version": "v5"},
   #   {"alias": "staging", "version": "v6"},
   # ]
   ```

**典型用法**:
```python
# 1. 训练新模型
artifact = wandb.Artifact("model", type="model")
artifact.add_file("new_model.pth")
wandb.log_artifact(artifact)  # 自动创建 v7

# 2. 标记为latest
wandb.create_alias(artifact, "latest", version="v7")

# 3. 测试通过后，标记为staging
wandb.update_alias(artifact, "staging", version="v7")

# 4. 生产部署后，更新production
wandb.update_alias(artifact, "production", version="v7")
```

**适用场景**:
- 环境管理（dev/staging/prod）
- 版本发布（v1.0, v1.1, v2.0）
- 快速回滚（将production指向旧版本）
- 语义化版本（latest, stable, beta）

---

### 3. 超参数优化（Hyperparameter Tuning）

#### 3.1 Sweeps（扫描）

**是什么？**
Sweep是自动化的超参数搜索任务，系统会自动尝试不同的超参数组合并找到最佳配置。

**优化方法**:
```python
SweepMethod = "random" | "grid" | "bayes"
```

| 方法 | 说明 | 适用场景 |
|------|------|----------|
| **Random** | 随机采样 | 快速探索，参数空间大 |
| **Grid** | 网格搜索 | 参数少，希望全面覆盖 |
| **Bayes** | 贝叶斯优化 | 智能搜索，预算有限 |

**配置示例**:
```python
sweep_config = {
    "method": "bayes",
    "metric": {
        "name": "val_accuracy",
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
        },
        "dropout": {
            "distribution": "uniform",
            "min": 0.1,
            "max": 0.5
        },
        "optimizer": {
            "values": ["adam", "sgd", "rmsprop"]
        }
    },
    "early_terminate": {
        "type": "hyperband",
        "min_iter": 10
    }
}

# 创建sweep
sweep_id = wandb.sweep(sweep_config, project="hyperparameter-tuning")
```

**主要功能**:

1. **创建和配置**
   ```python
   # 定义参数空间
   sweep = wandb.create_sweep(
       name="lr-tuning",
       method="bayes",
       metric_name="val_loss",
       metric_goal="minimize",
       config={...}
   )
   ```

2. **执行sweep**
   ```python
   # Agent自动获取建议的参数并运行
   def train():
       run = wandb.init()
       config = wandb.config  # 自动注入建议的参数

       model = build_model(config)
       accuracy = train_model(model, config)

       wandb.log({"val_accuracy": accuracy})

   # 运行50次实验
   wandb.agent(sweep_id, function=train, count=50)
   ```

3. **状态控制**
   ```python
   wandb.pause_sweep(sweep_id)    # 暂停
   wandb.resume_sweep(sweep_id)   # 恢复
   wandb.finish_sweep(sweep_id)   # 结束
   ```

4. **获取参数建议**（手动模式）
   ```python
   # 获取下一组参数
   suggestion = wandb.suggest_params(sweep_id)
   # {
   #   "learning_rate": 0.0023,
   #   "batch_size": 64,
   #   "dropout": 0.35
   # }
   ```

5. **可视化分析**
   ```python
   # 参数重要性
   importance = wandb.get_param_importance(sweep_id)
   # {
   #   "learning_rate": 0.8,
   #   "batch_size": 0.5,
   #   "dropout": 0.3
   # }

   # 平行坐标图数据
   viz_data = wandb.get_parallel_coords(sweep_id)
   ```

**适用场景**:
- 调整学习率、批大小等超参数
- 对比不同优化器
- 网络结构搜索（层数、节点数）
- 数据增强策略选择

---

#### 3.2 Bayes Optimization（贝叶斯优化）

**底层实现**: Optuna库

**核心思想**:
1. 根据历史试验结果，建立目标函数的概率模型
2. 使用采集函数决定下一个最有希望的参数组合
3. 迭代优化，快速收敛到最优解

**配置**:
```python
sweep_config = {
    "method": "bayes",
    "optuna_config": {
        "sampler": "TPESampler",        # 采样器
        "n_startup_trials": 10,         # 初始随机试验数
        "n_ei_candidates": 24,          # Expected Improvement候选数
    }
}
```

**优势**:
- 🚀 比随机搜索快5-10倍
- 🎯 智能探索和利用平衡
- 📈 支持并行试验

**示例**:
```python
# 100次试验，贝叶斯优化
sweep_config = {
    "method": "bayes",
    "metric": {"name": "f1_score", "goal": "maximize"},
    "parameters": {
        "lr": {"min": 0.0001, "max": 0.1},
        "weight_decay": {"min": 0, "max": 0.01}
    }
}

sweep_id = wandb.sweep(sweep_config)
wandb.agent(sweep_id, train, count=100)

# Bayes优化可能在30-40次试验后就找到接近最优解
# Random搜索可能需要80-100次
```

---

### 4. 模型治理（Model Governance）

#### 4.1 Model Registry（模型注册中心）

**是什么？**
集中管理和追踪模型从开发到生产的完整生命周期。

**模型阶段**:
```python
ModelStage = None | Staging | Production | Archived
```

**生命周期**:
```
训练 → 注册 → 测试(Staging) → 部署(Production) → 归档(Archived)
```

**数据模型**:
```python
RegisteredModel {
    name: str,                 # 模型名称（唯一）
    description: str,
    tags: list,
    project_id: UUID,
    created_by: UUID,
}

ModelVersion {
    model_id: UUID,
    version: str,              # v1, v2, v3...
    description: str,
    stage: ModelStage,         # None/Staging/Production/Archived
    run_id: UUID,              # 关联的训练运行
    artifact_version_id: UUID, # 关联的模型文件
    metrics: dict,             # 性能指标
    tags: list,
    approved_by: UUID,         # 审批人
    approved_at: datetime,
}
```

**主要功能**:

1. **注册模型**
   ```python
   # 1. 训练完成
   run = wandb.init(project="sentiment-analysis")
   model = train_model()
   wandb.log({"accuracy": 0.92})

   # 2. 保存为artifact
   artifact = wandb.Artifact("model", type="model")
   artifact.add_file("model.pth")
   wandb.log_artifact(artifact)

   # 3. 注册到Model Registry
   registered_model = wandb.register_model(
       name="sentiment-classifier",
       description="BERT模型用于电商评论情感分类"
   )

   # 4. 创建模型版本
   version = wandb.create_model_version(
       model_name="sentiment-classifier",
       run_id=run.id,
       artifact_version_id=artifact.version.id,
       description="使用10万条评论训练",
       metrics={"accuracy": 0.92, "f1": 0.91}
   )
   ```

2. **阶段转换**
   ```python
   # None → Staging（测试环境）
   wandb.transition_stage(
       model="sentiment-classifier",
       version="v3",
       to_stage="Staging",
       comment="准备测试"
   )

   # Staging → Production（生产环境）
   wandb.transition_stage(
       model="sentiment-classifier",
       version="v3",
       to_stage="Production",
       comment="测试通过，上线生产"
   )

   # Production → Archived（归档）
   wandb.transition_stage(
       model="sentiment-classifier",
       version="v2",  # 旧版本
       to_stage="Archived",
       comment="被v3替代"
   )
   ```

3. **查询模型**
   ```python
   # 获取所有Production模型
   prod_models = wandb.list_model_versions(
       model="sentiment-classifier",
       stage="Production"
   )

   # 获取最新版本
   latest = wandb.get_latest_version("sentiment-classifier")
   ```

4. **审批机制**
   ```python
   # 需要审批才能进入Production
   wandb.approve_version(
       model="sentiment-classifier",
       version="v3",
       approved_by="tech_lead_id",
       comment="性能提升5%，批准上线"
   )
   ```

**适用场景**:
- 模型版本追踪
- A/B测试（Production中运行多个版本）
- 快速回滚（切换Production版本）
- 合规审计（记录所有阶段转换）

---

### 5. 安全与运维

#### 5.1 Authentication（认证）

**认证方式**: JWT（JSON Web Token）

**主要功能**:

1. **用户注册**
   ```python
   # 密码强度要求：
   # - 最少12字符
   # - 包含大小写字母、数字、特殊字符
   response = requests.post("/api/v1/auth/register", json={
       "username": "john",
       "email": "john@example.com",
       "password": "SecurePass123!",
       "full_name": "John Doe"
   })
   ```

2. **登录**
   ```python
   response = requests.post("/api/v1/auth/login", data={
       "username": "john",
       "password": "SecurePass123!"
   })

   tokens = response.json()
   # {
   #   "access_token": "eyJ0eXAi...",
   #   "refresh_token": "eyJ0eXAi...",
   #   "token_type": "bearer"
   # }
   ```

3. **使用token访问API**
   ```python
   headers = {"Authorization": f"Bearer {access_token}"}
   response = requests.get("/api/v1/projects", headers=headers)
   ```

4. **刷新token**
   ```python
   # access_token过期后（默认30分钟）
   response = requests.post("/api/v1/auth/refresh", data={
       "refresh_token": refresh_token
   })
   ```

5. **登出**（token黑名单）
   ```python
   # token被加入黑名单，无法继续使用
   requests.post("/api/v1/auth/logout", headers=headers)
   ```

**安全特性**:
- ✅ 密码哈希（bcrypt）
- ✅ Token黑名单（Redis）
- ✅ 频率限制（5次/分钟）
- ✅ Token过期（30分钟/7天）

---

#### 5.2 Audit Logs（审计日志）

**是什么？**
记录所有安全关键操作，用于合规审计和安全监控。

**事件类型**:

| 类别 | 事件 | 示例 |
|------|------|------|
| **认证** | 登录成功/失败、登出、密码修改 | `auth.login.success` |
| **授权** | 访问被拒绝 | `authz.access_denied` |
| **数据修改** | 项目/模型/artifact创建/更新/删除 | `project.create` |
| **数据访问** | artifact下载 | `artifact.download` |
| **安全** | 可疑活动、权限变更 | `security.suspicious` |

**日志字段**:
```python
AuditLog {
    event_type: str,           # "auth.login.success"
    event_category: str,       # "authentication"
    severity: str,             # critical/high/medium/low/info

    user_id: UUID,
    username: str,

    ip_address: str,           # IPv4/IPv6
    user_agent: str,
    request_method: str,       # GET/POST/PUT/DELETE
    request_path: str,         # "/api/v1/projects"

    description: str,          # "User 'john' logged in successfully"
    resource_type: str,        # "project"
    resource_id: str,          # "proj-123"

    metadata: dict,            # 额外上下文
    status: str,               # success/failure/error
    created_at: datetime,
}
```

**主要功能**:

1. **自动记录**
   ```python
   # 登录失败自动记录
   # {
   #   "event_type": "auth.login.failed",
   #   "username": "attacker",
   #   "ip_address": "1.2.3.4",
   #   "metadata": {"reason": "invalid_password", "attempts": 5}
   # }
   ```

2. **查询审计日志**（管理员）
   ```python
   # 查询最近失败的登录尝试
   GET /api/v1/audit/logs/security/failed-logins?hours=24

   # 查询特定用户的所有操作
   GET /api/v1/audit/logs/user/{user_id}

   # 高级过滤
   GET /api/v1/audit/logs?
       event_category=data_modification&
       severity=high&
       start_date=2025-01-01&
       end_date=2025-01-31
   ```

3. **统计分析**
   ```python
   GET /api/v1/audit/stats/summary?hours=24

   # {
   #   "total_events": 1523,
   #   "by_category": {
   #     "authentication": 450,
   #     "data_modification": 800,
   #     "data_access": 273
   #   },
   #   "by_severity": {
   #     "critical": 0,
   #     "high": 5,
   #     "medium": 120,
   #     "low": 1398
   #   },
   #   "authentication": {
   #     "successful_logins": 420,
   #     "failed_logins": 30,
   #     "failure_rate": 0.067
   #   }
   # }
   ```

**适用场景**:
- 安全事件调查
- 合规审计（SOC2、ISO27001）
- 检测异常行为（暴力破解、数据泄露）
- 用户行为分析

---

#### 5.3 Monitoring（监控）

**健康检查**:

| 端点 | 用途 | 返回码 |
|------|------|--------|
| `/health` | 基本检查 | 200 OK |
| `/health/ready` | 依赖检查 | 200/503 |
| `/health/live` | 存活检查 | 200 OK |

**监控指标**:
```python
GET /metrics

{
    "application": {
        "name": "wanLLMDB",
        "version": "0.1.0",
        "uptime_seconds": 86400
    },
    "system": {
        "cpu": {"percent": 25.5, "count": 8},
        "memory": {
            "total_bytes": 17179869184,
            "used_bytes": 8589934592,
            "percent": 50.0
        },
        "disk": {
            "total_bytes": 107374182400,
            "used_bytes": 53687091200,
            "percent": 50.0
        }
    },
    "database": {
        "connected": true,
        "database_size_bytes": 1073741824,
        "connection_count": 15,
        "pool_size": 50
    },
    "redis": {
        "connected": true,
        "used_memory_bytes": 5242880,
        "total_keys": 1523
    }
}
```

**适用场景**:
- 负载均衡健康检查
- Kubernetes liveness/readiness probe
- 监控告警（Prometheus/Grafana）
- 性能调优

---

## 使用场景

### 场景1: 图像分类模型开发

**背景**: AI团队需要开发一个商品图像分类模型

**工作流程**:

1. **创建项目**
   ```python
   wandb.init(project="product-classification")
   ```

2. **实验追踪**（尝试不同模型）
   ```python
   # 实验1: ResNet50
   run1 = wandb.init(name="resnet50-baseline", tags=["resnet", "baseline"])
   wandb.config.update({"model": "resnet50", "lr": 0.001})
   # 训练...
   wandb.log({"val_accuracy": 0.85})
   wandb.finish()

   # 实验2: EfficientNet
   run2 = wandb.init(name="efficientnet-v1", tags=["efficientnet"])
   wandb.config.update({"model": "efficientnet_b0", "lr": 0.001})
   # 训练...
   wandb.log({"val_accuracy": 0.88})
   wandb.finish()
   ```

3. **超参数优化**
   ```python
   sweep_config = {
       "method": "bayes",
       "metric": {"name": "val_accuracy", "goal": "maximize"},
       "parameters": {
           "lr": {"min": 0.0001, "max": 0.01},
           "batch_size": {"values": [32, 64, 128]},
           "augmentation": {"values": ["light", "medium", "heavy"]}
       }
   }

   sweep_id = wandb.sweep(sweep_config)
   wandb.agent(sweep_id, train, count=20)
   ```

4. **保存最佳模型**
   ```python
   # 找到最佳实验
   best_run = wandb.get_best_run(metric="val_accuracy", order="max")

   # 保存模型为artifact
   artifact = wandb.Artifact("best-model", type="model")
   artifact.add_file("best_model.pth")
   wandb.log_artifact(artifact, aliases=["latest", "production"])
   ```

5. **模型部署**
   ```python
   # 注册模型
   model = wandb.register_model(
       name="product-classifier",
       description="商品图像分类模型"
   )

   # 创建版本并部署到生产
   version = wandb.create_model_version(
       model="product-classifier",
       artifact="best-model:latest",
       stage="Production"
   )
   ```

---

### 场景2: NLP模型迭代优化

**背景**: 优化情感分析模型性能

**工作流程**:

1. **版本化数据集**
   ```python
   # v1: 原始数据（10k样本）
   dataset_v1 = wandb.Artifact("sentiment-dataset", type="dataset")
   dataset_v1.add_file("reviews_10k.csv")
   wandb.log_artifact(dataset_v1, aliases=["v1"])

   # v2: 扩展数据（50k样本）
   dataset_v2 = wandb.Artifact("sentiment-dataset", type="dataset")
   dataset_v2.add_file("reviews_50k.csv")
   wandb.log_artifact(dataset_v2, aliases=["v2", "latest"])
   ```

2. **对比不同数据版本的效果**
   ```python
   # 使用v1训练
   run1 = wandb.init(name="train-on-v1")
   dataset = wandb.use_artifact("sentiment-dataset:v1")
   # 训练... accuracy: 0.82

   # 使用v2训练
   run2 = wandb.init(name="train-on-v2")
   dataset = wandb.use_artifact("sentiment-dataset:v2")
   # 训练... accuracy: 0.89 (提升7%)
   ```

3. **模型演进**
   ```python
   # v1: LSTM baseline
   model_v1 = train_lstm()
   wandb.log_artifact(model_v1, aliases=["v1"])

   # v2: BERT fine-tuned
   model_v2 = train_bert()
   wandb.log_artifact(model_v2, aliases=["v2", "production"])

   # v3: 集成模型
   model_v3 = ensemble(model_v1, model_v2)
   wandb.log_artifact(model_v3, aliases=["v3", "latest"])
   ```

---

### 场景3: 团队协作实验

**背景**: 5人团队协同开发对话系统

**工作流程**:

1. **创建共享项目**
   ```python
   # Tech Lead创建项目
   project = wandb.create_project(
       name="dialogue-system",
       visibility="private"  # 仅团队可见
   )
   ```

2. **成员并行实验**
   ```python
   # 成员A: 优化intent识别
   wandb.init(project="dialogue-system", name="intent-classifier-v1")

   # 成员B: 优化实体抽取
   wandb.init(project="dialogue-system", name="ner-model-v1")

   # 成员C: 优化对话管理
   wandb.init(project="dialogue-system", name="dialog-manager-v1")
   ```

3. **实验对比和讨论**
   ```python
   # 查看所有runs
   runs = wandb.list_runs("dialogue-system")

   # 按accuracy排序
   best_runs = sorted(runs, key=lambda r: r.metrics["accuracy"], reverse=True)

   # 标记最佳实验
   wandb.add_tag(best_runs[0], "production-candidate")
   ```

4. **模型集成**
   ```python
   # 使用团队最佳组件
   intent_model = wandb.use_artifact("intent-classifier:production")
   ner_model = wandb.use_artifact("ner-model:production")
   dialog_model = wandb.use_artifact("dialog-manager:production")

   # 集成系统
   system = integrate(intent_model, ner_model, dialog_model)
   ```

---

## 与竞品对比

### wanLLMDB vs W&B vs MLflow

| 功能 | wanLLMDB | Weights & Biases | MLflow |
|------|----------|------------------|--------|
| **实验追踪** | ✅ | ✅ | ✅ |
| **超参数优化** | ✅ (Random/Grid/Bayes) | ✅ (强大) | ⚠️ (基础) |
| **模型注册** | ✅ | ⚠️ (有限) | ✅ |
| **Artifact管理** | ✅ | ✅ | ⚠️ (基础) |
| **实时可视化** | ⏳ (计划中) | ✅ (强大) | ⚠️ |
| **协作功能** | ✅ | ✅ | ⚠️ |
| **部署方式** | ✅ 自托管 + 云 | ☁️ 云为主 | ✅ 自托管 |
| **价格** | 🆓 开源 | 💰 付费 | 🆓 开源 |
| **学习曲线** | ⭐⭐⭐ 中等 | ⭐⭐ 简单 | ⭐⭐⭐⭐ 较难 |

### 核心优势

1. **开源自托管**: 数据完全掌控，无隐私泄露风险
2. **企业级安全**: 审计日志、RBAC、数据加密
3. **高性能**: 微服务架构，时序数据库优化
4. **易于集成**: RESTful API，Python SDK，Docker部署

---

## 技术架构

### 系统架构图

```
                          ┌─────────────────┐
                          │  Frontend (React)│
                          └────────┬─────────┘
                                   │ HTTP/WebSocket
                          ┌────────▼─────────┐
                          │  API Gateway (Go) │
                          └────────┬─────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
        ┌───────▼────────┐  ┌─────▼──────┐  ┌───────▼────────┐
        │  Backend (FastAPI)│  │Metric Service│  │  Auth Service  │
        │  - Projects      │  │   (Go)       │  │   (FastAPI)    │
        │  - Runs          │  │              │  │                │
        │  - Artifacts     │  └──────┬───────┘  └────────────────┘
        │  - Sweeps        │         │
        │  - Model Registry│         │
        └─────────┬────────┘         │
                  │                  │
        ┌─────────┼──────────────────┼──────────┐
        │         │                  │          │
  ┌─────▼─────┐ ┌▼──────────┐ ┌────▼─────┐  ┌─▼───────┐
  │PostgreSQL │ │TimescaleDB│ │  Redis   │  │ MinIO   │
  │(主数据)   │ │(时序数据) │ │(缓存/黑名单)│ │(对象存储)│
  └───────────┘ └───────────┘ └──────────┘  └─────────┘
```

### 核心技术栈

**后端**:
- FastAPI (Python) - RESTful API
- SQLAlchemy - ORM
- Alembic - 数据库迁移
- Pydantic - 数据验证
- JWT - 认证
- SlowAPI - 频率限制
- Optuna - 贝叶斯优化

**数据库**:
- PostgreSQL 15 - 主数据库
- TimescaleDB - 时序指标
- Redis 7 - 缓存和token黑名单

**存储**:
- MinIO - 对象存储（S3兼容）

**前端**:
- React 18 + TypeScript
- Redux Toolkit - 状态管理
- Ant Design - UI组件
- Recharts/Plotly - 可视化

**DevOps**:
- Docker + Docker Compose
- Kubernetes (可选)
- GitHub Actions / GitLab CI
- Prometheus + Grafana (监控)

---

## 未来规划

### Roadmap

#### Phase 5: 高级可视化 (Q2 2025)
- ✨ 实时训练曲线
- ✨ 超参数重要性图
- ✨ 模型对比视图
- ✨ 交互式探索（Parallel Coordinates）

#### Phase 6: 协作增强 (Q3 2025)
- ✨ 实验评论和讨论
- ✨ 报告生成和分享
- ✨ 团队仪表板
- ✨ 通知和提醒

#### Phase 7: 企业功能 (Q4 2025)
- ✨ RBAC权限系统
- ✨ SSO集成（LDAP/OAuth）
- ✨ 多租户支持
- ✨ 成本追踪

#### Phase 8: 集成与扩展 (2026)
- ✨ MLflow导入/导出
- ✨ Kubernetes Operator
- ✨ Airflow集成
- ✨ Jupyter插件

---

## 总结

wanLLMDB是一个**功能完整、架构清晰**的ML实验管理平台，适用于：

✅ **个人研究者**: 追踪个人实验，管理模型版本
✅ **小团队**: 协作开发，共享实验结果
✅ **企业**: 大规模实验管理，模型治理，合规审计

**核心优势**:
- 🆓 开源免费
- 🔒 数据私有
- 🚀 高性能
- 🛡️ 企业级安全
- 📈 易于扩展

**立即开始**: 查看 [快速启动指南](./GETTING_STARTED.md)

---

**问题反馈**: https://github.com/your-org/wanLLMDB/issues
**文档**: https://docs.wanllmdb.com
**社区**: https://community.wanllmdb.com
