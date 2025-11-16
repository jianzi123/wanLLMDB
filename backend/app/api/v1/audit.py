"""
Audit Log API Endpoints

Provides endpoints for viewing and querying audit logs (admin only).
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User as UserModel
from app.schemas.user import User
from pydantic import BaseModel


router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class AuditLogResponse(BaseModel):
    """Audit log response schema."""

    id: UUID
    event_type: str
    event_category: str
    severity: str
    user_id: Optional[UUID]
    username: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_method: Optional[str]
    request_path: Optional[str]
    description: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    resource_name: Optional[str]
    event_metadata: Optional[dict]
    status: str
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response."""

    logs: List[AuditLogResponse]
    total: int
    skip: int
    limit: int


# ============================================================================
# Helper Functions
# ============================================================================

def check_admin_user(current_user: User, db: Session) -> UserModel:
    """
    Verify that current user is an admin.

    Admin users are configured via ADMIN_USERS environment variable.
    Format: comma-separated usernames (e.g., "admin,tech_lead,manager")

    Raises:
        HTTPException: If user is not found, admin users not configured, or user is not an admin
    """
    user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # Get configured admin users
    admin_users = settings.get_admin_users()

    if not admin_users:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin users not configured. Please set ADMIN_USERS environment variable.",
        )

    if user.username not in admin_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. Only administrators can access audit logs.",
        )

    return user


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[str] = None,
    event_category: Optional[str] = None,
    severity: Optional[str] = None,
    user_id: Optional[UUID] = None,
    username: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get audit logs with filtering and pagination.

    **Filters**:
    - event_type: Filter by event type (e.g., "auth.login.success")
    - event_category: Filter by category (authentication, authorization, data_modification, etc.)
    - severity: Filter by severity (critical, high, medium, low, info)
    - user_id: Filter by user ID
    - username: Filter by username
    - resource_type: Filter by resource type (project, artifact, user, etc.)
    - resource_id: Filter by resource ID
    - start_date: Filter logs after this date
    - end_date: Filter logs before this date

    **Requires**: Admin access
    """
    # Check admin permission
    check_admin_user(current_user, db)

    # Build query
    query = db.query(AuditLog)

    # Apply filters
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if event_category:
        query = query.filter(AuditLog.event_category == event_category)
    if severity:
        query = query.filter(AuditLog.severity == severity)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username}%"))
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.filter(AuditLog.resource_id == resource_id)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    # Get total count
    total = query.count()

    # Order by created_at descending (newest first)
    query = query.order_by(desc(AuditLog.created_at))

    # Apply pagination
    logs = query.offset(skip).limit(limit).all()

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific audit log entry by ID.

    **Requires**: Admin access
    """
    # Check admin permission
    check_admin_user(current_user, db)

    # Get log
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )

    return AuditLogResponse.model_validate(log)


@router.get("/logs/user/{user_id}", response_model=AuditLogListResponse)
async def get_user_audit_logs(
    user_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all audit logs for a specific user.

    **Requires**: Admin access
    """
    # Check admin permission
    check_admin_user(current_user, db)

    # Build query
    query = db.query(AuditLog).filter(AuditLog.user_id == user_id)

    # Get total count
    total = query.count()

    # Order by created_at descending
    query = query.order_by(desc(AuditLog.created_at))

    # Apply pagination
    logs = query.offset(skip).limit(limit).all()

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/logs/security/failed-logins", response_model=AuditLogListResponse)
async def get_failed_logins(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    hours: int = Query(24, ge=1, le=720),  # Last 24 hours by default, max 30 days
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get recent failed login attempts.

    Useful for detecting brute force attacks or suspicious activity.

    **Parameters**:
    - hours: Number of hours to look back (default: 24, max: 720)

    **Requires**: Admin access
    """
    # Check admin permission
    check_admin_user(current_user, db)

    # Calculate start time
    from datetime import timedelta
    start_time = datetime.utcnow() - timedelta(hours=hours)

    # Build query
    query = db.query(AuditLog).filter(
        AuditLog.event_type == "auth.login.failed",
        AuditLog.created_at >= start_time,
    )

    # Get total count
    total = query.count()

    # Order by created_at descending
    query = query.order_by(desc(AuditLog.created_at))

    # Apply pagination
    logs = query.offset(skip).limit(limit).all()

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stats/summary")
async def get_audit_stats(
    hours: int = Query(24, ge=1, le=720),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get summary statistics for audit logs.

    **Parameters**:
    - hours: Number of hours to look back (default: 24, max: 720)

    **Requires**: Admin access
    """
    # Check admin permission
    check_admin_user(current_user, db)

    # Calculate start time
    from datetime import timedelta
    start_time = datetime.utcnow() - timedelta(hours=hours)

    # Get counts by category
    from sqlalchemy import func

    category_counts = db.query(
        AuditLog.event_category,
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.created_at >= start_time
    ).group_by(
        AuditLog.event_category
    ).all()

    # Get counts by severity
    severity_counts = db.query(
        AuditLog.severity,
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.created_at >= start_time
    ).group_by(
        AuditLog.severity
    ).all()

    # Get failed login count
    failed_logins = db.query(func.count(AuditLog.id)).filter(
        AuditLog.event_type == "auth.login.failed",
        AuditLog.created_at >= start_time,
    ).scalar()

    # Get successful login count
    successful_logins = db.query(func.count(AuditLog.id)).filter(
        AuditLog.event_type == "auth.login.success",
        AuditLog.created_at >= start_time,
    ).scalar()

    # Get total event count
    total_events = db.query(func.count(AuditLog.id)).filter(
        AuditLog.created_at >= start_time
    ).scalar()

    return {
        "period_hours": hours,
        "start_time": start_time,
        "total_events": total_events,
        "by_category": {cat: count for cat, count in category_counts},
        "by_severity": {sev: count for sev, count in severity_counts},
        "authentication": {
            "successful_logins": successful_logins,
            "failed_logins": failed_logins,
            "failure_rate": (failed_logins / (successful_logins + failed_logins) if (successful_logins + failed_logins) > 0 else 0),
        },
    }
