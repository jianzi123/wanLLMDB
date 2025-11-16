#!/bin/bash
#
# Database Backup Script for wanLLMDB
#
# Creates a compressed backup of the PostgreSQL database.
# Supports both local and remote backups to S3-compatible storage.
#
# Usage:
#   ./backup-database.sh [OPTIONS]
#
# Options:
#   --local-only    Only create local backup (skip S3 upload)
#   --retention N   Keep last N backups (default: 7)
#   --help          Show this help message
#

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# ============================================================================
# Configuration
# ============================================================================

# Load environment variables from .env if it exists
if [ -f ../.env ]; then
    set -a
    source ../.env
    set +a
fi

# Defaults
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="wanllmdb_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"
LOCAL_ONLY=false

# Database configuration (from environment or .env)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-wanllmdb}"
DB_USER="${POSTGRES_USER:-wanllm}"
DB_PASSWORD="${POSTGRES_PASSWORD:-}"

# S3/MinIO configuration (optional)
S3_BUCKET="${MINIO_BUCKET_NAME:-wanllmdb-backups}"
S3_ENDPOINT="${MINIO_ENDPOINT:-}"
S3_ACCESS_KEY="${MINIO_ACCESS_KEY:-}"
S3_SECRET_KEY="${MINIO_SECRET_KEY:-}"

# ============================================================================
# Helper Functions
# ============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

show_help() {
    cat << EOF
Database Backup Script for wanLLMDB

Usage: $0 [OPTIONS]

Options:
  --local-only    Only create local backup (skip S3 upload)
  --retention N   Keep last N backups (default: 7)
  --help          Show this help message

Environment Variables:
  POSTGRES_DB            Database name (default: wanllmdb)
  POSTGRES_USER          Database user (default: wanllm)
  POSTGRES_PASSWORD      Database password (required)
  DB_HOST                Database host (default: localhost)
  DB_PORT                Database port (default: 5432)
  BACKUP_DIR             Backup directory (default: ./backups)
  BACKUP_RETENTION_DAYS  Number of days to keep backups (default: 7)
  MINIO_BUCKET_NAME      S3 bucket for remote backups
  MINIO_ENDPOINT         S3 endpoint URL
  MINIO_ACCESS_KEY       S3 access key
  MINIO_SECRET_KEY       S3 secret key

Example:
  # Local backup only
  $0 --local-only

  # Backup with custom retention
  $0 --retention 14

  # Backup to S3
  export MINIO_BUCKET_NAME=wanllmdb-backups
  export MINIO_ENDPOINT=minio.example.com:9000
  $0

EOF
}

# ============================================================================
# Parse Arguments
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --local-only)
            LOCAL_ONLY=true
            shift
            ;;
        --retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# ============================================================================
# Validation
# ============================================================================

# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null; then
    error "pg_dump not found. Please install PostgreSQL client tools."
    exit 1
fi

# Check if database password is set
if [ -z "$DB_PASSWORD" ]; then
    error "POSTGRES_PASSWORD environment variable is not set"
    exit 1
fi

# ============================================================================
# Create Backup
# ============================================================================

log "Starting database backup..."
log "Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
log "Backup file: ${BACKUP_PATH}"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Set password for pg_dump
export PGPASSWORD="${DB_PASSWORD}"

# Create backup with pg_dump
log "Creating database dump..."
if pg_dump \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --username="${DB_USER}" \
    --dbname="${DB_NAME}" \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    | gzip > "${BACKUP_PATH}"; then
    log "✓ Database backup created successfully"
else
    error "Failed to create database backup"
    exit 1
fi

# Unset password
unset PGPASSWORD

# Get backup size
BACKUP_SIZE=$(du -h "${BACKUP_PATH}" | cut -f1)
log "Backup size: ${BACKUP_SIZE}"

# ============================================================================
# Create Metadata File
# ============================================================================

