# Phase 2 剩余Sprints执行计划

## 执行摘要

基于Phase 1/2 Review分析，Phase 2还有以下关键功能未完成：
- SDK Artifact支持（Critical）
- Run文件管理（High）
- Artifact高级功能（Medium）
- 模型注册表（High）
- 日志系统（High）
- 报告系统（Medium）

本文档规划了Phase 2剩余Sprint的执行顺序和详细任务清单。

**创建日期**: 2024-11-16
**预计总时长**: 8-10周
**状态**: 待执行

---

## 优先级排序

基于功能依赖关系和业务价值，建议执行顺序：

| 优先级 | Sprint | 功能 | 时长 | 原因 |
|-------|--------|------|------|------|
| 🔴 P0 | Sprint 7 | SDK Artifact支持 | 1周 | Critical，阻塞Artifact工作流 |
| 🔴 P0 | Sprint 8 | Run文件管理 | 1周 | High，完善Run功能 |
| 🟡 P1 | Sprint 9 | 日志系统 | 2周 | High，重要的调试功能 |
| 🟡 P1 | Sprint 10-11 | 模型注册表 | 2-3周 | High，MLOps关键组件 |
| 🟢 P2 | Sprint 12 | Artifact高级功能 | 1-2周 | Medium，增强功能 |
| 🟢 P2 | Sprint 13-14 | 报告系统 | 2周 | Medium，协作功能 |

**总计**: 8-10周

---

## Sprint 7: SDK Artifact支持 (Week 1)

### 目标

实现完整的SDK Artifact功能，使用户可以通过Python代码管理Artifacts。

### 优先级：🔴 Critical

**为什么优先**：
- Artifact后端和前端已完成，但SDK缺失导致功能无法使用
- 阻塞wandb用户迁移
- 依赖关系：Model Registry依赖Artifact SDK

### 任务清单

#### 1. SDK Artifact类实现 (~200 lines)

**文件**: `sdk/python/src/wanllmdb/artifact.py`

```python
class Artifact:
    """Artifact for versioning datasets, models, and files."""

    def __init__(self, name: str, type: str, description: str = None, metadata: dict = None):
        """Initialize artifact."""
        self.name = name
        self.type = type  # 'dataset', 'model', 'file', 'code'
        self.description = description
        self.metadata = metadata or {}
        self._files = []  # List of files to upload
        self._version_id = None
        self._manifest = {}

    def add_file(self, local_path: str, name: str = None) -> 'ArtifactFile':
        """Add a single file to the artifact."""
        pass

    def add_dir(self, local_path: str, name: str = None) -> None:
        """Add a directory recursively."""
        pass

    def add_reference(self, uri: str, name: str = None, checksum: bool = True) -> None:
        """Add reference to external file (S3, GCS, etc.)."""
        pass

    def download(self, root: str = None) -> str:
        """Download artifact files."""
        pass

    def get_path(self, name: str) -> str:
        """Get path to a file in the artifact."""
        pass

    def verify(self) -> bool:
        """Verify artifact integrity."""
        pass
```

**关键功能**:
- 文件收集和manifest构建
- MD5/SHA256哈希计算
- 文件去重检查
- 本地缓存管理

#### 2. Run集成 (~100 lines)

**文件**: `sdk/python/src/wanllmdb/run.py` (修改)

```python
class Run:
    def log_artifact(self, artifact: Artifact, aliases: List[str] = None) -> Artifact:
        """Log an artifact."""
        # 1. 创建artifact（如果不存在）
        # 2. 创建新版本
        # 3. 上传文件到MinIO（presigned URLs）
        # 4. 注册文件到版本
        # 5. Finalize版本
        # 6. 添加别名
        pass

    def use_artifact(self, artifact_or_name: Union[str, Artifact],
                     version: str = None,
                     aliases: List[str] = None) -> Artifact:
        """Use an artifact."""
        # 1. 解析artifact名称和版本
        # 2. 查询artifact版本
        # 3. 返回Artifact对象（用于download）
        pass
```

#### 3. 文件上传工作流 (~150 lines)

**文件**: `sdk/python/src/wanllmdb/artifact.py` (扩展)

