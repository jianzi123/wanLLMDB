from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


# Shared properties
class RunBase(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []


# Properties to receive on creation
class RunCreate(RunBase):
    project_id: UUID

    # Git info
    git_commit: Optional[str] = None
    git_remote: Optional[str] = None
    git_branch: Optional[str] = None

    # Environment info
    host: Optional[str] = None
    os: Optional[str] = None
    python_version: Optional[str] = None


# Properties to receive on update
class RunUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["running", "finished", "crashed", "killed"]:
            raise ValueError("state must be one of: running, finished, crashed, killed")
        return v


# Config operations
class RunConfigUpdate(BaseModel):
    config: Dict[str, Any]


# Tag operations
class RunTagAdd(BaseModel):
    tags: List[str]


# Finish run
class RunFinish(BaseModel):
    exit_code: int = 0
    summary: Optional[Dict[str, Any]] = None


# Properties shared in DB model
class RunInDBBase(RunBase):
    id: UUID
    project_id: UUID
    user_id: UUID
    state: str

    git_commit: Optional[str] = None
    git_remote: Optional[str] = None
    git_branch: Optional[str] = None

    host: Optional[str] = None
    os: Optional[str] = None
    python_version: Optional[str] = None

    started_at: datetime
    finished_at: Optional[datetime] = None
    heartbeat_at: datetime

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Properties to return to client
class Run(RunInDBBase):
    config: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    duration: Optional[float] = None  # in seconds


# Properties stored in DB
class RunInDB(RunInDBBase):
    pass


# List response
class RunList(BaseModel):
    items: List[Run]
    total: int
    page: int
    page_size: int
    total_pages: int
