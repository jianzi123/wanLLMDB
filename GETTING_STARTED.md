# wanLLMDB 快速启动指南

**版本**: 1.0
**更新日期**: 2025-11-16
**适用于**: 开发环境和生产环境

---

## 📋 目录

1. [系统要求](#系统要求)
2. [快速开始（5分钟）](#快速开始5分钟)
3. [开发环境设置](#开发环境设置)
4. [生产环境部署](#生产环境部署)
5. [验证安装](#验证安装)
6. [常见问题](#常见问题)
7. [下一步](#下一步)

---

## 系统要求

### 最低要求

| 组件 | 要求 |
|------|------|
| **操作系统** | Linux, macOS, Windows (WSL2) |
| **Docker** | 20.10+ |
| **Docker Compose** | 2.0+ |
| **内存** | 4GB (推荐8GB+) |
| **磁盘空间** | 10GB+ |
| **端口** | 3000, 8000, 5432, 6379, 9000, 9001 |

### 推荐配置

- **CPU**: 4核+
- **内存**: 8GB+
- **磁盘**: SSD 20GB+

---

## 快速开始（5分钟）

### 步骤1: 克隆仓库

```bash
git clone https://github.com/your-org/wanLLMDB.git
cd wanLLMDB
```

### 步骤2: 启动开发环境

```bash
# 一键启动所有服务（Docker Compose）
docker-compose up -d

# 查看启动状态
docker-compose ps
```

### 步骤3: 等待服务就绪（约30秒）

```bash
# 检查后端健康状态
curl http://localhost:8000/health

# 预期输出：
# {"status":"healthy","timestamp":"2025-11-16T..."}
```

### 步骤4: 访问应用

| 服务 | URL | 说明 |
|------|-----|------|
| **前端界面** | http://localhost:3000 | 主Web界面 |
| **后端API** | http://localhost:8000 | RESTful API |
| **API文档** | http://localhost:8000/docs | Swagger UI |
| **MinIO控制台** | http://localhost:9001 | 对象存储管理 |

**默认登录凭证**（仅开发环境）:
- 用户名: `admin`
- 密码: `admin123`（首次登录后请修改）

### 步骤5: 创建第一个实验

```bash
# 使用Python SDK
pip install wanllmdb

# 运行示例脚本
python examples/quickstart.py
```

**🎉 恭喜！你的wanLLMDB已经运行起来了！**

---

## 开发环境设置

### 方式一：Docker Compose（推荐）

#### 1. 环境配置

```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置（可选，默认配置可直接使用）
nano .env
```

**关键配置项**:
```bash
# 数据库（PostgreSQL）
POSTGRES_DB=wanllmdb
POSTGRES_USER=wanllm
POSTGRES_PASSWORD=dev_password_123

# Redis（缓存和JWT黑名单）
REDIS_URL=redis://redis:6379/0

# MinIO（对象存储）
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=wanllmdb-artifacts

# JWT认证
SECRET_KEY=dev_secret_key_for_local_development_only_min_32_chars

# CORS（前端访问）
CORS_ORIGINS=http://localhost:3000
```

#### 2. 启动服务

```bash
# 后台启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 查看所有服务状态
docker-compose ps
```

#### 3. 运行数据库迁移

```bash
# 进入后端容器
docker-compose exec backend bash

# 运行迁移
poetry run alembic upgrade head

# 退出容器
exit
```

#### 4. 创建测试用户（可选）

```bash
# 使用API创建用户
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
  }'
```

---

### 方式二：本地开发（不使用Docker）

适用于需要调试代码的开发者。

#### 1. 前置服务

需要手动启动：
- PostgreSQL 15+
- Redis 7+
- MinIO（或使用AWS S3）

#### 2. 后端设置

```bash
cd backend

# 安装Poetry（依赖管理工具）
curl -sSL https://install.python-poetry.org | python3 -

# 安装依赖
poetry install

# 配置环境变量
cp .env.example .env
nano .env  # 修改数据库连接等配置

# 运行迁移
poetry run alembic upgrade head

# 启动开发服务器（自动重载）
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器（自动重载）
npm run dev
```

访问: http://localhost:3000

---

## 生产环境部署

### 方式一：使用自动化部署脚本（推荐）

#### 1. 准备环境配置

```bash
# 复制生产环境配置模板
cp .env.production.example .env.production

# 编辑配置（务必修改所有密码！）
nano .env.production
```

**关键配置**（必须修改）:
```bash
# JWT密钥（32字符以上）
SECRET_KEY=生成强密钥，不要使用默认值！

# 数据库密码
POSTGRES_PASSWORD=强密码，不要使用默认值！

# Redis密码
REDIS_PASSWORD=强密码，不要使用默认值！

# MinIO凭证（12字符以上，不能是minioadmin）
MINIO_ACCESS_KEY=强访问密钥12字符以上
MINIO_SECRET_KEY=强密钥12字符以上

# CORS（生产域名）
CORS_ORIGINS=https://your-domain.com
```

**生成强密钥的方法**:
```bash
# SECRET_KEY（32字符）
python -c "import secrets; print(secrets.token_urlsafe(32))"

# MinIO密钥（16字符）
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

#### 2. 初始部署

```bash
cd backend/scripts

# 运行初始部署脚本
./deploy-production.sh --initial
```

**脚本会自动**:
- ✅ 验证环境配置
- ✅ 构建Docker镜像
- ✅ 启动所有服务
- ✅ 运行数据库迁移
- ✅ 创建MinIO存储桶
- ✅ 执行健康检查
- ✅ 显示部署摘要

#### 3. 配置Nginx反向代理

```nginx
# /etc/nginx/sites-available/wanllmdb
server {
    listen 80;
    server_name your-domain.com;

    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL证书（使用Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 后端API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/wanllmdb /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 4. 设置自动备份

```bash
# 编辑crontab
crontab -e

# 添加每日备份任务（凌晨2点）
0 2 * * * /opt/wanllmdb/backend/scripts/backup-database.sh >> /var/log/wanllmdb/backup.log 2>&1
```

---

### 方式二：手动部署

#### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 安装Nginx
sudo apt install nginx -y
```

#### 2. 部署应用

```bash
# 克隆代码
cd /opt
sudo git clone https://github.com/your-org/wanLLMDB.git
cd wanLLMDB

# 配置环境
sudo cp .env.production.example backend/.env
sudo nano backend/.env  # 修改密码

# 启动服务
sudo docker-compose -f docker-compose.prod.yml up -d

# 运行迁移
sudo docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 检查服务状态
sudo docker-compose -f docker-compose.prod.yml ps
```

#### 3. 配置防火墙

```bash
# 仅允许必要端口
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

---

## 验证安装

### 1. 健康检查

```bash
# 基本健康检查
curl http://localhost:8000/health

# 就绪检查（验证依赖）
curl http://localhost:8000/health/ready

# 系统指标
curl http://localhost:8000/metrics | jq
```

**预期输出**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-16T12:00:00.000000"
}
```

### 2. 数据库连接

```bash
# 检查PostgreSQL
docker-compose exec postgres pg_isready -U wanllm

# 检查数据库表
docker-compose exec postgres psql -U wanllm -d wanllmdb -c "\dt"
```

### 3. 对象存储

```bash
# 访问MinIO控制台
open http://localhost:9001

# 登录（使用MINIO_ACCESS_KEY和MINIO_SECRET_KEY）
# 验证bucket "wanllmdb-artifacts" 已创建
```

### 4. API测试

```bash
# 查看API文档
open http://localhost:8000/docs

# 测试注册API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
  }'
```

### 5. 前端访问

```bash
# 打开浏览器
open http://localhost:3000

# 使用创建的用户登录
```

---

## 常见问题

### Q1: 端口已被占用

**错误**: `Error: bind: address already in use`

**解决**:
```bash
# 查看占用端口的进程
sudo lsof -i :8000

# 停止占用的服务或修改.env中的端口配置
# 例如修改BACKEND_PORT=8001
```

### Q2: 数据库迁移失败

**错误**: `alembic.util.exc.CommandError`

**解决**:
```bash
# 检查数据库连接
docker-compose exec backend bash
poetry run alembic current

# 如果显示"头指针不在当前分支"
poetry run alembic stamp head
poetry run alembic upgrade head
```

### Q3: MinIO连接失败

**错误**: `S3 connection error`

**解决**:
```bash
# 检查MinIO服务状态
docker-compose ps minio

# 检查MinIO日志
docker-compose logs minio

# 重启MinIO
docker-compose restart minio

# 验证bucket创建
docker-compose exec minio mc ls local/
```

### Q4: 前端无法连接后端

**错误**: `Network Error` 或 `CORS error`

**解决**:
```bash
# 检查CORS配置
# backend/.env
CORS_ORIGINS=http://localhost:3000

# 检查后端是否运行
curl http://localhost:8000/health

# 检查前端环境变量
# frontend/.env
VITE_API_BASE_URL=http://localhost:8000
```

### Q5: JWT token无效

**错误**: `Could not validate credentials`

**解决**:
```bash
# 检查SECRET_KEY配置
# backend/.env
SECRET_KEY=至少32字符的强密钥

# 清除Redis中的token黑名单
docker-compose exec redis redis-cli FLUSHDB
```

### Q6: Docker容器内存不足

**错误**: `Container killed (OOMKilled)`

**解决**:
```bash
# 增加Docker资源限制
# 编辑docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G  # 增加内存限制
```

### Q7: 数据库连接池耗尽

**错误**: `QueuePool limit exceeded`

**解决**:
```bash
# 增加连接池大小
# backend/.env
DATABASE_POOL_SIZE=100  # 默认50
DATABASE_MAX_OVERFLOW=50  # 默认20
```

---

## 下一步

### 🎓 学习资源

1. **产品功能详解**: 阅读 [PRODUCT_FEATURES.md](./PRODUCT_FEATURES.md)
2. **API文档**: 访问 http://localhost:8000/docs
3. **SDK文档**: 查看 `sdk/README.md`
4. **示例代码**: 浏览 `examples/` 目录

### 🔧 开发指南

- **贡献代码**: 阅读 `CONTRIBUTING.md`
- **架构文档**: 查看 `docs/architecture/`
- **测试指南**: 阅读 `TESTING.md`

### 🚀 生产部署

- **生产部署指南**: 阅读 `PRODUCTION_DEPLOYMENT.md`
- **安全加固**: 查看 `SECURITY_FIXES_IMPLEMENTED.md`
- **监控运维**: 参考 `backend/scripts/README.md`

### 📞 获取帮助

- **GitHub Issues**: https://github.com/your-org/wanLLMDB/issues
- **文档**: https://docs.wanllmdb.com
- **社区**: https://community.wanllmdb.com
- **邮箱**: support@wanllmdb.com

---

## 附录

### 服务管理命令

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart backend

# 查看日志
docker-compose logs -f backend

# 进入容器
docker-compose exec backend bash

# 查看资源使用
docker stats
```

### 数据库管理

```bash
# 连接数据库
docker-compose exec postgres psql -U wanllm -d wanllmdb

# 备份数据库
cd backend/scripts
./backup-database.sh --local-only

# 恢复数据库
./restore-database.sh wanllmdb_backup_TIMESTAMP.sql.gz
```

### 清理和重置

```bash
# 停止并删除所有容器（保留数据卷）
docker-compose down

# 删除所有容器和数据卷（⚠️ 危险操作）
docker-compose down -v

# 清理Docker资源
docker system prune -a
```

---

**祝你使用愉快！** 🎉

如有问题，请查看[常见问题](#常见问题)或联系技术支持。