**流程**:
```python
def _upload_files(self, version_id: str) -> None:
    """Upload all files in the artifact."""
    for file_info in self._files:
        # 1. 计算文件哈希
        md5_hash = self._compute_md5(file_info['local_path'])
        sha256_hash = self._compute_sha256(file_info['local_path'])

        # 2. 请求upload URL
        response = self._client.post(
            f'/artifacts/versions/{version_id}/files/upload-url',
            data={
                'path': file_info['path'],
                'name': file_info['name'],
                'size': file_info['size'],
                'md5_hash': md5_hash,
                'sha256_hash': sha256_hash
            }
        )

        # 3. 上传到MinIO
        upload_url = response['upload_url']
        self._upload_to_storage(file_info['local_path'], upload_url)

        # 4. 注册文件
        self._client.post(
            f'/artifacts/versions/{version_id}/files',
            data={
                'path': file_info['path'],
                'name': file_info['name'],
                'size': file_info['size'],
                'storage_key': response['storage_key'],
                'md5_hash': md5_hash,
                'sha256_hash': sha256_hash
            }
        )
```

#### 4. 本地缓存管理 (~100 lines)

**文件**: `sdk/python/src/wanllmdb/artifact_cache.py`

```python
class ArtifactCache:
    """Local cache for downloaded artifacts."""

    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.path.expanduser('~/.wanllmdb/artifacts')

    def get(self, artifact_id: str, version: str) -> Optional[str]:
        """Get cached artifact path."""
        pass

    def put(self, artifact_id: str, version: str, files: List[dict]) -> str:
        """Cache downloaded artifact."""
        pass

    def cleanup(self, max_size_gb: float = 10.0) -> None:
        """Clean up old artifacts."""
        pass
```

#### 5. 示例代码 (~150 lines)

**文件**: `sdk/python/examples/artifact_example.py`

```python
import wanllmdb as wandb

# Example 1: Log a dataset artifact
run = wandb.init(project='my-project', name='prepare-data')

# Create artifact
dataset = wandb.Artifact(
    name='mnist-dataset',
    type='dataset',
    description='MNIST training and test data'
)

# Add files
dataset.add_file('data/train.csv')
dataset.add_file('data/test.csv')
dataset.add_dir('data/images/')

# Log artifact
wandb.log_artifact(dataset, aliases=['latest', 'v1'])
wandb.finish()

# Example 2: Use an artifact
run = wandb.init(project='my-project', name='train-model')

# Get artifact
dataset = wandb.use_artifact('mnist-dataset:latest')
data_dir = dataset.download()

# Use the data
train_data = pd.read_csv(f'{data_dir}/train.csv')

# Example 3: Log a model artifact
model_artifact = wandb.Artifact('my-model', type='model')
model_artifact.add_file('model.h5')
wandb.log_artifact(model_artifact)
```

### API更新（可选）

如果需要别名功能，需要扩展后端API：

**Backend**: `backend/app/api/v1/artifacts.py`

```python
@router.post("/versions/{version_id}/aliases")
def add_alias(version_id: UUID, alias: str):
    """Add alias to artifact version."""
    pass

@router.get("/{artifact_id}/aliases/{alias}")
def get_version_by_alias(artifact_id: UUID, alias: str):
    """Get artifact version by alias."""
    pass
```

### 测试计划

- [ ] 单元测试：Artifact类方法
- [ ] 集成测试：文件上传/下载工作流
- [ ] 端到端测试：完整artifact生命周期
- [ ] 性能测试：大文件上传（>1GB）

### 交付物

- ✅ `sdk/python/src/wanllmdb/artifact.py` (~350 lines)
- ✅ `sdk/python/src/wanllmdb/artifact_cache.py` (~100 lines)
- ✅ `sdk/python/src/wanllmdb/run.py` (修改，+100 lines)
- ✅ `sdk/python/examples/artifact_example.py` (~150 lines)
- ✅ 测试用例
- ✅ 使用文档

**预估时间**: 1周（5个工作日）

---

## Sprint 8: Run文件管理 (Week 2)

### 目标

实现Run级别的文件上传/下载功能，补齐wandb.save()功能。

### 优先级：🔴 High

### 任务清单

#### 1. Backend Run Files API (~150 lines)

**文件**: `backend/app/api/v1/runs.py` (扩展)

