#!/bin/bash
#
# Production Deployment Script for wanLLMDB
#
# Deploys or updates wanLLMDB in a production environment.
#
# Usage:
#   ./deploy-production.sh [OPTIONS]
#
# Options:
#   --initial       Initial deployment (creates database, runs migrations)
#   --update        Update deployment (pulls latest, restarts services)
#   --rollback      Rollback to previous version
#   --help          Show this help message
#

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INITIAL_DEPLOY=false
UPDATE_DEPLOY=false
ROLLBACK_DEPLOY=false

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
Production Deployment Script for wanLLMDB

Usage: $0 [OPTIONS]

Options:
  --initial       Initial deployment (first-time setup)
  --update        Update existing deployment
  --rollback      Rollback to previous version
  --help          Show this help message

Examples:
  # Initial deployment
  $0 --initial

  # Update deployment
  $0 --update

  # Rollback deployment
  $0 --rollback

Prerequisites:
  - Docker and Docker Compose installed
  - .env.production file configured
  - Git repository cloned
  - Port 8000 available

EOF
}

check_prerequisites() {
    log "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker not installed"
        exit 1
    fi
    log "✓ Docker installed: $(docker --version | head -n1)"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose not installed"
        exit 1
    fi
    log "✓ Docker Compose installed"

    # Check .env.production exists
    if [ ! -f "${PROJECT_ROOT}/.env.production" ]; then
        error ".env.production file not found"
        error "Copy .env.production.example to .env.production and configure it"
        exit 1
    fi
    log "✓ .env.production file found"

    # Check required environment variables
    set -a
    source "${PROJECT_ROOT}/.env.production"
    set +a

    if [ -z "${SECRET_KEY:-}" ] || [ "${SECRET_KEY}" = "CHANGE_THIS_TO_STRONG_SECRET_MIN_32_CHARS_GENERATE_UNIQUE_VALUE" ]; then
        error "SECRET_KEY not configured in .env.production"
        exit 1
    fi

    if [ -z "${POSTGRES_PASSWORD:-}" ] || [ "${POSTGRES_PASSWORD}" = "CHANGE_THIS_TO_STRONG_DATABASE_PASSWORD" ]; then
        error "POSTGRES_PASSWORD not configured in .env.production"
        exit 1
    fi

    log "✓ Environment variables validated"
}

# ============================================================================
# Parse Arguments
# ============================================================================

if [ $# -eq 0 ]; then
    error "No deployment type specified"
    show_help
    exit 1
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        --initial)
            INITIAL_DEPLOY=true
            shift
            ;;
        --update)
            UPDATE_DEPLOY=true
            shift
            ;;
        --rollback)
            ROLLBACK_DEPLOY=true
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
# Initial Deployment
# ============================================================================

if [ "$INITIAL_DEPLOY" = true ]; then
    log "=================================================="
    log "Starting INITIAL deployment..."
    log "=================================================="

    check_prerequisites

    cd "${PROJECT_ROOT}"

    # Copy environment file
    log "Setting up environment..."
    cp .env.production backend/.env

    # Build Docker images
    log "Building Docker images..."
    docker-compose -f docker-compose.prod.yml build

    # Start services
    log "Starting services..."
    docker-compose -f docker-compose.prod.yml up -d postgres redis minio

    # Wait for database to be ready
    log "Waiting for PostgreSQL to be ready..."
    sleep 10
    docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U wanllm || true
    sleep 5

    # Create MinIO bucket
    log "Setting up MinIO bucket..."
    docker-compose -f docker-compose.prod.yml exec -T minio \
        mc alias set local http://localhost:9000 "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" || true
    docker-compose -f docker-compose.prod.yml exec -T minio \
        mc mb local/"${MINIO_BUCKET_NAME}" || true

    # Run database migrations
    log "Running database migrations..."
    docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

    # Start backend
    log "Starting backend service..."
    docker-compose -f docker-compose.prod.yml up -d backend

    # Wait for backend to be ready
    log "Waiting for backend to be ready..."
    sleep 10

    # Health check
    log "Running health check..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            log "✓ Backend is healthy"
            break
        fi
        if [ $i -eq 30 ]; then
            error "Backend health check failed"
            docker-compose -f docker-compose.prod.yml logs backend
            exit 1
        fi
        sleep 2
    done

    log "=================================================="
    log "✓ Initial deployment completed successfully!"
    log "=================================================="
    log ""
    log "Services:"
    docker-compose -f docker-compose.prod.yml ps
    log ""
    log "Next steps:"
    log "1. Access API at: http://localhost:8000"
    log "2. View API docs at: http://localhost:8000/docs"
    log "3. Set up Nginx reverse proxy (see PRODUCTION_DEPLOYMENT.md)"
    log "4. Configure backups (see scripts/README.md)"
    log "5. Set up monitoring and alerting"
