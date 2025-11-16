"""Pydantic schemas for run files."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RunFileBase(BaseModel):
    """Base schema for run files."""
    name: str = Field(..., description="File name")
    path: str = Field(..., description="File path within run directory")
    size: int = Field(..., ge=0, description="File size in bytes")
    content_type: Optional[str] = Field(None, description="MIME type")
    description: Optional[str] = Field(None, max_length=500)


class RunFileCreate(RunFileBase):
    """Schema for creating a run file."""
    storage_key: str = Field(..., description="Storage key in MinIO")
    md5_hash: Optional[str] = Field(None, pattern=r"^[a-f0-9]{32}$")
    sha256_hash: Optional[str] = Field(None, pattern=r"^[a-f0-9]{64}$")


class RunFileUpdate(BaseModel):
    """Schema for updating a run file."""
    description: Optional[str] = Field(None, max_length=500)


class RunFile(RunFileBase):
    """Schema for run file response."""
    id: UUID
    run_id: UUID
    storage_key: str
    md5_hash: Optional[str] = None
    sha256_hash: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RunFileList(BaseModel):
    """Schema for paginated run file list."""
    items: list[RunFile]
    total: int
    skip: int
    limit: int


class FileUploadUrlRequest(BaseModel):
    """Schema for requesting file upload URL."""
    name: str = Field(..., description="File name")
    path: str = Field(..., description="File path within run directory")
    size: int = Field(..., ge=0, description="File size in bytes")
    content_type: Optional[str] = Field(None, description="MIME type")
    md5_hash: Optional[str] = Field(None, pattern=r"^[a-f0-9]{32}$")
    sha256_hash: Optional[str] = Field(None, pattern=r"^[a-f0-9]{64}$")


class FileUploadUrlResponse(BaseModel):
    """Schema for file upload URL response."""
    upload_url: str = Field(..., description="Presigned upload URL")
    storage_key: str = Field(..., description="Storage key for the file")
    expires_in: int = Field(..., description="URL expiration time in seconds")


class FileDownloadUrlResponse(BaseModel):
    """Schema for file download URL response."""
    download_url: str = Field(..., description="Presigned download URL")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: Optional[str] = Field(None, description="MIME type")
    expires_in: int = Field(..., description="URL expiration time in seconds")