```python
@router.post("/{run_id}/files/upload-url")
def get_run_file_upload_url(run_id: UUID, file_info: FileUploadRequest):
    """Get presigned URL for run file upload."""
    storage_key = f"projects/{run.project_id}/runs/{run_id}/files/{file_info.path}"
    upload_url = storage_service.get_upload_url(storage_key, expires_in=3600)
    return {"upload_url": upload_url, "storage_key": storage_key}

@router.post("/{run_id}/files")
def register_run_file(run_id: UUID, file_data: RunFileCreate):
    """Register uploaded file."""
    pass

@router.get("/{run_id}/files")
def list_run_files(run_id: UUID):
    """List all files for a run."""
    pass

@router.get("/files/{file_id}/download-url")
def get_run_file_download_url(file_id: UUID):
    """Get presigned URL for file download."""
    pass

@router.delete("/files/{file_id}")
def delete_run_file(file_id: UUID):
    """Delete a run file."""
    pass
```

#### 2. Database Schema (~50 lines)

**Migration**: `backend/alembic/versions/003_add_run_files.py`

```python
def upgrade():
    op.create_table(
        'run_files',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('run_id', UUID(as_uuid=True), ForeignKey('runs.id'), nullable=False),
        sa.Column('name', String(255), nullable=False),
        sa.Column('path', String(512), nullable=False),
        sa.Column('size', BigInteger, nullable=False),
        sa.Column('storage_key', String(512), nullable=False),
        sa.Column('content_type', String(100)),
        sa.Column('md5_hash', String(32)),
        sa.Column('created_at', DateTime(timezone=True), server_default=func.now()),
        sa.Index('ix_run_files_run_id', 'run_id'),
    )
```

#### 3. SDK wandb.save() (~100 lines)

**文件**: `sdk/python/src/wanllmdb/sdk.py` (扩展)

```python
def save(glob_str: str = None, base_path: str = '.', policy: str = 'live') -> Union[str, List[str]]:
    """Save files to the current run.

    Args:
        glob_str: Glob pattern (e.g., "*.h5", "checkpoint/*")
        base_path: Base directory for glob search
        policy: 'live' (continuous sync) or 'end' (save on finish)

    Returns:
        Path(s) to saved file(s)
    """
    if not _current_run:
        raise RuntimeError("No active run. Call wandb.init() first.")

    if glob_str is None:
        # Save all files in current directory
        glob_str = '*'

    # Find matching files
    import glob
    matches = glob.glob(os.path.join(base_path, glob_str), recursive=True)

    saved_files = []
    for file_path in matches:
        if os.path.isfile(file_path):
            _current_run._save_file(file_path, policy)
            saved_files.append(file_path)

    return saved_files[0] if len(saved_files) == 1 else saved_files
```

#### 4. Frontend Files Tab (~200 lines)

**文件**: `frontend/src/pages/RunDetailPage.tsx` (扩展)

添加新的"Files" Tab:

```typescript
<Tabs.TabPane tab="Files" key="files">
  <Card>
    <Space direction="vertical" style={{ width: '100%' }}>
      {/* Upload area */}
      <Upload.Dragger
        multiple
        customRequest={handleFileUpload}
        showUploadList={false}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">Click or drag files to upload</p>
      </Upload.Dragger>

      {/* File list */}
      <Table
        dataSource={runFiles}
        columns={[
          { title: 'Name', dataIndex: 'name', key: 'name' },
          { title: 'Size', dataIndex: 'size', key: 'size', render: formatBytes },
          { title: 'Uploaded', dataIndex: 'created_at', key: 'created_at' },
          {
            title: 'Actions',
            key: 'actions',
            render: (_, record) => (
              <Space>
                <Button icon={<DownloadOutlined />} onClick={() => handleDownload(record.id)}>
                  Download
                </Button>
                <Button danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>
                  Delete
                </Button>
              </Space>
            ),
          },
        ]}
      />
    </Space>
  </Card>
</Tabs.TabPane>
```

### 交付物

- ✅ Backend Run Files API (~150 lines)
- ✅ Database migration (~50 lines)
- ✅ SDK `wandb.save()` (~100 lines)
- ✅ Frontend Files Tab (~200 lines)
- ✅ 测试和文档

**预估时间**: 1周（5个工作日）

---

## Sprint 9: 日志系统 (Week 3-4)

### 目标

实现完整的日志收集、存储和查看功能。

### 优先级：🟡 High

### 任务清单

#### 1. Backend日志API (~200 lines)

**数据库模型**: `backend/app/models/run_log.py`

