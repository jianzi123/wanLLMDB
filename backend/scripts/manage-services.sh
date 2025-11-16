#!/bin/bash
#
# Service Management Script for wanLLMDB
#
# Manages wanLLMDB services in production.
#
# Usage:
#   ./manage-services.sh COMMAND [SERVICE]
#
# Commands:
#   start       Start services
#   stop        Stop services
#   restart     Restart services
#   status      Show service status
#   logs        Show service logs
#   ps          List running containers
#   help        Show this help message
#

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"

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
Service Management Script for wanLLMDB

Usage: $0 COMMAND [SERVICE]

Commands:
  start       Start all services or specific service
  stop        Stop all services or specific service
  restart     Restart all services or specific service
  status      Show service status and health
  logs        Show service logs (follows by default)
  ps          List running containers
  exec        Execute command in container
  shell       Open shell in container
  health      Run health checks
  help        Show this help message

Services:
  backend     FastAPI backend application
  postgres    PostgreSQL database
  redis       Redis cache
  minio       MinIO object storage
  nginx       Nginx reverse proxy (if configured)

Examples:
  # Start all services
  $0 start

  # Start only backend
  $0 start backend

  # Stop all services
  $0 stop

  # Restart backend
  $0 restart backend

  # View logs (all services)
  $0 logs

  # View backend logs only
  $0 logs backend

  # View last 50 lines of backend logs
  $0 logs backend 50

  # Show service status
  $0 status

  # Execute command in backend
  $0 exec backend alembic current

  # Open shell in backend
  $0 shell backend

  # Run health checks
  $0 health

EOF
}

check_compose() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        error "docker-compose.prod.yml not found"
        exit 1
    fi
}

# ============================================================================
# Commands
# ============================================================================

cmd_start() {
    local service="${1:-}"

    log "Starting services..."
    cd "$PROJECT_ROOT"

    if [ -z "$service" ]; then
        docker-compose -f docker-compose.prod.yml up -d
        log "✓ All services started"
    else
        docker-compose -f docker-compose.prod.yml up -d "$service"
        log "✓ Service '$service' started"
    fi

    log ""
    log "Service status:"
    docker-compose -f docker-compose.prod.yml ps
}

cmd_stop() {
    local service="${1:-}"

    log "Stopping services..."
    cd "$PROJECT_ROOT"

    if [ -z "$service" ]; then
        docker-compose -f docker-compose.prod.yml down
        log "✓ All services stopped"
    else
        docker-compose -f docker-compose.prod.yml stop "$service"
        log "✓ Service '$service' stopped"
    fi
}

cmd_restart() {
    local service="${1:-}"

    log "Restarting services..."
    cd "$PROJECT_ROOT"

    if [ -z "$service" ]; then
        docker-compose -f docker-compose.prod.yml restart
        log "✓ All services restarted"
    else
        docker-compose -f docker-compose.prod.yml restart "$service"
        log "✓ Service '$service' restarted"
    fi

    log ""
    log "Service status:"
    docker-compose -f docker-compose.prod.yml ps
}

cmd_status() {
    cd "$PROJECT_ROOT"

    log "Service status:"
    log ""
    docker-compose -f docker-compose.prod.yml ps

    log ""
    log "Resource usage:"
    docker stats --no-stream $(docker-compose -f docker-compose.prod.yml ps -q) 2>/dev/null || true
}

cmd_logs() {
    local service="${1:-}"
    local lines="${2:-}"

    cd "$PROJECT_ROOT"

    if [ -z "$service" ]; then
        if [ -z "$lines" ]; then
            docker-compose -f docker-compose.prod.yml logs -f
        else
            docker-compose -f docker-compose.prod.yml logs -f --tail="$lines"
        fi
    else
        if [ -z "$lines" ]; then
            docker-compose -f docker-compose.prod.yml logs -f "$service"
        else
            docker-compose -f docker-compose.prod.yml logs -f --tail="$lines" "$service"
        fi
    fi
}

cmd_ps() {
    cd "$PROJECT_ROOT"

    log "Running containers:"
    log ""
    docker-compose -f docker-compose.prod.yml ps
}

cmd_exec() {
    local service="${1:-}"
    shift

    if [ -z "$service" ]; then
        error "Service name required"
        show_help
        exit 1
    fi

    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.prod.yml exec "$service" "$@"
}

cmd_shell() {
    local service="${1:-backend}"

    cd "$PROJECT_ROOT"

    log "Opening shell in $service..."
    docker-compose -f docker-compose.prod.yml exec "$service" /bin/bash
}

cmd_health() {
    cd "$PROJECT_ROOT"

    log "Running health checks..."
    log ""

    # Backend health
    log "Backend health check:"
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "  ✓ Backend is healthy"
        curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health
    else
        error "  ✗ Backend is unhealthy"
    fi

    log ""

    # Backend readiness
    log "Backend readiness check:"
    if curl -f http://localhost:8000/health/ready > /dev/null 2>&1; then
        log "  ✓ Backend is ready"
    else
        error "  ✗ Backend is not ready"
    fi

    log ""

    # Database health
    log "Database health check:"
    if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U wanllm > /dev/null 2>&1; then
        log "  ✓ PostgreSQL is healthy"
    else
        error "  ✗ PostgreSQL is unhealthy"
    fi

    log ""

    # Redis health
    log "Redis health check:"
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
        log "  ✓ Redis is healthy"
    else
        error "  ✗ Redis is unhealthy"
    fi

    log ""

    # MinIO health
    log "MinIO health check:"
    if curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        log "  ✓ MinIO is healthy"
    else
        error "  ✗ MinIO is unhealthy"
    fi

    log ""
    log "Health check completed"
}

# ============================================================================
# Main
# ============================================================================

if [ $# -eq 0 ]; then
    error "No command specified"
    show_help
    exit 1
fi

check_compose

COMMAND="$1"
shift

case "$COMMAND" in
    start)
        cmd_start "$@"
        ;;
    stop)
        cmd_stop "$@"
        ;;
    restart)
        cmd_restart "$@"
        ;;
    status)
        cmd_status "$@"
        ;;
    logs)
        cmd_logs "$@"
        ;;
    ps)
        cmd_ps "$@"
        ;;
    exec)
        cmd_exec "$@"
        ;;
    shell)
        cmd_shell "$@"
        ;;
    health)
        cmd_health "$@"
        ;;
    help|--help|-h)
        show_help
        exit 0
        ;;
    *)
        error "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac

exit 0
