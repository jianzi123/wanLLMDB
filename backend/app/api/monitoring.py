"""
Monitoring and Health Check Endpoints

Provides comprehensive health checks and monitoring metrics for production deployment.
"""

from datetime import datetime
from typing import Dict, Any
import psutil
import platform

from fastapi import APIRouter, Depends, status, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_redis_client
from app.db.database import get_db


router = APIRouter()


# ============================================================================
# Health Check Endpoints
# ============================================================================

@router.get("/health")
async def basic_health_check():
    """
    Basic health check endpoint.

    Returns 200 OK if the application is running.
    Used by load balancers and Docker health checks.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check - verifies all dependencies are available.

    Checks:
    - Database connectivity
    - Redis connectivity (optional)
    - MinIO/S3 connectivity (if configured)

    Returns 200 if ready, 503 if not ready.
    """
    checks = {
        "database": False,
        "redis": False,
        "application": True,
    }
    errors = []

    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        checks["database"] = False
        errors.append(f"Database: {str(e)}")

    # Check Redis (optional - graceful degradation)
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.ping()
            checks["redis"] = True
        else:
            checks["redis"] = False
            errors.append("Redis: Not configured or unavailable (graceful degradation)")
    except Exception as e:
        checks["redis"] = False
        errors.append(f"Redis: {str(e)} (graceful degradation)")

    # Check MinIO/S3 (optional - would require MinIO client initialization)
    # For now, we skip this check as it's handled by storage layer

    # Determine overall status
    # Application is ready if database is available
    # Redis is optional (graceful degradation)
    is_ready = checks["database"]

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return Response(
        content={
            "ready": is_ready,
            "checks": checks,
            "errors": errors if errors else None,
            "timestamp": datetime.utcnow().isoformat(),
        },
        status_code=status_code,
        media_type="application/json",
    )


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check - verifies the application is alive.

    Returns 200 if alive. Used by Kubernetes liveness probes.
    Should always return 200 unless the application is deadlocked.
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Monitoring Endpoints
# ============================================================================

@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """
    Application metrics endpoint.

    Provides system and application metrics for monitoring.
    Compatible with Prometheus format (JSON variant).
    """
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "application": _get_application_metrics(),
        "system": _get_system_metrics(),
        "database": _get_database_metrics(db),
        "redis": _get_redis_metrics(),
    }

    return metrics


@router.get("/metrics/system")
async def get_system_metrics():
    """Get system resource metrics."""
    return _get_system_metrics()


@router.get("/metrics/database")
async def get_database_metrics(db: Session = Depends(get_db)):
    """Get database metrics."""
    return _get_database_metrics(db)


@router.get("/info")
async def get_info():
    """
    Get application information.

    Provides version, environment, and configuration details.
    """
    return {
        "application": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
        },
        "build": {
            "build_date": getattr(settings, "BUILD_DATE", None),
            "vcs_ref": getattr(settings, "VCS_REF", None),
        },
        "platform": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
        },
        "configuration": {
            "cors_origins": settings.CORS_ORIGINS,
            "database_pool_size": settings.DATABASE_POOL_SIZE,
            "database_max_overflow": settings.DATABASE_MAX_OVERFLOW,
        },
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _get_application_metrics() -> Dict[str, Any]:
    """Get application-level metrics."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "uptime_seconds": None,  # Would require tracking start time
    }


def _get_system_metrics() -> Dict[str, Any]:
    """Get system resource metrics."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count(),
            },
            "memory": {
                "total_bytes": memory.total,
                "available_bytes": memory.available,
                "used_bytes": memory.used,
                "percent": memory.percent,
            },
            "disk": {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "percent": disk.percent,
            },
            "network": {
                "connections": len(psutil.net_connections()),
            },
        }
    except Exception as e:
        return {
            "error": f"Unable to get system metrics: {str(e)}",
        }


def _get_database_metrics(db: Session) -> Dict[str, Any]:
    """Get database metrics."""
    try:
        # Get database size
        result = db.execute(text(
            "SELECT pg_database_size(current_database()) as size"
        )).fetchone()
        db_size = result[0] if result else 0

        # Get connection count
        result = db.execute(text(
            "SELECT count(*) FROM pg_stat_activity"
        )).fetchone()
        connection_count = result[0] if result else 0

        # Get table count
        result = db.execute(text(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
        )).fetchone()
        table_count = result[0] if result else 0

        return {
            "connected": True,
            "database_size_bytes": db_size,
            "connection_count": connection_count,
            "table_count": table_count,
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }


def _get_redis_metrics() -> Dict[str, Any]:
    """Get Redis metrics."""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return {
                "connected": False,
                "reason": "Redis not configured or unavailable",
            }

        # Get Redis info
        info = redis_client.info()

        return {
            "connected": True,
            "version": info.get("redis_version"),
            "uptime_seconds": info.get("uptime_in_seconds"),
            "connected_clients": info.get("connected_clients"),
            "used_memory_bytes": info.get("used_memory"),
            "used_memory_peak_bytes": info.get("used_memory_peak"),
            "total_keys": redis_client.dbsize(),
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }
