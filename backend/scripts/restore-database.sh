#!/bin/bash
#
# Database Restore Script for wanLLMDB
#
# Restores a PostgreSQL database from a compressed backup file.
# Can restore from local backup or download from S3/MinIO.
#
# Usage:
#   ./restore-database.sh BACKUP_FILE [OPTIONS]
#
# Options:
#   --from-s3       Download backup from S3 before restoring
#   --force         Skip confirmation prompt
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
FROM_S3=false
FORCE=false
BACKUP_FILE=""

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
Database Restore Script for wanLLMDB

Usage: $0 BACKUP_FILE [OPTIONS]

Arguments:
  BACKUP_FILE     Name of the backup file to restore (e.g., wanllmdb_backup_20250116_120000.sql.gz)

Options:
  --from-s3       Download backup from S3 before restoring
  --force         Skip confirmation prompt (DANGEROUS)
  --help          Show this help message

Environment Variables:
  POSTGRES_DB            Database name (default: wanllmdb)
  POSTGRES_USER          Database user (default: wanllm)
  POSTGRES_PASSWORD      Database password (required)
  DB_HOST                Database host (default: localhost)
  DB_PORT                Database port (default: 5432)
  BACKUP_DIR             Backup directory (default: ./backups)
  MINIO_BUCKET_NAME      S3 bucket for remote backups
  MINIO_ENDPOINT         S3 endpoint URL
  MINIO_ACCESS_KEY       S3 access key
  MINIO_SECRET_KEY       S3 secret key

Examples:
  # Restore from local backup
  $0 wanllmdb_backup_20250116_120000.sql.gz

  # Restore from S3 backup
  $0 wanllmdb_backup_20250116_120000.sql.gz --from-s3

  # Force restore without confirmation
  $0 wanllmdb_backup_20250116_120000.sql.gz --force

WARNING:
  This script will DROP and RECREATE the database, destroying all existing data.
  Make sure you have a current backup before proceeding!

EOF
}

confirm() {
    if [ "$FORCE" = true ]; then
        return 0
    fi

    echo ""
    echo "⚠️  WARNING: This will DROP and RECREATE the database!"
    echo "⚠️  All existing data will be LOST!"
    echo ""
    echo "Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
    echo "Backup:   ${BACKUP_FILE}"
    echo ""
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation

    if [ "$confirmation" != "yes" ]; then
        log "Restore cancelled by user"
        exit 0
    fi
}

# ============================================================================
# Parse Arguments
# ============================================================================

if [ $# -eq 0 ]; then
    error "No backup file specified"
    show_help
    exit 1
fi

BACKUP_FILE="$1"
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        --from-s3)
            FROM_S3=true
            shift
            ;;
        --force)
            FORCE=true
            shift
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

# Check if psql is available
if ! command -v psql &> /dev/null; then
    error "psql not found. Please install PostgreSQL client tools."
    exit 1
fi

# Check if database password is set
if [ -z "$DB_PASSWORD" ]; then
    error "POSTGRES_PASSWORD environment variable is not set"
    exit 1
fi

# ============================================================================
# Download from S3 (if requested)
# ============================================================================

BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

if [ "$FROM_S3" = true ]; then
    log "Downloading backup from S3..."

    mkdir -p "${BACKUP_DIR}"

    # Check if AWS CLI or MinIO client (mc) is available
    if command -v aws &> /dev/null; then
        log "Using AWS CLI for S3 download..."

        export AWS_ACCESS_KEY_ID="${S3_ACCESS_KEY}"
        export AWS_SECRET_ACCESS_KEY="${S3_SECRET_KEY}"
        export AWS_ENDPOINT_URL="https://${S3_ENDPOINT}"

        if aws s3 cp "s3://${S3_BUCKET}/backups/${BACKUP_FILE}" "${BACKUP_PATH}"; then
            log "✓ Backup downloaded from S3"
        else
            error "Failed to download backup from S3"
            exit 1
        fi

        unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_ENDPOINT_URL

    elif command -v mc &> /dev/null; then
        log "Using MinIO client for S3 download..."

        mc alias set wanllmdb "https://${S3_ENDPOINT}" "${S3_ACCESS_KEY}" "${S3_SECRET_KEY}" > /dev/null

        if mc cp "wanllmdb/${S3_BUCKET}/backups/${BACKUP_FILE}" "${BACKUP_PATH}"; then
            log "✓ Backup downloaded from MinIO"
        else
            error "Failed to download backup from MinIO"
            exit 1
        fi

    else
        error "Neither aws nor mc (MinIO client) found"
        exit 1
    fi