METADATA_FILE="${BACKUP_PATH}.meta"
cat > "${METADATA_FILE}" << EOF
{
  "timestamp": "${TIMESTAMP}",
  "database": "${DB_NAME}",
  "host": "${DB_HOST}",
  "port": "${DB_PORT}",
  "size": "${BACKUP_SIZE}",
  "file": "${BACKUP_FILE}",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

log "✓ Metadata file created: ${METADATA_FILE}"

# ============================================================================
# Upload to S3/MinIO (if configured)
# ============================================================================

if [ "$LOCAL_ONLY" = false ] && [ -n "$S3_ENDPOINT" ]; then
    log "Uploading backup to S3..."

    # Check if AWS CLI or MinIO client (mc) is available
    if command -v aws &> /dev/null; then
        log "Using AWS CLI for S3 upload..."

        # Configure AWS CLI
        export AWS_ACCESS_KEY_ID="${S3_ACCESS_KEY}"
        export AWS_SECRET_ACCESS_KEY="${S3_SECRET_KEY}"
        export AWS_ENDPOINT_URL="https://${S3_ENDPOINT}"

        # Upload backup file
        if aws s3 cp "${BACKUP_PATH}" "s3://${S3_BUCKET}/backups/${BACKUP_FILE}"; then
            log "✓ Backup uploaded to S3: s3://${S3_BUCKET}/backups/${BACKUP_FILE}"
        else
            error "Failed to upload backup to S3"
        fi

        # Upload metadata file
        aws s3 cp "${METADATA_FILE}" "s3://${S3_BUCKET}/backups/${BACKUP_FILE}.meta" || true

        # Cleanup
        unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_ENDPOINT_URL

    elif command -v mc &> /dev/null; then
        log "Using MinIO client for S3 upload..."

        # Configure MinIO client alias
        mc alias set wanllmdb "https://${S3_ENDPOINT}" "${S3_ACCESS_KEY}" "${S3_SECRET_KEY}" > /dev/null

        # Upload backup file
        if mc cp "${BACKUP_PATH}" "wanllmdb/${S3_BUCKET}/backups/${BACKUP_FILE}"; then
            log "✓ Backup uploaded to MinIO: ${S3_BUCKET}/backups/${BACKUP_FILE}"
        else
            error "Failed to upload backup to MinIO"
        fi

        # Upload metadata file
        mc cp "${METADATA_FILE}" "wanllmdb/${S3_BUCKET}/backups/${BACKUP_FILE}.meta" || true

    else
        error "Neither aws nor mc (MinIO client) found. Skipping S3 upload."
        error "Install AWS CLI (aws) or MinIO client (mc) to enable S3 uploads."
    fi
fi

# ============================================================================
# Cleanup Old Backups
# ============================================================================

log "Cleaning up old backups (retention: ${RETENTION_DAYS} days)..."

# Delete local backups older than retention period
find "${BACKUP_DIR}" -name "wanllmdb_backup_*.sql.gz" -type f -mtime +"${RETENTION_DAYS}" -delete
find "${BACKUP_DIR}" -name "wanllmdb_backup_*.sql.gz.meta" -type f -mtime +"${RETENTION_DAYS}" -delete

REMAINING_BACKUPS=$(find "${BACKUP_DIR}" -name "wanllmdb_backup_*.sql.gz" -type f | wc -l)
log "✓ Local cleanup complete. Remaining backups: ${REMAINING_BACKUPS}"

# ============================================================================
# Summary
# ============================================================================

log "=================================================="
log "Backup Summary"
log "=================================================="
log "Backup file:  ${BACKUP_PATH}"
log "Backup size:  ${BACKUP_SIZE}"
log "Timestamp:    ${TIMESTAMP}"
log "Retention:    ${RETENTION_DAYS} days"
if [ "$LOCAL_ONLY" = false ] && [ -n "$S3_ENDPOINT" ]; then
    log "S3 upload:    ✓ Completed"
else
    log "S3 upload:    Skipped"
fi
log "=================================================="
log "✓ Backup completed successfully"

exit 0
