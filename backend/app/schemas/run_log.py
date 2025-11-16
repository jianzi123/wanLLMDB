"""Schemas for run logs."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class RunLogBase(BaseModel):
    """Base schema for run log."""

    level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    message: str = Field(..., description="Log message")
    timestamp: datetime = Field(..., description="Log timestamp")
    source: str = Field(..., description="Log source: stdout, stderr, sdk, user")
    line_number: Optional[int] = Field(None, description="Sequential line number")


class RunLogCreate(RunLogBase):
    """Schema for creating a run log."""

    pass


class RunLogBatchCreate(BaseModel):
    """Schema for batch creating run logs."""

    logs: List[RunLogCreate] = Field(..., description="List of logs to create")


class RunLog(RunLogBase):
    """Schema for run log response."""

    id: UUID
    run_id: UUID

    class Config:
        from_attributes = True


class RunLogList(BaseModel):
    """Schema for paginated run log list."""

    items: List[RunLog]
    total: int
    skip: int
    limit: int


class RunLogFilter(BaseModel):
    """Schema for filtering run logs."""

    level: Optional[str] = Field(None, description="Filter by log level")
    source: Optional[str] = Field(None, description="Filter by source")
    search: Optional[str] = Field(None, description="Search in message")
    start_time: Optional[datetime] = Field(None, description="Start timestamp")
    end_time: Optional[datetime] = Field(None, description="End timestamp")


class RunLogDownloadRequest(BaseModel):
    """Schema for log download request."""

    format: str = Field(default="txt", description="Download format: txt, json, csv")
    filter: Optional[RunLogFilter] = None
