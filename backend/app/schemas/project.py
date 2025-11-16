from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
import re


# Shared properties
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    visibility: str = "private"

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        if v not in ["public", "private"]:
            raise ValueError("visibility must be 'public' or 'private'")
        return v


# Properties to receive on creation
class ProjectCreate(ProjectBase):
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("name must be at least 3 characters")
        if len(v) > 100:
            raise ValueError("name must be at most 100 characters")
        return v


# Properties to receive on update
class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["public", "private"]:
            raise ValueError("visibility must be 'public' or 'private'")
        return v


# Properties shared in DB model
class ProjectInDBBase(ProjectBase):
    id: UUID
    slug: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# Properties to return to client
class Project(ProjectInDBBase):
    run_count: Optional[int] = None
    last_activity: Optional[datetime] = None


# Properties stored in DB
class ProjectInDB(ProjectInDBBase):
    pass


# List response
class ProjectList(BaseModel):
    items: list[Project]
    total: int
    page: int
    page_size: int
    total_pages: int
