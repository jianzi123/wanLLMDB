"""
Audit Log Model for wanLLMDB

Tracks security-critical events and user actions for compliance and security monitoring.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    String,
    DateTime,
    JSON,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditLog(Base):
    """
    Audit log for security and compliance tracking.

    Records all security-critical events including:
    - Authentication events (login, logout, failed attempts)
    - Authorization events (permission checks, access denied)
    - Data modifications (create, update, delete)
    - Configuration changes
    - Security events (password changes, MFA events)
    """

    __tablename__ = "audit_logs"

    # Primary key
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Event information
    event_type = Column(String(100), nullable=False, index=True)
    """
    Type of event. Examples:
    - auth.login.success
    - auth.login.failed
    - auth.logout
    - auth.password_change
    - project.create
    - project.update
    - project.delete
    - artifact.upload
    - artifact.download
    - artifact.delete
    - user.create
    - user.update
    - user.delete
    - config.update
    """

    event_category = Column(String(50), nullable=False, index=True)
    """
    Category of event for filtering:
    - authentication
    - authorization
    - data_access
    - data_modification
    - configuration
    - security
    """

    severity = Column(String(20), nullable=False, index=True, default='info')
    """
    Severity level:
    - critical: Security incidents, data breaches, unauthorized access
    - high: Failed authentication, permission denied
    - medium: Data modifications, configuration changes
    - low: Successful logins, data reads
    - info: General operational events
    """

    # User information
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user = relationship("User", backref="audit_logs")

    username = Column(String(255), nullable=True, index=True)
    """Username at time of event (denormalized for historical tracking)"""

    # Request information
    ip_address = Column(String(45), nullable=True, index=True)
    """IPv4 or IPv6 address"""

    user_agent = Column(String(500), nullable=True)
    """Browser/client user agent string"""

    request_method = Column(String(10), nullable=True)
    """HTTP method: GET, POST, PUT, DELETE, etc."""

    request_path = Column(String(500), nullable=True)
    """API endpoint path"""

    # Event details
    description = Column(Text, nullable=False)
    """Human-readable description of the event"""

    resource_type = Column(String(100), nullable=True, index=True)
    """Type of resource affected: project, artifact, user, etc."""

    resource_id = Column(String(255), nullable=True, index=True)
    """ID of the affected resource"""

    resource_name = Column(String(500), nullable=True)
    """Name of the affected resource"""

    # Additional context
    metadata = Column(JSON, nullable=True)
    """
    Additional context as JSON. Examples:
    - {"failed_attempts": 3, "reason": "invalid_password"}
    - {"artifact_size": 1024000, "artifact_type": "model"}
    - {"old_value": "private", "new_value": "public"}
    """

    # Status
    status = Column(String(20), nullable=False, default='success')
    """Status: success, failure, error"""

    error_message = Column(Text, nullable=True)
    """Error message if status is failure/error"""

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, event_type={self.event_type}, "
            f"user={self.username}, created_at={self.created_at})>"
        )


# Composite indexes for common queries
Index('ix_audit_logs_user_created', AuditLog.user_id, AuditLog.created_at)
Index('ix_audit_logs_category_created', AuditLog.event_category, AuditLog.created_at)
Index('ix_audit_logs_severity_created', AuditLog.severity, AuditLog.created_at)
Index('ix_audit_logs_resource_type_id', AuditLog.resource_type, AuditLog.resource_id)
Index('ix_audit_logs_event_created', AuditLog.event_type, AuditLog.created_at)
