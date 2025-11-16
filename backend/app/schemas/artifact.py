"""
Artifact schemas for API validation and serialization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# Artifact schemas
class ArtifactBase(BaseModel):
    """Base artifact schema."""
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern="^(model|dataset|file|code)$")
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class ArtifactCreate(ArtifactBase):
    """Schema for creating an artifact."""
    project_id: UUID


class ArtifactUpdate(BaseModel):
    """Schema for updating an artifact."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class ArtifactInDBBase(ArtifactBase):
    """Base schema for artifact in database."""
    id: UUID
    project_id: UUID
    created_by: UUID
    version_count: int
    latest_version: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Artifact(ArtifactInDBBase):
    """Schema for artifact response."""
    pass


class ArtifactWithVersions(Artifact):
    """Schema for artifact with versions."""
    versions: List["ArtifactVersion"] = []


# Artifact Version schemas
class ArtifactVersionBase(BaseModel):
    """Base artifact version schema."""
    description: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ArtifactVersionCreate(ArtifactVersionBase):
    """Schema for creating an artifact version."""
    artifact_id: UUID
    version: Optional[str] = None  # Auto-generated if not provided
    run_id: Optional[UUID] = None


class ArtifactVersionUpdate(BaseModel):
    """Schema for updating an artifact version."""
    description: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ArtifactVersionFinalize(BaseModel):
    """Schema for finalizing an artifact version."""
    digest: Optional[str] = None


class ArtifactVersionInDBBase(ArtifactVersionBase):
    """Base schema for artifact version in database."""
    id: UUID
    artifact_id: UUID
    version: str
    file_count: int
    total_size: int
    storage_path: str
    digest: Optional[str]
    run_id: Optional[UUID]
    is_finalized: bool
    created_by: UUID
    created_at: datetime
    finalized_at: Optional[datetime]

    class Config:
        from_attributes = True


class ArtifactVersion(ArtifactVersionInDBBase):
    """Schema for artifact version response."""
    pass


class ArtifactVersionWithFiles(ArtifactVersion):
    """Schema for artifact version with files."""
    files: List["ArtifactFile"] = []


# Artifact File schemas
class ArtifactFileBase(BaseModel):
    """Base artifact file schema."""
    path: str = Field(..., min_length=1, max_length=500)
    name: str = Field(..., min_length=1, max_length=255)
    size: int = Field(..., ge=0)
    mime_type: Optional[str] = None


class ArtifactFileCreate(ArtifactFileBase):
    """Schema for creating an artifact file."""
    version_id: UUID
    storage_key: str
    md5_hash: Optional[str] = None
    sha256_hash: Optional[str] = None


class ArtifactFileInDBBase(ArtifactFileBase):
    """Base schema for artifact file in database."""
    id: UUID
    version_id: UUID
    storage_key: str
    md5_hash: Optional[str]
    sha256_hash: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ArtifactFile(ArtifactFileInDBBase):
    """Schema for artifact file response."""
    pass


# File upload schemas
class FileUploadRequest(BaseModel):
    """Schema for file upload request."""
    version_id: UUID
    path: str
    name: str
    size: int
    mime_type: Optional[str] = None


class FileUploadResponse(BaseModel):
    """Schema for file upload response."""
    upload_url: str
    storage_key: str
    expires_in: int  # Seconds


class FileDownloadRequest(BaseModel):
    """Schema for file download request."""
    file_id: UUID


class FileDownloadResponse(BaseModel):
    """Schema for file download response."""
    download_url: str
    file_name: str
    size: int
    mime_type: Optional[str]
    expires_in: int  # Seconds


# List schemas
class ArtifactList(BaseModel):
    """Schema for paginated artifact list."""
    items: List[Artifact]
    total: int
    page: int
    page_size: int
    total_pages: int


class ArtifactVersionList(BaseModel):
    """Schema for paginated artifact version list."""
    items: List[ArtifactVersion]
    total: int
    page: int
    page_size: int
    total_pages: int
