"""Model registry models for managing model versions and stages."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class ModelStage(str, enum.Enum):
    """Model deployment stages."""

    NONE = "none"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class RegisteredModel(Base):
    """Registered model in the model registry."""

    __tablename__ = "registered_models"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=False)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    versions = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan", order_by="ModelVersion.created_at.desc()")

    # Unique constraint: model name must be unique within a project
    __table_args__ = (
        UniqueConstraint('project_id', 'name', name='uq_project_model_name'),
        Index('ix_registered_models_project_id', 'project_id'),
        Index('ix_registered_models_name', 'name'),
    )

    def __repr__(self):
        return f"<RegisteredModel {self.name}>"


class ModelVersion(Base):
    """Version of a registered model."""

    __tablename__ = "model_versions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    model_id = Column(PGUUID(as_uuid=True), ForeignKey("registered_models.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    stage = Column(SQLEnum(ModelStage), default=ModelStage.NONE, nullable=False, index=True)

    # Link to run and artifact
    run_id = Column(PGUUID(as_uuid=True), ForeignKey("runs.id"), nullable=True)
    artifact_version_id = Column(PGUUID(as_uuid=True), ForeignKey("artifact_versions.id"), nullable=True)

    # Metadata
    metrics = Column(JSON, default=dict, nullable=False)  # Key metrics for this model version
    tags = Column(JSON, default=list, nullable=False)
    metadata_json = Column("metadata", JSON, default=dict, nullable=False)  # Additional metadata

    # Approval/review info
    approved_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    model = relationship("RegisteredModel", back_populates="versions")

    # Unique constraint: version must be unique within a model
    __table_args__ = (
        UniqueConstraint('model_id', 'version', name='uq_model_version'),
        Index('ix_model_versions_model_id', 'model_id'),
        Index('ix_model_versions_stage', 'stage'),
        Index('ix_model_versions_run_id', 'run_id'),
    )

    def __repr__(self):
        return f"<ModelVersion {self.version} stage={self.stage}>"


class ModelVersionTransition(Base):
    """History of model version stage transitions."""

    __tablename__ = "model_version_transitions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    model_version_id = Column(PGUUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True)

    from_stage = Column(SQLEnum(ModelStage), nullable=False)
    to_stage = Column(SQLEnum(ModelStage), nullable=False)

    comment = Column(Text, nullable=True)
    transitioned_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    transitioned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('ix_model_version_transitions_model_version_id', 'model_version_id'),
    )

    def __repr__(self):
        return f"<ModelVersionTransition {self.from_stage} → {self.to_stage}>"