```python
class RunLog(Base):
    __tablename__ = "run_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(PGUUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    level = Column(String(10))  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(50))  # 'stdout', 'stderr', 'sdk'
    line_number = Column(Integer)

    __table_args__ = (
        Index('ix_run_logs_run_id_timestamp', 'run_id', 'timestamp'),
    )
```

**API**: `backend/app/api/v1/run_logs.py`

```python
@router.post("/{run_id}/logs/batch")
def batch_upload_logs(run_id: UUID, logs: List[LogCreate]):
    """Batch upload logs."""
    pass

@router.get("/{run_id}/logs")
def get_run_logs(run_id: UUID,
                 level: Optional[str] = None,
                 search: Optional[str] = None,
                 skip: int = 0,
                 limit: int = 1000):
    """Get run logs with filtering."""
    pass

@router.get("/{run_id}/logs/stream")
async def stream_run_logs(run_id: UUID, websocket: WebSocket):
    """Stream logs via WebSocket."""
    pass
```

#### 2. SDK日志捕获 (~150 lines)

**文件**: `sdk/python/src/wanllmdb/logging.py`

```python
import sys
import logging
from io import StringIO

class LogCapture:
    """Capture stdout/stderr and send to backend."""

    def __init__(self, run):
        self.run = run
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.buffer = []
        self.enabled = True

    def start(self):
        """Start capturing logs."""
        sys.stdout = self._create_wrapper(sys.stdout, 'stdout')
        sys.stderr = self._create_wrapper(sys.stderr, 'stderr')

    def stop(self):
        """Stop capturing logs."""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        self._flush()

    def _create_wrapper(self, stream, source):
        """Create wrapper for stdout/stderr."""
        class StreamWrapper:
            def __init__(self, stream, capture, source):
                self.stream = stream
                self.capture = capture
                self.source = source

            def write(self, text):
                self.stream.write(text)
                if self.capture.enabled:
                    self.capture._add_log(text, self.source)

            def flush(self):
                self.stream.flush()

        return StreamWrapper(stream, self, source)

    def _add_log(self, text, source):
        """Add log to buffer."""
        if text.strip():
            self.buffer.append({
                'message': text,
                'source': source,
                'timestamp': datetime.utcnow().isoformat()
            })
            if len(self.buffer) >= 100:  # Flush every 100 lines
                self._flush()

    def _flush(self):
        """Flush logs to backend."""
        if self.buffer:
            self.run._upload_logs(self.buffer)
            self.buffer = []
```

#### 3. Frontend日志查看器 (~300 lines)

**文件**: `frontend/src/components/LogViewer.tsx`

