# wanLLMDB 运维操作指南

完整的服务启动、重启、升级操作手册。

**版本**: 1.0
**更新日期**: 2025-11-16

---

## 📋 目录

- [服务启动](#服务启动)
- [服务重启](#服务重启)
- [代码升级](#代码升级)
- [日志查看](#日志查看)
- [数据库操作](#数据库操作)
- [故障排查](#故障排查)
- [监控与告警](#监控与告警)
- [备份与恢复](#备份与恢复)

---

## 服务启动

### 方式一：本地开发（不使用 Docker）

适用于开发调试场景。

#### 1. 启动基础服务

```bash
# 启动 PostgreSQL
sudo systemctl start postgresql
# 或使用 Docker
docker run -d --name postgres \
  -e POSTGRES_DB=wanllmdb \
  -e POSTGRES_USER=wanllm \
  -e POSTGRES_PASSWORD=dev_password_123 \
  -p 5432:5432 \
  postgres:15-alpine

# 启动 Redis
sudo systemctl start redis
# 或使用 Docker
docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine

# 启动 MinIO
docker run -d --name minio \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  -p 9000:9000 -p 9001:9001 \
  minio/minio server /data --console-address ":9001"
```

#### 2. 启动后端服务

```bash
cd backend

# 安装依赖（首次）
poetry install

# 配置环境变量
cp .env.example .env
nano .env  # 修改数据库连接等配置

# 运行数据库迁移
poetry run alembic upgrade head

# 启动开发服务器（自动重载）
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用后台运行
nohup poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

**访问**:
- API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

#### 3. 启动前端服务

```bash
cd frontend

# 安装依赖（首次）
npm install

# 配置环境变量
cp .env.example .env.local
nano .env.local  # 修改 API 地址

# 启动开发服务器
npm run dev

# 或使用后台运行
nohup npm run dev > frontend.log 2>&1 &
```

**访问**: http://localhost:3000

---

### 方式二：Docker Compose（推荐开发环境）

适用于快速搭建完整开发环境。

#### 1. 启动所有服务

```bash
# 进入项目根目录
cd wanLLMDB

# 首次启动（构建镜像）
docker-compose up -d --build

# 后续启动（不重新构建）
docker-compose up -d

# 前台运行（查看日志）
docker-compose up
```

#### 2. 验证服务状态

```bash
# 查看所有服务状态
docker-compose ps

# 预期输出：
NAME                COMMAND                  SERVICE             STATUS              PORTS
wanllmdb-backend    "uvicorn app.main:..."   backend             Up 2 minutes        0.0.0.0:8000->8000/tcp
wanllmdb-frontend   "npm run dev"            frontend            Up 2 minutes        0.0.0.0:3000->3000/tcp
wanllmdb-postgres   "docker-entrypoint..."   postgres            Up 2 minutes        0.0.0.0:5432->5432/tcp
wanllmdb-redis      "redis-server --req..."  redis               Up 2 minutes        0.0.0.0:6379->6379/tcp
wanllmdb-minio      "minio server /data..."  minio               Up 2 minutes        0.0.0.0:9000-9001->9000-9001/tcp
```

#### 3. 初始化数据库（首次启动）

```bash
# 进入后端容器
docker-compose exec backend bash

# 运行迁移
poetry run alembic upgrade head

# 退出容器
exit
```

#### 4. 访问服务

| 服务 | URL | 说明 |
|------|-----|------|
| 前端 | http://localhost:3000 | Web 界面 |
| 后端 API | http://localhost:8000 | RESTful API |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| MinIO 控制台 | http://localhost:9001 | 对象存储管理 |
| PostgreSQL | localhost:5432 | 数据库（需客户端连接） |
| Redis | localhost:6379 | 缓存（需客户端连接） |

---

### 方式三：Kubernetes（生产环境）

适用于生产环境和大规模部署。

#### 1. 首次部署

```bash
cd k8s/scripts

# 生成密钥
./generate-secrets.sh

# 部署到生产环境
./deploy.sh production apply

# 等待所有 Pod 就绪（约 2-5 分钟）
kubectl get pods -n wanllmdb -w
```

#### 2. 验证部署

```bash
# 运行健康检查
./health-check.sh production

# 查看服务状态
kubectl get all -n wanllmdb

# 查看 Ingress
kubectl get ingress -n wanllmdb
```

#### 3. 访问服务

**通过 Ingress（需配置 DNS）**:
- https://wanllmdb.example.com
- https://api.wanllmdb.example.com

**通过 Port-Forward（本地测试）**:
```bash
# 前端
kubectl port-forward -n wanllmdb svc/frontend 3000:3000

# 后端
kubectl port-forward -n wanllmdb svc/backend 8000:8000

# MinIO 控制台
kubectl port-forward -n wanllmdb svc/minio-console 9001:9001
```

---

## 服务重启

### Docker Compose 环境

#### 重启所有服务

```bash
docker-compose restart
```

#### 重启单个服务

```bash
# 重启后端
docker-compose restart backend

# 重启前端
docker-compose restart frontend

# 重启数据库（注意：会中断连接）
docker-compose restart postgres
```

#### 强制重新创建容器

```bash
# 重新创建所有容器
docker-compose down
docker-compose up -d

# 重新创建单个容器
docker-compose up -d --force-recreate backend
```

---

### Kubernetes 环境

#### 重启 Deployment（推荐）

```bash
# 重启后端（滚动重启，零停机）
kubectl rollout restart deployment/backend -n wanllmdb

# 重启前端
kubectl rollout restart deployment/frontend -n wanllmdb

# 查看重启进度
kubectl rollout status deployment/backend -n wanllmdb
```

#### 重启 StatefulSet

```bash
# 重启 PostgreSQL（会中断连接）
kubectl rollout restart statefulset/postgres -n wanllmdb

# 重启 Redis
kubectl rollout restart statefulset/redis -n wanllmdb

# 重启 MinIO
kubectl rollout restart statefulset/minio -n wanllmdb
```

#### 删除 Pod 强制重启

```bash
# 删除特定 Pod（自动重建）
kubectl delete pod backend-xxx-xxx -n wanllmdb

# 删除所有后端 Pod（逐个重启）
kubectl delete pods -l app=backend -n wanllmdb
```

---

### 本地开发环境

#### 后端重启

```bash
# 方式 1: 如果使用 --reload 模式，代码改动会自动重载
# 无需手动重启

# 方式 2: 手动重启
# 找到进程并杀掉
ps aux | grep uvicorn
kill <PID>

# 重新启动
cd backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端重启

```bash
# 方式 1: 如果使用 npm run dev，代码改动会自动重载
# 无需手动重启

# 方式 2: 手动重启
# 停止服务 (Ctrl+C)
# 重新启动
cd frontend
npm run dev
```

---

## 代码升级

### 场景一：本地开发代码修改

#### 后端代码修改

```bash
# 1. 修改代码
nano backend/app/api/v1/projects.py

# 2. 如果使用 --reload 模式，自动生效
# 如果没有使用 --reload，需要重启服务

# 3. 如果修改了数据库模型，需要创建迁移
cd backend
poetry run alembic revision --autogenerate -m "描述修改内容"
poetry run alembic upgrade head
```

#### 前端代码修改

```bash
# 1. 修改代码
nano frontend/src/pages/index.tsx

# 2. 开发模式下自动热重载，无需手动操作

# 3. 如果修改了依赖，需要重新安装
npm install
```

---

### 场景二：Docker Compose 环境升级

#### 完整升级流程

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 停止服务
docker-compose down

# 3. 重新构建镜像（如果代码有改动）
docker-compose build

# 4. 启动服务
docker-compose up -d

# 5. 运行数据库迁移（如果有新迁移）
docker-compose exec backend poetry run alembic upgrade head

# 6. 验证服务
docker-compose ps
curl http://localhost:8000/health
```

#### 仅升级后端

```bash
# 1. 重新构建后端镜像
docker-compose build backend

# 2. 重启后端服务
docker-compose up -d --no-deps backend

# 3. 运行迁移
docker-compose exec backend poetry run alembic upgrade head

# 4. 验证
docker-compose logs backend --tail=50
curl http://localhost:8000/health
```

#### 仅升级前端

```bash
# 1. 重新构建前端镜像
docker-compose build frontend

# 2. 重启前端服务
docker-compose up -d --no-deps frontend

# 3. 验证
curl http://localhost:3000
```

---

### 场景三：Kubernetes 生产环境升级（零停机）

#### 完整升级流程（推荐）

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 构建新版本镜像（添加版本标签）
cd backend
docker build -t wanllmdb/backend:v1.2.0 .
docker tag wanllmdb/backend:v1.2.0 wanllmdb/backend:latest

cd ../frontend
docker build -t wanllmdb/frontend:v1.2.0 .
docker tag wanllmdb/frontend:v1.2.0 wanllmdb/frontend:latest

# 3. 推送到镜像仓库
docker push wanllmdb/backend:v1.2.0
docker push wanllmdb/backend:latest
docker push wanllmdb/frontend:v1.2.0
docker push wanllmdb/frontend:latest

# 4. 更新 Kubernetes Deployment
kubectl set image deployment/backend \
  backend=wanllmdb/backend:v1.2.0 \
  -n wanllmdb

kubectl set image deployment/frontend \
  frontend=wanllmdb/frontend:v1.2.0 \
  -n wanllmdb

# 5. 监控滚动更新进度
kubectl rollout status deployment/backend -n wanllmdb
kubectl rollout status deployment/frontend -n wanllmdb

# 6. 验证新版本
kubectl get pods -n wanllmdb -l app=backend
kubectl logs -n wanllmdb -l app=backend --tail=50

# 7. 如果有问题，快速回滚
kubectl rollout undo deployment/backend -n wanllmdb
```

#### 数据库迁移（有 Schema 变更时）

```bash
# 1. 运行迁移前先备份数据库
cd k8s/scripts
./backup-database.sh production

# 2. 在一个 Pod 中运行迁移
kubectl exec -it -n wanllmdb deployment/backend -- \
  poetry run alembic upgrade head

# 3. 验证迁移成功
kubectl exec -it -n wanllmdb deployment/backend -- \
  poetry run alembic current

# 4. 重启所有后端 Pod 以刷新连接
kubectl rollout restart deployment/backend -n wanllmdb
```

#### 使用 Kustomize 升级（推荐）

```bash
# 1. 更新镜像标签
cd k8s/overlays/production
nano kustomization.yaml

# 添加 images 配置：
# images:
#   - name: wanllmdb/backend
#     newTag: v1.2.0
#   - name: wanllmdb/frontend
#     newTag: v1.2.0

# 2. 应用更新
kubectl apply -k k8s/overlays/production

# 3. 监控部署
kubectl rollout status deployment/backend -n wanllmdb
```

#### 金丝雀发布（灰度发布）

```bash
# 1. 创建金丝雀 Deployment
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-canary
  namespace: wanllmdb
spec:
  replicas: 1  # 仅 1 个副本用于测试
  selector:
    matchLabels:
      app: backend
      version: canary
  template:
    metadata:
      labels:
        app: backend
        version: canary
    spec:
      containers:
        - name: backend
          image: wanllmdb/backend:v1.2.0
          # ... 其他配置同主 Deployment
EOF

# 2. 观察金丝雀 Pod 日志和指标
kubectl logs -n wanllmdb -l version=canary --tail=100 -f

# 3. 如果一切正常，升级主 Deployment
kubectl set image deployment/backend \
  backend=wanllmdb/backend:v1.2.0 \
  -n wanllmdb

# 4. 删除金丝雀 Deployment
kubectl delete deployment backend-canary -n wanllmdb
```

---

## 日志查看

### Docker Compose 环境

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs backend -f
docker-compose logs frontend -f

# 查看最近 100 行日志
docker-compose logs backend --tail=100

# 查看特定时间范围日志
docker-compose logs backend --since 2025-11-16T10:00:00
```

### Kubernetes 环境

```bash
# 查看后端日志（所有 Pod）
kubectl logs -n wanllmdb -l app=backend --tail=100 -f

# 查看特定 Pod 日志
kubectl logs -n wanllmdb backend-xxx-xxx -f

# 查看前一个容器日志（Pod 崩溃后）
kubectl logs -n wanllmdb backend-xxx-xxx --previous

# 导出日志到文件
kubectl logs -n wanllmdb -l app=backend --since=1h > backend.log

# 查看多个 Pod 日志（使用 stern 工具）
stern -n wanllmdb backend
```

### 本地开发环境

```bash
# 如果使用 nohup 后台运行
tail -f backend.log
tail -f frontend.log

# 直接查看 uvicorn 日志（前台运行）
# 日志会直接输出到终端
```

---

## 数据库操作

### 连接数据库

#### Docker Compose 环境

```bash
# 连接 PostgreSQL
docker-compose exec postgres psql -U wanllm -d wanllmdb

# 连接 Redis
docker-compose exec redis redis-cli
```

#### Kubernetes 环境

```bash
# 连接 PostgreSQL
kubectl exec -it -n wanllmdb postgres-0 -- psql -U wanllm -d wanllmdb

# 连接 Redis
REDIS_PASSWORD=$(kubectl get secret wanllmdb-secrets -n wanllmdb -o jsonpath='{.data.REDIS_PASSWORD}' | base64 -d)
kubectl exec -it -n wanllmdb redis-0 -- redis-cli -a "$REDIS_PASSWORD"
```

### 数据库迁移

#### 创建新迁移

```bash
cd backend

# 自动生成迁移（推荐）
poetry run alembic revision --autogenerate -m "添加新表 experiments"

# 手动创建迁移
poetry run alembic revision -m "自定义迁移"
```

#### 应用迁移

```bash
# 升级到最新版本
poetry run alembic upgrade head

# 升级到特定版本
poetry run alembic upgrade <revision_id>

# 降级一个版本
poetry run alembic downgrade -1

# 查看当前版本
poetry run alembic current

# 查看迁移历史
poetry run alembic history
```

### 数据库备份与恢复

#### Docker Compose 环境

**备份**:
```bash
# 使用脚本备份
cd backend/scripts
./backup-database.sh --local-only

# 手动备份
docker-compose exec postgres pg_dump -U wanllm -d wanllmdb | gzip > backup.sql.gz
```

**恢复**:
```bash
# 使用脚本恢复
./restore-database.sh backup.sql.gz

# 手动恢复
gunzip < backup.sql.gz | docker-compose exec -T postgres psql -U wanllm -d wanllmdb
```

#### Kubernetes 环境

**备份**:
```bash
cd k8s/scripts
./backup-database.sh production
```

**恢复**:
```bash
./restore-database.sh production /path/to/backup.sql.gz
```

---

## 故障排查

### 常见问题与解决方案

#### 1. 服务无法启动

**症状**: 容器/Pod 一直重启

**排查步骤**:
```bash
# Docker Compose
docker-compose logs backend --tail=50

# Kubernetes
kubectl describe pod backend-xxx-xxx -n wanllmdb
kubectl logs backend-xxx-xxx -n wanllmdb --previous
```

**常见原因**:
- 数据库连接失败 → 检查数据库是否启动、连接字符串是否正确
- 端口被占用 → 修改端口配置
- 环境变量缺失 → 检查 .env 或 ConfigMap/Secret
- 依赖服务未就绪 → 等待依赖服务启动

#### 2. 数据库连接错误

**错误**: `could not connect to server: Connection refused`

**解决**:
```bash
# 检查 PostgreSQL 是否运行
docker-compose ps postgres  # Docker
kubectl get pods -n wanllmdb -l app=postgres  # K8s

# 检查连接字符串
echo $DATABASE_URL

# 测试连接
docker-compose exec backend bash
poetry run python -c "from app.db.database import engine; engine.connect()"
```

#### 3. MinIO 存储桶未创建

**错误**: `NoSuchBucket: The specified bucket does not exist`

**解决**:
```bash
# Docker Compose
docker-compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker-compose exec minio mc mb local/wanllmdb-artifacts

# Kubernetes
kubectl exec -it -n wanllmdb minio-0 -- sh
mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
mc mb local/wanllmdb-artifacts
```

#### 4. 前端无法连接后端

**错误**: `Network Error` 或 `CORS error`

**解决**:
```bash
# 检查后端是否运行
curl http://localhost:8000/health

# 检查 CORS 配置
# backend/.env
CORS_ORIGINS=http://localhost:3000

# 检查前端 API 地址
# frontend/.env.local
VITE_API_BASE_URL=http://localhost:8000
```

#### 5. 内存不足（OOM）

**症状**: Pod 被 OOMKilled

**解决**:
```bash
# 查看资源使用
kubectl top pods -n wanllmdb

# 增加内存限制
# 编辑 k8s/base/backend-deployment.yaml
resources:
  limits:
    memory: "4Gi"  # 增加限制

# 应用更新
kubectl apply -f k8s/base/backend-deployment.yaml
```

---

## 监控与告警

### 健康检查

```bash
# 基本健康检查
curl http://localhost:8000/health

# 就绪检查（含依赖验证）
curl http://localhost:8000/health/ready

# 存活检查
curl http://localhost:8000/health/live

# 系统指标
curl http://localhost:8000/metrics | jq
```

### Kubernetes 监控

```bash
# 查看 Pod 状态
kubectl get pods -n wanllmdb -w

# 查看事件
kubectl get events -n wanllmdb --sort-by='.lastTimestamp' | tail -20

# 查看资源使用
kubectl top pods -n wanllmdb
kubectl top nodes

# 查看 Pod 详情
kubectl describe pod backend-xxx-xxx -n wanllmdb
```

---

## 备份与恢复

### 定期备份策略

#### 手动备份

```bash
# Docker Compose
cd backend/scripts
./backup-database.sh --local-only

# Kubernetes
cd k8s/scripts
./backup-database.sh production
```

#### 自动备份（Cron）

**Docker Compose 环境**:
```bash
# 添加到 crontab
crontab -e

# 每天凌晨 2 点备份
0 2 * * * cd /path/to/wanLLMDB/backend/scripts && ./backup-database.sh --local-only >> /var/log/wanllmdb-backup.log 2>&1
```

**Kubernetes 环境**:
```yaml
# k8s/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: wanllmdb
spec:
  schedule: "0 2 * * *"  # 每天凌晨 2 点
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:15-alpine
              command:
                - /bin/sh
                - -c
                - |
                  pg_dump -U wanllm -d wanllmdb | \
                  gzip > /backup/wanllmdb_$(date +%Y%m%d_%H%M%S).sql.gz
              env:
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: wanllmdb-secrets
                      key: POSTGRES_PASSWORD
              volumeMounts:
                - name: backup-storage
                  mountPath: /backup
          restartPolicy: OnFailure
          volumes:
            - name: backup-storage
              persistentVolumeClaim:
                claimName: backup-pvc
```

### 数据恢复

```bash
# Docker Compose
cd backend/scripts
./restore-database.sh /path/to/backup.sql.gz

# Kubernetes
cd k8s/scripts
./restore-database.sh production /path/to/backup.sql.gz

# 恢复后重启后端
kubectl rollout restart deployment/backend -n wanllmdb
```

---

## 安全加固

### 1. 更新密钥

```bash
# 生成新密钥
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Docker Compose: 更新 .env
nano .env

# Kubernetes: 更新 Secret
kubectl create secret generic wanllmdb-secrets \
  --from-literal=SECRET_KEY=<new-key> \
  --dry-run=client -o yaml | kubectl apply -f -

# 重启服务使密钥生效
kubectl rollout restart deployment/backend -n wanllmdb
```

### 2. 更新证书

```bash
# Kubernetes TLS 证书（使用 cert-manager 自动更新）
kubectl get certificate -n wanllmdb
kubectl describe certificate wanllmdb-tls -n wanllmdb

# 手动更新证书
kubectl create secret tls wanllmdb-tls \
  --cert=/path/to/cert.pem \
  --key=/path/to/key.pem \
  -n wanllmdb \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 常用运维命令速查

### Docker Compose

| 操作 | 命令 |
|------|------|
| 启动所有服务 | `docker-compose up -d` |
| 停止所有服务 | `docker-compose down` |
| 重启服务 | `docker-compose restart <service>` |
| 查看日志 | `docker-compose logs -f <service>` |
| 查看状态 | `docker-compose ps` |
| 执行命令 | `docker-compose exec <service> <command>` |
| 重建容器 | `docker-compose up -d --force-recreate <service>` |

### Kubernetes

| 操作 | 命令 |
|------|------|
| 查看 Pod | `kubectl get pods -n wanllmdb` |
| 查看日志 | `kubectl logs -f <pod> -n wanllmdb` |
| 重启 Deployment | `kubectl rollout restart deployment/<name> -n wanllmdb` |
| 扩缩容 | `kubectl scale deployment/<name> --replicas=N -n wanllmdb` |
| 执行命令 | `kubectl exec -it <pod> -n wanllmdb -- <command>` |
| 查看事件 | `kubectl get events -n wanllmdb` |
| Port-forward | `kubectl port-forward svc/<service> <local>:<remote> -n wanllmdb` |

---

## 联系支持

如遇到无法解决的问题：

- **GitHub Issues**: https://github.com/your-org/wanLLMDB/issues
- **文档**: https://docs.wanllmdb.com
- **邮箱**: support@wanllmdb.com

---

**版权所有 © 2025 wanLLMDB**
