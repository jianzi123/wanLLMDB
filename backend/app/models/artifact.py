"""
Artifact models for file and model versioning.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, JSON, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Artifact(Base):
    """
    Artifact model for storing files, models, and datasets.

    Artifacts are versioned collections of files that can be attached to runs.
    """
    __tablename__ = "artifacts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # model, dataset, file, code
    description = Column(Text, nullable=True)

    # Ownership
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Metadata
    metadata = Column(JSON, nullable=True, default=dict)
    tags = Column(JSON, nullable=True, default=list)

    # Versioning
    version_count = Column(Integer, nullable=False, default=0)
    latest_version = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="artifacts")
    user = relationship("User")
    versions = relationship("ArtifactVersion", back_populates="artifact", cascade="all, delete-orphan")


class ArtifactVersion(Base):
    """
    Artifact version model for versioned artifact storage.

    Each version contains a collection of files stored in MinIO.
    """
    __tablename__ = "artifact_versions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    artifact_id = Column(PGUUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=False, index=True)
    version = Column(String(50), nullable=False, index=True)

    # Description and notes
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # File information
    file_count = Column(Integer, nullable=False, default=0)
    total_size = Column(BigInteger, nullable=False, default=0)  # Total size in bytes

    # Storage
    storage_path = Column(String(500), nullable=False)  # MinIO path prefix

    # Metadata
    metadata = Column(JSON, nullable=True, default=dict)
    digest = Column(String(64), nullable=True)  # Hash of all files for integrity

    # Association with run (optional)
    run_id = Column(PGUUID(as_uuid=True), ForeignKey("runs.id"), nullable=True, index=True)

    # Status
    is_finalized = Column(Boolean, nullable=False, default=False)

    # User who created this version
    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finalized_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    artifact = relationship("Artifact", back_populates="versions")
    run = relationship("Run")
    user = relationship("User")
    files = relationship("ArtifactFile", back_populates="version", cascade="all, delete-orphan")


class ArtifactFile(Base):
    """
    Individual file within an artifact version.
    """
    __tablename__ = "artifact_files"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    version_id = Column(PGUUID(as_uuid=True), ForeignKey("artifact_versions.id"), nullable=False, index=True)

    # File information
    path = Column(String(500), nullable=False)  # Relative path within artifact
    name = Column(String(255), nullable=False)
    size = Column(BigInteger, nullable=False)  # Size in bytes
    mime_type = Column(String(100), nullable=True)

    # Storage - either local (MinIO) or external reference (S3/GCS)
    is_reference = Column(Boolean, nullable=False, default=False, index=True)
    storage_key = Column(String(500), nullable=True)  # MinIO object key (for uploaded files)
    reference_uri = Column(String(1000), nullable=True)  # External URI (s3://, gs://, etc.)

    # Integrity
    md5_hash = Column(String(32), nullable=True)
    sha256_hash = Column(String(64), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    version = relationship("ArtifactVersion", back_populates="files")


class ArtifactDownload(Base):
    """
    Track artifact downloads for analytics.
    """
    __tablename__ = "artifact_downloads"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    version_id = Column(PGUUID(as_uuid=True), ForeignKey("artifact_versions.id"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Download information
    file_id = Column(PGUUID(as_uuid=True), ForeignKey("artifact_files.id"), nullable=True)  # If single file
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Timestamp
    downloaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    version = relationship("ArtifactVersion")
    user = relationship("User")
    file = relationship("ArtifactFile")


class ArtifactAlias(Base):
    """
    Artifact alias model for human-friendly version references.

    Aliases like "latest", "production", "stable" point to specific artifact versions.
    An artifact can only have one version with a specific alias at a time.
    """
    __tablename__ = "artifact_aliases"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    artifact_id = Column(PGUUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=False, index=True)
    version_id = Column(PGUUID(as_uuid=True), ForeignKey("artifact_versions.id"), nullable=False, index=True)
    alias = Column(String(100), nullable=False, index=True)

    # User who created/updated this alias
    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    artifact = relationship("Artifact")
    version = relationship("ArtifactVersion")
    user = relationship("User")