fi

# ============================================================================
# Verify Backup File Exists
# ============================================================================

if [ ! -f "${BACKUP_PATH}" ]; then
    error "Backup file not found: ${BACKUP_PATH}"
    error "Available backups:"
    ls -lh "${BACKUP_DIR}"/wanllmdb_backup_*.sql.gz 2>/dev/null || echo "  (none)"
    exit 1
fi

log "Found backup file: ${BACKUP_PATH}"
BACKUP_SIZE=$(du -h "${BACKUP_PATH}" | cut -f1)
log "Backup size: ${BACKUP_SIZE}"

# ============================================================================
# Confirmation
# ============================================================================

confirm

# ============================================================================
# Create Pre-Restore Backup
# ============================================================================

log "Creating pre-restore backup of current database..."

PRERESTORE_BACKUP="${BACKUP_DIR}/pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"

export PGPASSWORD="${DB_PASSWORD}"

if pg_dump \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --username="${DB_USER}" \
    --dbname="${DB_NAME}" \
    --no-owner \
    --no-acl \
    2>/dev/null | gzip > "${PRERESTORE_BACKUP}"; then
    log "✓ Pre-restore backup created: ${PRERESTORE_BACKUP}"
else
    log "⚠️  Warning: Could not create pre-restore backup (database may not exist)"
fi

# ============================================================================
# Restore Database
# ============================================================================

log "Starting database restore..."

# Restore from backup
log "Restoring database from backup..."

if gunzip -c "${BACKUP_PATH}" | psql \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --username="${DB_USER}" \
    --dbname="${DB_NAME}" \
    --quiet; then
    log "✓ Database restored successfully"
else
    error "Failed to restore database"
    error "You can restore the pre-restore backup if needed: ${PRERESTORE_BACKUP}"
    exit 1
fi

unset PGPASSWORD

# ============================================================================
# Run Migrations (if alembic is available)
# ============================================================================

if [ -f "../alembic.ini" ]; then
    log "Running database migrations..."
    cd ..
    if command -v poetry &> /dev/null; then
        if poetry run alembic upgrade head; then
            log "✓ Database migrations completed"
        else
            error "Failed to run migrations"
        fi
    else
        log "⚠️  Poetry not found, skipping migrations"
    fi
    cd scripts
fi

# ============================================================================
# Verify Restore
# ============================================================================

log "Verifying restored database..."

export PGPASSWORD="${DB_PASSWORD}"

# Count tables
TABLE_COUNT=$(psql \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --username="${DB_USER}" \
    --dbname="${DB_NAME}" \
    --tuples-only \
    --command="SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" \
    | tr -d ' ')

log "Tables found: ${TABLE_COUNT}"

unset PGPASSWORD

if [ "$TABLE_COUNT" -gt 0 ]; then
    log "✓ Database verification successful"
else
    error "Database appears to be empty after restore"
    exit 1
fi

# ============================================================================
# Summary
# ============================================================================

log "=================================================="
log "Restore Summary"
log "=================================================="
log "Database:         ${DB_NAME}@${DB_HOST}:${DB_PORT}"
log "Backup file:      ${BACKUP_FILE}"
log "Backup size:      ${BACKUP_SIZE}"
log "Tables restored:  ${TABLE_COUNT}"
log "Pre-restore backup: ${PRERESTORE_BACKUP}"
log "=================================================="
log "✓ Restore completed successfully"

exit 0
