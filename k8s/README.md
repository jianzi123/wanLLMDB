# wanLLMDB Kubernetes 部署指南

完整的 Kubernetes 部署配置，支持开发和生产环境。

## 📋 目录

- [架构概述](#架构概述)
- [前置要求](#前置要求)
- [快速开始](#快速开始)
- [详细部署步骤](#详细部署步骤)
- [环境配置](#环境配置)
- [运维操作](#运维操作)
- [故障排查](#故障排查)
- [安全最佳实践](#安全最佳实践)

---

## 架构概述

### 组件

- **Frontend**: React/Next.js 应用 (2 副本)
- **Backend**: FastAPI 应用 (2-3 副本)
- **PostgreSQL**: 主数据库 (StatefulSet, 1 副本)
- **Redis**: 缓存和 JWT 黑名单 (StatefulSet, 1 副本)
- **MinIO**: S3 兼容对象存储 (StatefulSet, 1 副本)
- **Ingress**: NGINX Ingress Controller (外部访问)

### 目录结构

```
k8s/
├── base/                          # 基础配置
│   ├── namespace.yaml            # 命名空间
│   ├── configmap.yaml            # 配置映射
│   ├── secrets.yaml.example      # 密钥模板
│   ├── postgres-statefulset.yaml # PostgreSQL
│   ├── redis-statefulset.yaml    # Redis
│   ├── minio-statefulset.yaml    # MinIO
│   ├── backend-deployment.yaml   # 后端应用
│   ├── frontend-deployment.yaml  # 前端应用
│   ├── ingress.yaml              # Ingress 配置
│   └── kustomization.yaml        # Kustomize 配置
├── overlays/
│   ├── development/              # 开发环境覆盖
│   │   ├── kustomization.yaml
│   │   ├── configmap-patch.yaml
│   │   └── ingress-patch.yaml
│   └── production/               # 生产环境覆盖
│       ├── kustomization.yaml
│       ├── configmap-patch.yaml
│       └── ingress-patch.yaml
├── scripts/
│   ├── deploy.sh                 # 主部署脚本
│   ├── generate-secrets.sh       # 生成密钥
│   ├── health-check.sh           # 健康检查
│   ├── backup-database.sh        # 数据库备份
│   └── restore-database.sh       # 数据库恢复
└── README.md                      # 本文档
```

---

## 前置要求

### 必需工具

| 工具 | 版本 | 安装 |
|------|------|------|
| **kubectl** | 1.24+ | [安装指南](https://kubernetes.io/docs/tasks/tools/) |
| **kustomize** | 4.5+ | [安装指南](https://kubectl.docs.kubernetes.io/installation/kustomize/) |
| **Kubernetes Cluster** | 1.24+ | Minikube, Kind, GKE, EKS, AKS 等 |

### 推荐工具

- **helm** (可选): 安装 NGINX Ingress Controller
- **k9s** (可选): Kubernetes CLI 管理工具

### 集群资源要求

#### 开发环境 (最低)
- **CPU**: 4 cores
- **内存**: 8 GB
- **存储**: 50 GB

#### 生产环境 (推荐)
- **CPU**: 16 cores
- **内存**: 32 GB
- **存储**: 500 GB+
- **节点数**: 3+ (高可用)

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/wanLLMDB.git
cd wanLLMDB/k8s
```

### 2. 生成密钥

```bash
cd scripts
chmod +x *.sh
./generate-secrets.sh
```

这会生成 `k8s/base/secrets.yaml` 并显示所有凭证。**请妥善保存这些凭证！**

### 3. 构建 Docker 镜像

```bash
# 构建后端镜像
cd ../backend
docker build -t wanllmdb/backend:latest .

# 构建前端镜像
cd ../frontend
docker build -t wanllmdb/frontend:latest .
```

### 4. 部署到开发环境

```bash
cd ../k8s/scripts
./deploy.sh development apply
```

### 5. 检查部署状态

```bash
./health-check.sh development
```

### 6. 访问应用

```bash
# Port-forward 方式访问
kubectl port-forward -n wanllmdb-dev svc/frontend 3000:3000
kubectl port-forward -n wanllmdb-dev svc/backend 8000:8000

# 浏览器访问
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## 详细部署步骤

### 步骤 1: 准备 Kubernetes 集群

#### 选项 A: 使用 Minikube (本地开发)

```bash
# 安装 Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# 启动集群
minikube start --cpus=4 --memory=8192 --disk-size=50g

# 启用 Ingress 插件
minikube addons enable ingress
```

#### 选项 B: 使用云服务商 (生产环境)

**Google Kubernetes Engine (GKE)**:
```bash
gcloud container clusters create wanllmdb-cluster \
  --num-nodes=3 \
  --machine-type=n1-standard-4 \
  --disk-size=100
```

**Amazon EKS** / **Azure AKS**: 参考各自文档

### 步骤 2: 安装 NGINX Ingress Controller

```bash
# 使用 Helm 安装
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# 等待部署完成
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```

### 步骤 3: 配置密钥

#### 自动生成 (推荐)

```bash
cd k8s/scripts
./generate-secrets.sh
```

#### 手动创建

```bash
cd k8s/base
cp secrets.yaml.example secrets.yaml

# 生成强密钥
python3 -c "import secrets; print(secrets.token_urlsafe(32))"  # SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(16))"  # POSTGRES_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(16))"  # REDIS_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(16))"  # MINIO_ACCESS_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(16))"  # MINIO_SECRET_KEY

# Base64 编码
echo -n "your-secret-here" | base64

# 编辑 secrets.yaml 并填入编码后的值
nano secrets.yaml

# 设置文件权限
chmod 600 secrets.yaml
```

### 步骤 4: 自定义配置

#### 修改域名 (生产环境)

编辑 `k8s/overlays/production/ingress-patch.yaml`:

```yaml
spec:
  tls:
    - hosts:
        - wanllmdb.yourdomain.com        # 修改为你的域名
        - api.wanllmdb.yourdomain.com
      secretName: wanllmdb-tls
  rules:
    - host: wanllmdb.yourdomain.com       # 修改为你的域名
      # ...
    - host: api.wanllmdb.yourdomain.com
      # ...
```

#### 修改资源限制

编辑 `k8s/overlays/production/kustomization.yaml` 中的 `patches` 部分。

### 步骤 5: 部署

#### 开发环境

```bash
cd k8s/scripts
./deploy.sh development apply
```

#### 生产环境

```bash
cd k8s/scripts
./deploy.sh production apply
```

### 步骤 6: 验证部署

```bash
# 健康检查
./health-check.sh production

# 查看所有资源
kubectl get all -n wanllmdb

# 查看日志
kubectl logs -n wanllmdb -l app=backend --tail=100 -f
```

---

## 环境配置

### 开发环境特性

- **命名空间**: `wanllmdb-dev`
- **副本数**: 最小 (Backend: 1, Frontend: 1)
- **资源限制**: 较低
- **存储**: 较小 (PG: 5GB, MinIO: 20GB)
- **Debug**: 启用
- **SSL**: 禁用

### 生产环境特性

- **命名空间**: `wanllmdb`
- **副本数**: 高可用 (Backend: 3, Frontend: 2)
- **资源限制**: 较高
- **存储**: 较大 (PG: 100GB, MinIO: 500GB)
- **Debug**: 禁用
- **SSL**: 启用 (需配置 cert-manager)
- **Pod 反亲和性**: 分散到不同节点

---

## 运维操作

### 扩缩容

```bash
# 手动扩容后端
kubectl scale deployment/backend -n wanllmdb --replicas=5

# 启用水平自动扩缩容 (HPA)
kubectl autoscale deployment/backend \
  -n wanllmdb \
  --cpu-percent=70 \
  --min=2 \
  --max=10
```

### 更新应用

```bash
# 构建新镜像
docker build -t wanllmdb/backend:v1.1.0 ./backend

# 推送到镜像仓库
docker push wanllmdb/backend:v1.1.0

# 更新部署
kubectl set image deployment/backend \
  backend=wanllmdb/backend:v1.1.0 \
  -n wanllmdb

# 查看滚动更新状态
kubectl rollout status deployment/backend -n wanllmdb

# 回滚到上一版本 (如果需要)
kubectl rollout undo deployment/backend -n wanllmdb
```

### 数据库备份与恢复

#### 备份

```bash
cd k8s/scripts

# 备份到默认目录 (./backups)
./backup-database.sh production

# 备份到指定目录
./backup-database.sh production /path/to/backups
```

#### 恢复

```bash
cd k8s/scripts

# 恢复数据库
./restore-database.sh production /path/to/backup.sql.gz

# 重启后端以刷新连接
kubectl rollout restart deployment/backend -n wanllmdb
```

### 查看日志

```bash
# 查看后端日志
kubectl logs -n wanllmdb -l app=backend --tail=100 -f

# 查看特定 Pod 日志
kubectl logs -n wanllmdb backend-xxx-xxx -f

# 查看前一个容器的日志 (崩溃时)
kubectl logs -n wanllmdb backend-xxx-xxx --previous

# 导出日志到文件
kubectl logs -n wanllmdb -l app=backend --since=1h > backend.log
```

### 执行命令

```bash
# 进入 PostgreSQL shell
kubectl exec -it -n wanllmdb postgres-0 -- psql -U wanllm -d wanllmdb

# 进入后端容器
kubectl exec -it -n wanllmdb backend-xxx-xxx -- /bin/bash

# 运行数据库迁移
kubectl exec -it -n wanllmdb backend-xxx-xxx -- poetry run alembic upgrade head
```

### 访问 MinIO 控制台

```bash
# Port-forward 到本地
kubectl port-forward -n wanllmdb svc/minio-console 9001:9001

# 浏览器访问: http://localhost:9001
# 使用生成的 MINIO_ACCESS_KEY 和 MINIO_SECRET_KEY 登录
```

---

## 故障排查

### 常见问题

#### 1. Pods 一直处于 Pending 状态

**原因**: 资源不足或 PVC 无法绑定

**解决**:
```bash
# 查看事件
kubectl describe pod <pod-name> -n wanllmdb

# 检查节点资源
kubectl top nodes

# 检查 PVC 状态
kubectl get pvc -n wanllmdb
```

#### 2. Backend Pods 启动失败

**原因**: 数据库连接失败或密钥配置错误

**解决**:
```bash
# 查看日志
kubectl logs -n wanllmdb <backend-pod> --tail=50

# 检查密钥
kubectl get secret wanllmdb-secrets -n wanllmdb -o yaml

# 检查数据库连接
kubectl exec -n wanllmdb postgres-0 -- pg_isready -U wanllm
```

#### 3. Ingress 无法访问

**原因**: Ingress Controller 未安装或 DNS 未配置

**解决**:
```bash
# 检查 Ingress Controller
kubectl get pods -n ingress-nginx

# 检查 Ingress 资源
kubectl get ingress -n wanllmdb
kubectl describe ingress wanllmdb-ingress -n wanllmdb

# 获取 Ingress IP
kubectl get ingress -n wanllmdb -o wide

# 临时使用 port-forward
kubectl port-forward -n wanllmdb svc/frontend 3000:3000
```

#### 4. MinIO 存储桶未创建

**解决**:
```bash
# 进入 MinIO 容器
kubectl exec -it -n wanllmdb minio-0 -- sh

# 配置 mc (MinIO Client)
mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

# 创建存储桶
mc mb local/wanllmdb-artifacts

# 设置公共访问策略 (如果需要)
mc policy set download local/wanllmdb-artifacts
```

#### 5. 数据库迁移失败

**解决**:
```bash
# 手动运行迁移
kubectl exec -it -n wanllmdb backend-xxx-xxx -- \
  poetry run alembic upgrade head

# 检查当前迁移版本
kubectl exec -it -n wanllmdb backend-xxx-xxx -- \
  poetry run alembic current

# 查看迁移历史
kubectl exec -it -n wanllmdb backend-xxx-xxx -- \
  poetry run alembic history
```

### 调试工具

```bash
# 查看所有资源
kubectl get all -n wanllmdb

# 查看事件
kubectl get events -n wanllmdb --sort-by='.lastTimestamp'

# 描述资源
kubectl describe pod <pod-name> -n wanllmdb
kubectl describe svc <service-name> -n wanllmdb

# 查看资源使用
kubectl top pods -n wanllmdb
kubectl top nodes

# 交互式调试 Pod
kubectl run -it --rm debug --image=busybox --restart=Never -n wanllmdb -- sh
```

---

## 安全最佳实践

### 1. 密钥管理

- ✅ **使用强随机密钥**: 使用 `generate-secrets.sh` 生成
- ✅ **限制文件权限**: `chmod 600 secrets.yaml`
- ✅ **不要提交密钥到 Git**: 添加 `secrets.yaml` 到 `.gitignore`
- ✅ **定期轮换密钥**: 每 90 天更换一次生产密钥
- ✅ **使用外部密钥管理**: 考虑使用 HashiCorp Vault 或云厂商 KMS

### 2. 网络安全

- ✅ **启用 TLS/SSL**: 生产环境必须使用 HTTPS
- ✅ **配置网络策略**: 限制 Pod 间通信
- ✅ **启用 RBAC**: 限制 ServiceAccount 权限
- ✅ **使用 Ingress 速率限制**: 防止 DDoS 攻击

示例网络策略:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-network-policy
  namespace: wanllmdb
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - protocol: TCP
          port: 6379
```

### 3. 资源限制

- ✅ **设置 Resource Requests 和 Limits**: 防止资源耗尽
- ✅ **配置 Pod Security Policies**: 限制特权容器
- ✅ **启用 Quota**: 限制命名空间资源使用

### 4. 备份策略

- ✅ **定期备份数据库**: 使用 CronJob 自动备份
- ✅ **异地备份**: 将备份存储到其他区域
- ✅ **测试恢复流程**: 定期验证备份可用性

自动备份 CronJob 示例:

```yaml
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

### 5. 监控与告警

- ✅ **部署 Prometheus + Grafana**: 监控集群指标
- ✅ **配置告警规则**: 及时发现问题
- ✅ **集中日志管理**: 使用 ELK Stack 或 Loki

---

## 清理资源

### 删除应用 (保留 PVC)

```bash
cd k8s/scripts
./deploy.sh production delete
```

### 完全删除 (包括数据)

```bash
# 删除应用
./deploy.sh production delete

# 删除 PVC (数据将永久丢失!)
kubectl delete pvc --all -n wanllmdb

# 删除命名空间
kubectl delete namespace wanllmdb
```

---

## 支持与贡献

- **问题反馈**: [GitHub Issues](https://github.com/your-org/wanLLMDB/issues)
- **文档**: [完整文档](https://docs.wanllmdb.com)
- **社区**: [Discussion](https://github.com/your-org/wanLLMDB/discussions)

---

## 许可证

详见 [LICENSE](../LICENSE) 文件。
