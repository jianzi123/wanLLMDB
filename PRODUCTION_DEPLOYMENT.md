# Production Deployment Guide - wanLLMDB

**Version**: 1.0
**Last Updated**: 2025-11-16
**Status**: Production Ready ✅

This guide covers deploying wanLLMDB to production with all security fixes and optimizations from Phases 1-3.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Database Setup](#database-setup)
4. [Redis Setup (Optional)](#redis-setup-optional)
5. [MinIO Setup](#minio-setup)
6. [Application Deployment](#application-deployment)
7. [Security Checklist](#security-checklist)
8. [Performance Tuning](#performance-tuning)
9. [Monitoring & Maintenance](#monitoring--maintenance)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Services
- **PostgreSQL**: 12+ (recommended: 14+)
- **MinIO**: S3-compatible object storage
- **Python**: 3.11+
- **Poetry**: 1.5+ (dependency management)

### Optional Services
- **Redis**: 6+ (for JWT token blacklist)
- **Nginx/Traefik**: Reverse proxy (recommended)

### System Requirements
- **CPU**: 2+ cores
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 20GB+ for application + database
- **Network**: Stable connection for external storage (MinIO/S3)

---

## Environment Configuration

### 1. Create Production `.env` File

```bash
cd backend
cp .env.example .env
```

### 2. Configure Required Variables

**CRITICAL - Security Settings**:

```bash
# Secret key for JWT tokens (MUST be 32+ characters, unique per environment)
SECRET_KEY="your-super-secret-key-min-32-chars-change-in-production"

# Algorithm for JWT (do not change unless you know what you're doing)
ALGORITHM="HS256"

# Token expiration times
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

**Database Configuration**:

```bash
# PostgreSQL connection
DATABASE_URL="postgresql://wanllm:secure_password@localhost:5432/wanllmdb_prod"

# Connection pool settings (optimized for production)
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_RECYCLE=3600
DATABASE_POOL_PRE_PING=true
```

**MinIO Configuration** (REQUIRED - No defaults allowed):

```bash
# MinIO credentials (MUST be 12+ characters, no default values)
# ⚠️  DO NOT use 'minioadmin' or other common values
MINIO_ENDPOINT="minio.example.com:9000"
MINIO_ACCESS_KEY="your-strong-access-key-min-12-chars"
MINIO_SECRET_KEY="your-strong-secret-key-min-12-chars"
MINIO_SECURE=true  # Use HTTPS
MINIO_BUCKET_NAME="wanllmdb-artifacts"
```

**Redis Configuration** (Optional - for token blacklist):

```bash
# Redis for JWT token blacklist (optional but recommended)
REDIS_URL="redis://localhost:6379/0"
```

**CORS Settings**:

```bash
# Frontend origin(s) - comma-separated for multiple
CORS_ORIGINS="https://your-frontend.com,https://app.example.com"
```

### 3. Validate Configuration

**Security Validation** (automated):

```bash
# The application will automatically validate:
# ✓ SECRET_KEY is 32+ characters
# ✓ MINIO_ACCESS_KEY is 12+ characters and not a default value
# ✓ MINIO_SECRET_KEY is 12+ characters and not a default value
# ❌ Application will FAIL TO START if validation fails
```

---

## Database Setup

### 1. Create Production Database

```bash
# As postgres user
sudo -u postgres psql

CREATE DATABASE wanllmdb_prod;
CREATE USER wanllm WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE wanllmdb_prod TO wanllm;

# PostgreSQL 15+ requires additional grants
\c wanllmdb_prod
GRANT ALL ON SCHEMA public TO wanllm;
```

### 2. Run Database Migrations

```bash
cd backend

# Install dependencies
poetry install --no-dev

# Run migrations (includes performance indexes from migration 008)
poetry run alembic upgrade head
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Running upgrade 007 -> 008, Add performance indexes
```

### 3. Verify Migrations

```bash
# Check current revision
poetry run alembic current

# Should show: 008 (head)
```

### 4. Verify Performance Indexes

Connect to database and verify indexes exist:

```sql
-- Check for performance indexes
SELECT tablename, indexname
FROM pg_indexes
WHERE indexname LIKE 'ix_%'
ORDER BY tablename, indexname;

-- Expected indexes:
-- ix_artifact_files_version_path
-- ix_artifact_versions_artifact_created
-- ix_artifacts_name_type
-- ix_artifacts_project_type
-- ix_projects_created_by
-- ix_projects_visibility_created
-- ix_runs_project_created
```

---

## Redis Setup (Optional)

Redis is used for JWT token blacklist. **If Redis is unavailable, the system gracefully degrades** (tokens cannot be revoked but authentication still works).

### Option 1: Local Redis (Development/Small Production)

```bash
# Install Redis
sudo apt-get install redis-server  # Ubuntu/Debian
# OR
brew install redis  # macOS

# Start Redis
sudo systemctl start redis
sudo systemctl enable redis

# Verify
redis-cli ping
# Expected: PONG
```

### Option 2: Redis Cloud/Managed Service (Recommended for Production)

```bash
# Update REDIS_URL in .env
REDIS_URL="redis://username:password@redis-host:6379/0"
```

### Test Redis Integration

```bash
# Test token blacklist functionality
poetry run pytest backend/tests/security/test_jwt_blacklist.py -v
```

---

## MinIO Setup

### Option 1: Self-Hosted MinIO

```bash
# Download MinIO
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/

# Create data directory
sudo mkdir -p /data/minio
sudo chown -R $USER:$USER /data/minio

# Start MinIO with strong credentials
export MINIO_ROOT_USER="your-strong-access-key-min-12-chars"
export MINIO_ROOT_PASSWORD="your-strong-secret-key-min-12-chars"

minio server /data/minio --console-address ":9001"
```

### Option 2: MinIO Docker

```bash
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER="your-strong-access-key" \
  -e MINIO_ROOT_PASSWORD="your-strong-secret-key" \
  -v /data/minio:/data \
  minio/minio server /data --console-address ":9001"
```

### Option 3: AWS S3 / GCS (Cloud Storage)

Update `.env` to use S3-compatible endpoints:

```bash
# AWS S3
MINIO_ENDPOINT="s3.amazonaws.com"
MINIO_ACCESS_KEY="your-aws-access-key"
MINIO_SECRET_KEY="your-aws-secret-key"
MINIO_BUCKET_NAME="your-bucket-name"

# Google Cloud Storage (with S3-compatible API)
MINIO_ENDPOINT="storage.googleapis.com"
```

### Create Bucket

```bash
# Using MinIO client (mc)
mc alias set myminio http://localhost:9000 ACCESS_KEY SECRET_KEY
mc mb myminio/wanllmdb-artifacts

# Set bucket policy (adjust as needed)
mc anonymous set download myminio/wanllmdb-artifacts/public
```

---

## Application Deployment

### 1. Install Dependencies

```bash
cd backend
poetry install --no-dev --no-root
```

### 2. Run Security Tests (Pre-Deployment Validation)

```bash
# Run all security tests
poetry run pytest tests/security/ -v

# Expected: 76 tests passing

# Run security audit
poetry run pytest tests/security/test_security_audit.py -v

# Expected: 22 tests passing, 1 skipped
```

### 3. Run Performance Tests

```bash
poetry run pytest tests/performance/ -v

# Expected: 12 tests passing
```

### 4. Start Application

**Option 1: Direct (Development/Testing)**:

```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Option 2: Production with Gunicorn** (Recommended):

```bash
# Install gunicorn
poetry add gunicorn[uvicorn]

# Start with multiple workers
poetry run gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /var/log/wanllmdb/access.log \
  --error-logfile /var/log/wanllmdb/error.log
```

**Option 3: Systemd Service** (Linux Production):

Create `/etc/systemd/system/wanllmdb.service`:

```ini
[Unit]
Description=wanLLMDB API Service
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=wanllm
Group=wanllm
WorkingDirectory=/opt/wanllmdb/backend
Environment="PATH=/opt/wanllmdb/backend/.venv/bin"
ExecStart=/opt/wanllmdb/backend/.venv/bin/gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable wanllmdb
sudo systemctl start wanllmdb
sudo systemctl status wanllmdb
```

### 5. Configure Reverse Proxy (Nginx Example)

```nginx
# /etc/nginx/sites-available/wanllmdb
server {
    listen 443 ssl http2;
    server_name api.wanllmdb.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/api.wanllmdb.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.wanllmdb.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # Rate limiting (additional layer to API rate limiting)
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

---

## Security Checklist

Before going to production, verify ALL items:

- [ ] **Strong SECRET_KEY configured** (32+ characters, unique)
- [ ] **No default MinIO credentials** (validation enforced)
- [ ] **Database password is strong** and not exposed
- [ ] **HTTPS/TLS enabled** (via reverse proxy)
- [ ] **CORS origins configured** (not set to "*")
- [ ] **Redis password set** (if using Redis)
- [ ] **MinIO/S3 access restricted** (not public buckets)
- [ ] **Security tests passing** (76/76 tests)
- [ ] **Security audit passing** (22/23 tests)
- [ ] **Firewall configured** (only necessary ports open)
- [ ] **Rate limiting active** (slowapi + optional nginx layer)
- [ ] **Log rotation configured** (prevent disk fill)
- [ ] **Backup strategy in place** (database + object storage)

---

## Performance Tuning

### Database Connection Pool (Already Optimized)

Current settings (from Phase 2):
```
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_RECYCLE=3600
DATABASE_POOL_PRE_PING=true
```

**Adjust based on load**:
- Small deployment (< 100 concurrent users): 20 + 10
- Medium deployment (< 500 concurrent users): 50 + 20 (current)
- Large deployment (> 500 concurrent users): 100 + 50

### Worker Count (Gunicorn)

Formula: `(2 x CPU cores) + 1`

Examples:
- 2 cores: 5 workers
- 4 cores: 9 workers
- 8 cores: 17 workers

### PostgreSQL Tuning

```sql
-- Check current connections
SELECT count(*) FROM pg_stat_activity;

-- Recommended postgresql.conf settings for production
max_connections = 200
shared_buffers = 2GB  -- 25% of RAM
effective_cache_size = 6GB  -- 75% of RAM
maintenance_work_mem = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1  -- For SSD
effective_io_concurrency = 200  -- For SSD
work_mem = 10MB
min_wal_size = 1GB
max_wal_size = 4GB
```

---

## Monitoring & Maintenance

### Health Check Endpoint

```bash
curl http://localhost:8000/health
# Expected: 200 OK
```

### Monitor Logs

```bash
# Application logs
tail -f /var/log/wanllmdb/error.log

# Nginx logs
tail -f /var/log/nginx/access.log

# System journal
journalctl -u wanllmdb -f
```

### Database Maintenance

```sql
-- Monitor active connections
SELECT count(*), state FROM pg_stat_activity GROUP BY state;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan;

-- Vacuum and analyze (run weekly)
VACUUM ANALYZE;
```

### Redis Monitoring (if enabled)

```bash
# Check token blacklist size
redis-cli DBSIZE

# Monitor memory usage
redis-cli INFO memory

# Check keys with pattern
redis-cli KEYS "blacklist:*" | wc -l
```

---

## Troubleshooting

### Issue: Application Fails to Start

**Error**: "MINIO_ACCESS_KEY cannot be a default/weak value"

**Solution**: Update `.env` with strong credentials (12+ characters, not 'minioadmin')

---

**Error**: "SECRET_KEY must be at least 32 characters"

**Solution**: Generate strong secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

### Issue: Database Connection Pool Exhausted

**Symptoms**: "QueuePool limit of size X overflow Y reached"

**Solutions**:
1. Increase pool size: `DATABASE_POOL_SIZE=100`
2. Increase overflow: `DATABASE_MAX_OVERFLOW=50`
3. Check for connection leaks in code
4. Monitor with: `SELECT count(*) FROM pg_stat_activity;`

---

### Issue: Redis Connection Failed

**Symptoms**: "Warning: Redis connection failed"

**Impact**: Token blacklist disabled, logout functionality degraded

**Solutions**:
1. Start Redis: `sudo systemctl start redis`
2. Check Redis URL in `.env`
3. Verify Redis is accessible: `redis-cli ping`
4. **Note**: Application continues to work without Redis (graceful degradation)

---

### Issue: Slow Query Performance

**Symptoms**: API endpoints taking > 500ms

**Diagnosis**:
```bash
# Run performance tests
poetry run pytest tests/performance/ -v

# Check if indexes exist
psql -d wanllmdb_prod -c "\di"
```

**Solutions**:
1. Ensure migration 008 (performance indexes) was run
2. Run `VACUUM ANALYZE` on database
3. Check query plans: `EXPLAIN ANALYZE SELECT ...`
4. Verify N+1 query fixes are active

---

### Issue: Rate Limiting Too Aggressive

**Symptoms**: Users getting 429 errors frequently

**Solutions**:
1. Adjust rate limits in `backend/app/api/v1/auth.py`:
   ```python
   @limiter.limit("10/minute")  # Increase from 5/minute
   ```
2. Consider per-user rate limiting instead of per-IP
3. Add rate limit exception handling for specific IPs

---

## Support & Documentation

- **Security Fixes**: See `SECURITY_FIXES_IMPLEMENTED.md`
- **Test Documentation**: See `TESTING.md` (generated)
- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Code Review**: See `PHASE_1_2_CODE_REVIEW.md`

---

**Deployment Status**: ✅ Ready for Production
**Last Security Audit**: 2025-11-16 (PASS)
**Last Performance Test**: 2025-11-16 (PASS)
