"""Schemas for model registry."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.model_registry import ModelStage


# Registered Model Schemas

class RegisteredModelBase(BaseModel):
    """Base schema for registered model."""

    name: str = Field(..., description="Model name (unique within project)")
    description: Optional[str] = Field(None, description="Model description")
    tags: List[str] = Field(default_factory=list, description="Model tags")


class RegisteredModelCreate(RegisteredModelBase):
    """Schema for creating a registered model."""

    project_id: UUID = Field(..., description="Project ID")


class RegisteredModelUpdate(BaseModel):
    """Schema for updating a registered model."""

    description: Optional[str] = None
    tags: Optional[List[str]] = None


class RegisteredModel(RegisteredModelBase):
    """Schema for registered model response."""

    id: UUID
    project_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RegisteredModelWithVersions(RegisteredModel):
    """Schema for registered model with versions."""

    versions: List['ModelVersion'] = []


class RegisteredModelList(BaseModel):
    """Schema for paginated registered model list."""

    items: List[RegisteredModel]
    total: int
    skip: int
    limit: int


# Model Version Schemas

class ModelVersionBase(BaseModel):
    """Base schema for model version."""

    version: str = Field(..., description="Version string (e.g., v1, 1.0.0)")
    description: Optional[str] = Field(None, description="Version description")
    stage: ModelStage = Field(default=ModelStage.NONE, description="Deployment stage")
    tags: List[str] = Field(default_factory=list, description="Version tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ModelVersionCreate(ModelVersionBase):
    """Schema for creating a model version."""

    run_id: Optional[UUID] = Field(None, description="Associated run ID")
    artifact_version_id: Optional[UUID] = Field(None, description="Associated artifact version ID")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Model metrics")


class ModelVersionUpdate(BaseModel):
    """Schema for updating a model version."""

    description: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ModelVersion(ModelVersionBase):
    """Schema for model version response."""

    id: UUID
    model_id: UUID
    run_id: Optional[UUID] = None
    artifact_version_id: Optional[UUID] = None
    metrics: Dict[str, float] = {}
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelVersionList(BaseModel):
    """Schema for paginated model version list."""

    items: List[ModelVersion]
    total: int
    skip: int
    limit: int


# Stage Transition Schemas

class StageTransitionRequest(BaseModel):
    """Schema for stage transition request."""

    stage: ModelStage = Field(..., description="Target stage")
    comment: Optional[str] = Field(None, description="Transition comment")


class ModelVersionTransition(BaseModel):
    """Schema for model version transition response."""

    id: UUID
    model_version_id: UUID
    from_stage: ModelStage
    to_stage: ModelStage
    comment: Optional[str] = None
    transitioned_by: UUID
    transitioned_at: datetime

    class Config:
        from_attributes = True


class ModelVersionTransitionList(BaseModel):
    """Schema for transition history list."""

    items: List[ModelVersionTransition]
    total: int


# Model Registry Summary

class ModelRegistrySummary(BaseModel):
    """Summary statistics for model registry."""

    total_models: int
    total_versions: int
    by_stage: Dict[str, int]
