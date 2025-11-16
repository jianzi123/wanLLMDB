"""
Audit Logging Utilities for wanLLMDB

Provides functions for logging security-critical events and user actions.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


class AuditLogger:
    """
    Centralized audit logging service.

    Usage:
        audit = AuditLogger(db)
        audit.log_auth_success(user, request)
        audit.log_auth_failure(username, request, reason="invalid_password")
        audit.log_data_modification("project.create", user, project_id, request)
    """

    def __init__(self, db: Session):
        self.db = db

    def _extract_request_info(self, request: Optional[Request]) -> Dict[str, Any]:
        """Extract relevant information from FastAPI request."""
        if request is None:
            return {
                "ip_address": None,
                "user_agent": None,
                "request_method": None,
                "request_path": None,
            }

        # Get IP address (handle proxy headers)
        ip_address = request.client.host if request.client else None
        if "x-forwarded-for" in request.headers:
            ip_address = request.headers["x-forwarded-for"].split(",")[0].strip()
        elif "x-real-ip" in request.headers:
            ip_address = request.headers["x-real-ip"]

        return {
            "ip_address": ip_address,
            "user_agent": request.headers.get("user-agent"),
            "request_method": request.method,
            "request_path": str(request.url.path),
        }

    def _create_log(
        self,
        event_type: str,
        event_category: str,
        description: str,
        severity: str = "info",
        user: Optional[User] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Create and save an audit log entry."""
        request_info = self._extract_request_info(request)

        audit_log = AuditLog(
            event_type=event_type,
            event_category=event_category,
            description=description,
            severity=severity,
            user_id=user.id if user else None,
            username=username or (user.username if user else None),
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            resource_name=resource_name,
            status=status,
            error_message=error_message,
            event_metadata=metadata,
            **request_info,
        )

        self.db.add(audit_log)
        self.db.commit()
        return audit_log

    # ========================================================================
    # Authentication Events
    # ========================================================================

    def log_auth_success(
        self,
        user: User,
        request: Optional[Request] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log successful authentication."""
        return self._create_log(
            event_type="auth.login.success",
            event_category="authentication",
            description=f"User '{user.username}' logged in successfully",
            severity="low",
            user=user,
            status="success",
            metadata=metadata,
            request=request,
        )

    def log_auth_failure(
        self,
        username: str,
        reason: str,
        request: Optional[Request] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log failed authentication attempt."""
        meta = metadata or {}
        meta["reason"] = reason

        return self._create_log(
            event_type="auth.login.failed",
            event_category="authentication",
            description=f"Failed login attempt for user '{username}': {reason}",
            severity="high",
            username=username,
            status="failure",
            error_message=reason,
            metadata=meta,
            request=request,
        )

    def log_logout(
        self,
        user: User,
        token_revoked: bool = False,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log user logout."""
        return self._create_log(
            event_type="auth.logout",
            event_category="authentication",
            description=f"User '{user.username}' logged out",
            severity="low",
            user=user,
            status="success",
            metadata={"token_revoked": token_revoked},
            request=request,
        )

    def log_password_change(
        self,
        user: User,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log password change."""
        return self._create_log(
            event_type="auth.password_change",
            event_category="security",
            description=f"User '{user.username}' changed their password",
            severity="medium",
            user=user,
            status="success",
            request=request,
        )

    def log_token_revoked(
        self,
        user: User,
        reason: str = "logout",
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log token revocation."""
        return self._create_log(
            event_type="auth.token_revoked",
            event_category="security",
            description=f"Token revoked for user '{user.username}': {reason}",
            severity="medium",
            user=user,
            metadata={"reason": reason},
            request=request,
        )

    # ========================================================================
    # Authorization Events
    # ========================================================================

    def log_access_denied(
        self,
        user: Optional[User],
        resource_type: str,
        resource_id: str,
        reason: str,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log access denied event."""
        username = user.username if user else "anonymous"
        return self._create_log(
            event_type="authz.access_denied",
            event_category="authorization",
            description=f"Access denied for user '{username}' to {resource_type} '{resource_id}': {reason}",
            severity="high",
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            status="failure",
            error_message=reason,
            request=request,
        )

    # ========================================================================
    # Data Modification Events
    # ========================================================================

    def log_project_created(
        self,
        user: User,
        project_id: UUID,
        project_name: str,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log project creation."""
        return self._create_log(
            event_type="project.create",
            event_category="data_modification",
            description=f"User '{user.username}' created project '{project_name}'",
            severity="medium",
            user=user,
            resource_type="project",
            resource_id=str(project_id),
            resource_name=project_name,
            request=request,
        )

    def log_project_updated(
        self,
        user: User,
        project_id: UUID,
        project_name: str,
        changes: Dict[str, Any],
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log project update."""
        return self._create_log(
            event_type="project.update",
            event_category="data_modification",
            description=f"User '{user.username}' updated project '{project_name}'",
            severity="medium",
            user=user,
            resource_type="project",
            resource_id=str(project_id),
            resource_name=project_name,
            metadata={"changes": changes},
            request=request,
        )

    def log_project_deleted(
        self,
        user: User,
        project_id: UUID,
        project_name: str,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log project deletion."""
        return self._create_log(
            event_type="project.delete",
            event_category="data_modification",
            description=f"User '{user.username}' deleted project '{project_name}'",
            severity="high",
            user=user,
            resource_type="project",
            resource_id=str(project_id),
            resource_name=project_name,
            request=request,
        )

    def log_artifact_uploaded(
        self,
        user: User,
        artifact_id: UUID,
        artifact_name: str,
        artifact_type: str,
        size_bytes: int,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log artifact upload."""
        return self._create_log(
            event_type="artifact.upload",
            event_category="data_modification",
            description=f"User '{user.username}' uploaded artifact '{artifact_name}' ({artifact_type})",
            severity="medium",
            user=user,
            resource_type="artifact",
            resource_id=str(artifact_id),
            resource_name=artifact_name,
            metadata={"artifact_type": artifact_type, "size_bytes": size_bytes},
            request=request,
        )

    def log_artifact_downloaded(
        self,
        user: User,
        artifact_id: UUID,
        artifact_name: str,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log artifact download."""
        return self._create_log(
            event_type="artifact.download",
            event_category="data_access",
            description=f"User '{user.username}' downloaded artifact '{artifact_name}'",
            severity="low",
            user=user,
            resource_type="artifact",
            resource_id=str(artifact_id),
            resource_name=artifact_name,
            request=request,
        )

    def log_artifact_deleted(
        self,
        user: User,
        artifact_id: UUID,
        artifact_name: str,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log artifact deletion."""
        return self._create_log(
            event_type="artifact.delete",
            event_category="data_modification",
            description=f"User '{user.username}' deleted artifact '{artifact_name}'",
            severity="high",
            user=user,
            resource_type="artifact",
            resource_id=str(artifact_id),
            resource_name=artifact_name,
            request=request,
        )

    # ========================================================================
    # User Management Events
    # ========================================================================

    def log_user_created(
        self,
        admin_user: User,
        new_user_id: UUID,
        new_username: str,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log user creation."""
        return self._create_log(
            event_type="user.create",
            event_category="data_modification",
            description=f"Admin '{admin_user.username}' created user '{new_username}'",
            severity="medium",
            user=admin_user,
            resource_type="user",
            resource_id=str(new_user_id),
            resource_name=new_username,
            request=request,
        )

    def log_user_deleted(
        self,
        admin_user: User,
        deleted_user_id: UUID,
        deleted_username: str,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log user deletion."""
        return self._create_log(
            event_type="user.delete",
            event_category="data_modification",
            description=f"Admin '{admin_user.username}' deleted user '{deleted_username}'",
            severity="critical",
            user=admin_user,
            resource_type="user",
            resource_id=str(deleted_user_id),
            resource_name=deleted_username,
            request=request,
        )

    # ========================================================================
    # Security Events
    # ========================================================================

    def log_security_event(
        self,
        event_type: str,
        description: str,
        severity: str = "high",
        user: Optional[User] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log generic security event."""
        return self._create_log(
            event_type=event_type,
            event_category="security",
            description=description,
            severity=severity,
            user=user,
            metadata=metadata,
            request=request,
        )


# ============================================================================
# Helper Functions
# ============================================================================

def get_audit_logger(db: Session) -> AuditLogger:
    """Get an audit logger instance."""
    return AuditLogger(db)