fi

# ============================================================================
# Update Deployment
# ============================================================================

if [ "$UPDATE_DEPLOY" = true ]; then
    log "=================================================="
    log "Starting UPDATE deployment..."
    log "=================================================="

    check_prerequisites

    cd "${PROJECT_ROOT}"

    # Create backup before update
    log "Creating pre-update backup..."
    if [ -f "backend/scripts/backup-database.sh" ]; then
        cd backend/scripts
        ./backup-database.sh --local-only
        cd "${PROJECT_ROOT}"
    else
        log "⚠️  Warning: Backup script not found, skipping backup"
    fi

    # Pull latest code (if using Git)
    if [ -d ".git" ]; then
        log "Pulling latest code..."
        git pull
    fi

    # Rebuild Docker images
    log "Rebuilding Docker images..."
    docker-compose -f docker-compose.prod.yml build backend

    # Run database migrations
    log "Running database migrations..."
    docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

    # Restart backend with zero-downtime (if possible)
    log "Restarting backend service..."
    docker-compose -f docker-compose.prod.yml up -d backend

    # Wait for new backend to be ready
    log "Waiting for updated backend to be ready..."
    sleep 10

    # Health check
    log "Running health check..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            log "✓ Backend is healthy"
            break
        fi
        if [ $i -eq 30 ]; then
            error "Backend health check failed"
            docker-compose -f docker-compose.prod.yml logs backend --tail=50
            exit 1
        fi
        sleep 2
    done

    # Cleanup old images
    log "Cleaning up old Docker images..."
    docker image prune -f

    log "=================================================="
    log "✓ Update deployment completed successfully!"
    log "=================================================="
    log ""
    log "Services:"
    docker-compose -f docker-compose.prod.yml ps
fi

# ============================================================================
# Rollback Deployment
# ============================================================================

if [ "$ROLLBACK_DEPLOY" = true ]; then
    log "=================================================="
    log "Starting ROLLBACK deployment..."
    log "=================================================="

    check_prerequisites

    cd "${PROJECT_ROOT}"

    # List available backups
    log "Available backups:"
    ls -lh backend/scripts/backups/pre_restore_*.sql.gz 2>/dev/null || echo "No backups found"

    # Ask user to select backup
    read -p "Enter backup filename to restore (or 'cancel' to abort): " BACKUP_FILE

    if [ "$BACKUP_FILE" = "cancel" ]; then
        log "Rollback cancelled"
        exit 0
    fi

    # Restore database
    log "Restoring database from backup..."
    cd backend/scripts
    ./restore-database.sh "$BACKUP_FILE" --force
    cd "${PROJECT_ROOT}"

    # Restart services
    log "Restarting services..."
    docker-compose -f docker-compose.prod.yml restart backend

    # Health check
    log "Running health check..."
    sleep 10
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "✓ Backend is healthy after rollback"
    else
        error "Backend health check failed after rollback"
        exit 1
    fi

    log "=================================================="
    log "✓ Rollback completed successfully!"
    log "=================================================="
fi

exit 0
