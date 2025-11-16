"""
Shared dependencies for API endpoints.
"""

from app.db.database import get_db
from app.api.v1.auth import get_current_user
from app.services.storage_service import storage_service


def get_storage_service():
    """Get the global storage service instance."""
    return storage_service


__all__ = ["get_db", "get_current_user", "get_storage_service", "storage_service"]