```typescript
import React, { useEffect, useRef, useState } from 'react';
import { Input, Select, Button, Space } from 'antd';
import { DownloadOutlined, ClearOutlined } from '@ant-design/icons';

interface LogLine {
  timestamp: string;
  level: string;
  message: string;
  source: string;
}

export const LogViewer: React.FC<{ runId: string }> = ({ runId }) => {
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [filter, setFilter] = useState({ level: 'all', search: '' });
  const [autoScroll, setAutoScroll] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  // WebSocket connection for real-time logs
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/api/v1/runs/${runId}/logs/stream`);

    ws.onmessage = (event) => {
      const log = JSON.parse(event.data);
      setLogs((prev) => [...prev, log]);
    };

    return () => ws.close();
  }, [runId]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter((log) => {
    if (filter.level !== 'all' && log.level !== filter.level) return false;
    if (filter.search && !log.message.toLowerCase().includes(filter.search.toLowerCase())) {
      return false;
    }
    return true;
  });

  return (
    <div>
      {/* Toolbar */}
      <Space style={{ marginBottom: 16 }}>
        <Select value={filter.level} onChange={(v) => setFilter({ ...filter, level: v })}>
          <Select.Option value="all">All Levels</Select.Option>
          <Select.Option value="DEBUG">Debug</Select.Option>
          <Select.Option value="INFO">Info</Select.Option>
          <Select.Option value="WARNING">Warning</Select.Option>
          <Select.Option value="ERROR">Error</Select.Option>
        </Select>
        <Input.Search
          placeholder="Search logs..."
          value={filter.search}
          onChange={(e) => setFilter({ ...filter, search: e.target.value })}
          style={{ width: 300 }}
        />
        <Button icon={<ClearOutlined />} onClick={() => setLogs([])}>Clear</Button>
        <Button icon={<DownloadOutlined />}>Download</Button>
      </Space>

      {/* Log display */}
      <div
        ref={containerRef}
        style={{
          height: 600,
          overflow: 'auto',
          backgroundColor: '#1e1e1e',
          color: '#d4d4d4',
          fontFamily: 'monospace',
          padding: 16,
        }}
      >
        {filteredLogs.map((log, idx) => (
          <div key={idx} style={{ marginBottom: 4 }}>
            <span style={{ color: '#888' }}>[{log.timestamp}]</span>
            <span style={{ color: getLevelColor(log.level), marginLeft: 8 }}>
              [{log.level}]
            </span>
            <span style={{ marginLeft: 8 }}>{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

function getLevelColor(level: string): string {
  switch (level) {
    case 'ERROR': return '#f44336';
    case 'WARNING': return '#ff9800';
    case 'INFO': return '#2196f3';
    default: return '#888';
  }
}
```

### 交付物

- ✅ Backend日志API (~200 lines)
- ✅ SDK日志捕获 (~150 lines)
- ✅ Frontend日志查看器 (~300 lines)
- ✅ WebSocket实时流
- ✅ 测试和文档

**预估时间**: 2周（10个工作日）

---

## Sprint 10-11: 模型注册表 (Week 5-7)

### 目标

实现完整的Model Registry系统，支持模型版本管理和阶段转换。

### 优先级：🟡 High

### 任务清单

#### 1. Backend数据模型 (~150 lines)

**文件**: `backend/app/models/model_registry.py`

```python
class RegisteredModel(Base):
    __tablename__ = "registered_models"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    tags = Column(JSON, default=list)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    versions = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")

class ModelStage(str, enum.Enum):
    NONE = "none"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"

class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    model_id = Column(PGUUID(as_uuid=True), ForeignKey("registered_models.id"), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text)
    stage = Column(SQLEnum(ModelStage), default=ModelStage.NONE, index=True)

    # 链接到Run和Artifact
    run_id = Column(PGUUID(as_uuid=True), ForeignKey("runs.id"))
    artifact_version_id = Column(PGUUID(as_uuid=True), ForeignKey("artifact_versions.id"))

    # 元数据
    metrics = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('model_id', 'version', name='uq_model_version'),
    )
```

#### 2. Backend Registry API (~400 lines)

**文件**: `backend/app/api/v1/model_registry.py`

```python
# 模型CRUD
@router.post("/models")
def create_model(model_data: RegisteredModelCreate):
    """Register a new model."""
    pass

@router.get("/models")
def list_models(project_id: Optional[UUID] = None, skip: int = 0, limit: int = 50):
    """List registered models."""
    pass

@router.get("/models/{model_id}")
def get_model(model_id: UUID):
    """Get model details."""
    pass

# 版本管理
@router.post("/models/{model_id}/versions")
def create_model_version(model_id: UUID, version_data: ModelVersionCreate):
    """Create a new model version."""
    pass

@router.get("/models/{model_id}/versions")
def list_model_versions(model_id: UUID):
    """List all versions of a model."""
    pass

@router.get("/models/{model_id}/versions/{version}")
def get_model_version(model_id: UUID, version: str):
    """Get specific model version."""
    pass

# 阶段管理
@router.post("/models/{model_id}/versions/{version}/transition")
def transition_stage(model_id: UUID, version: str, stage: ModelStage):
    """Transition model version to a different stage."""
    # 检查权限
    # 如果stage是production，可能需要审批
    # 更新数据库
    pass

@router.get("/models/stages/{stage}")
def get_models_by_stage(stage: ModelStage):
    """Get all models in a specific stage."""
    pass
```

#### 3. SDK Model Registry (~200 lines)

**文件**: `sdk/python/src/wanllmdb/model_registry.py`

```python
def log_model(path: str, registered_model_name: str,
              version: str = None, tags: List[str] = None,
              description: str = None) -> str:
    """Log a model to the registry.

    Args:
        path: Path to model file
        registered_model_name: Name of the registered model
        version: Version string (auto-generated if None)
        tags: Tags for this version
        description: Version description

    Returns:
        Model version ID
    """
    if not _current_run:
        raise RuntimeError("No active run. Call wandb.init() first.")

    # 1. 创建model artifact
    artifact = Artifact(registered_model_name, type='model')
    artifact.add_file(path)

    # 2. Log artifact
    _current_run.log_artifact(artifact)

    # 3. 注册到Model Registry
    response = _current_run._client.post(
        f'/registry/models/{registered_model_name}/versions',
        data={
            'version': version or f'v{int(time.time())}',
            'run_id': _current_run.id,
            'artifact_version_id': artifact._version_id,
            'tags': tags,
            'description': description,
            'metrics': _current_run.summary
        }
    )

    return response['id']

def use_model(name: str, stage: str = None, version: str = None) -> str:
    """Use a registered model.

    Args:
        name: Registered model name
        stage: 'production', 'staging', etc. (overrides version)
        version: Specific version to use

    Returns:
        Path to downloaded model
    """
    if stage:
        # Get version by stage
        response = _client.get(f'/registry/models/{name}/stages/{stage}')
        version = response['version']

    # Get model version
    model_version = _client.get(f'/registry/models/{name}/versions/{version}')

    # Download artifact
    artifact = use_artifact(model_version['artifact_version_id'])
    return artifact.download()
```

#### 4. Frontend Registry UI (~600 lines)

**文件**: `frontend/src/pages/ModelRegistryPage.tsx`

- 模型列表页（搜索、过滤、阶段标识）
- 模型详情页（版本历史、性能指标、链接的Run）
- 阶段转换UI（按钮+确认）
- 版本对比

### 交付物

- ✅ Backend Registry API (~550 lines)
- ✅ Database migration (~100 lines)
- ✅ SDK model registry (~200 lines)
- ✅ Frontend Registry UI (~600 lines)
- ✅ 测试和文档

**预估时间**: 2-3周（10-15个工作日）

---

## Sprint 12: Artifact高级功能 (Week 8-9, Optional)

### 优先级：🟢 Medium

### 任务清单

1. **Artifact别名系统**
   - 后端别名API
   - SDK别名支持
   - 前端别名管理

2. **云存储集成**
   - S3集成（引用外部文件）
   - GCS集成
   - 预签名URL生成

3. **数据血缘可视化**
   - 依赖图谱构建
   - D3.js可视化
   - 影响分析

**预估时间**: 1-2周

---

## Sprint 13-14: 报告系统 (Week 10-12, Optional)

### 优先级：🟢 Medium

### 任务清单

1. **报告编辑器**
   - Markdown编辑器（react-markdown）
   - 实时预览
   - 代码高亮

2. **图表嵌入**
   - Run图表引用
   - 动态数据更新
   - 图片上传

3. **分享功能**
   - 分享链接生成
   - 权限控制
   - 公开报告

**预估时间**: 2周

---

## 执行方案

### 方案A：核心优先（4周）

**包含**：
- Sprint 7: SDK Artifact支持 ✅
- Sprint 8: Run文件管理 ✅
- Sprint 9: 日志系统 ✅

**优点**：快速补齐最critical的gaps
**缺点**：缺少Model Registry

### 方案B：完整MLOps（7-8周，推荐）⭐

**包含**：
- Sprint 7-11: 全部核心功能
- 包含Model Registry

**优点**：完整MLOps工作流
**缺点**：时间较长

### 方案C：全功能（10-12周）

**包含**：
- Sprint 7-14: 所有功能

**优点**：功能最完整
**缺点**：开发周期长

---

## 建议执行顺序

基于依赖关系和优先级，建议按以下顺序执行：

### 第1-2周：立即开始

**Sprint 7 + 8（并行）**:
- 前端团队：Run Files Tab
- 后端团队：SDK Artifact实现
- 可以并行开发，互不阻塞

### 第3-4周：

**Sprint 9**:
- 日志系统（前后端）

### 第5-7周：

**Sprint 10-11**:
- Model Registry（前后端）

### 第8-12周（可选）：

**Sprint 12-14**:
- Artifact高级功能
- 报告系统

---

## 总结

### 推荐方案：方案B（7-8周）

这是性价比最高的方案，包含：
1. ✅ SDK Artifact支持（Critical）
2. ✅ Run文件管理（High）
3. ✅ 日志系统（High）
4. ✅ Model Registry（High）

完成后，wanLLMDB将具备完整的MLOps核心功能，可以投入生产使用。

### 下一步行动

请确认：
1. 选择执行方案（A/B/C）
2. 是否立即开始Sprint 7（SDK Artifact支持）
3. 团队资源分配

**等待您的指示！** 🚀

---

**文档版本**: v1.0
**创建日期**: 2024-11-16
**状态**: 待批准
