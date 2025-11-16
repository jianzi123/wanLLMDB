"""
Pydantic schemas for Sweep models.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field


# Enums
class SweepMethod(str):
    RANDOM = "random"
    GRID = "grid"
    BAYES = "bayes"


class SweepState(str):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELED = "canceled"


class MetricGoal(str):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


# Base schemas
class SweepBase(BaseModel):
    """Base schema for Sweep."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    method: str = Field(default="random")
    metric_name: str = Field(..., min_length=1)
    metric_goal: str = Field(default="maximize")
    config: Dict[str, Any] = Field(default_factory=dict)
    early_terminate: Optional[Dict[str, Any]] = None
    run_cap: Optional[int] = Field(None, ge=1)


class SweepCreate(SweepBase):
    """Schema for creating a sweep."""
    project_id: UUID


class SweepUpdate(BaseModel):
    """Schema for updating a sweep."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    state: Optional[str] = None
    run_cap: Optional[int] = Field(None, ge=1)


class Sweep(SweepBase):
    """Schema for sweep response."""
    id: UUID
    project_id: UUID
    created_by: UUID
    state: str
    run_count: int
    best_run_id: Optional[UUID] = None
    best_value: Optional[float] = None
    optuna_config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SweepList(BaseModel):
    """Schema for paginated sweep list."""
    items: List[Sweep]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    total_pages: int = Field(alias="totalPages")

    class Config:
        populate_by_name = True


# Sweep Run schemas
class SweepRunBase(BaseModel):
    """Base schema for SweepRun."""
    sweep_id: UUID
    run_id: UUID
    suggested_params: Optional[Dict[str, Any]] = None
    metric_value: Optional[float] = None


class SweepRunCreate(SweepRunBase):
    """Schema for creating a sweep run association."""
    pass


class SweepRun(SweepRunBase):
    """Schema for sweep run response."""
    id: UUID
    trial_number: Optional[int] = None
    trial_state: Optional[str] = None
    is_best: bool
    created_at: datetime
    evaluated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Sweep parameter suggestion schemas
class SweepSuggestRequest(BaseModel):
    """Request schema for suggesting next parameters."""
    sweep_id: UUID


class SweepSuggestResponse(BaseModel):
    """Response schema for suggested parameters."""
    suggested_params: Dict[str, Any]
    trial_number: Optional[int] = None


# Sweep statistics schemas
class SweepStats(BaseModel):
    """Statistics for a sweep."""
    sweep_id: UUID
    total_runs: int
    completed_runs: int
    running_runs: int
    failed_runs: int
    best_value: Optional[float] = None
    best_run_id: Optional[UUID] = None
    best_params: Optional[Dict[str, Any]] = None
    parameter_importance: Optional[Dict[str, float]] = None


# Hyperparameter configuration schemas
class ParameterDistribution(BaseModel):
    """Schema for parameter distribution configuration."""
    # For categorical parameters
    values: Optional[List[Any]] = None

    # For continuous parameters
    distribution: Optional[str] = None  # uniform, log_uniform, normal
    min: Optional[float] = None
    max: Optional[float] = None
    mu: Optional[float] = None  # For normal distribution
    sigma: Optional[float] = None  # For normal distribution

    # For integer parameters
    q: Optional[int] = None  # Quantization step


class SweepConfig(BaseModel):
    """Complete sweep configuration."""
    method: str
    metric: Dict[str, str]  # {"name": "accuracy", "goal": "maximize"}
    parameters: Dict[str, ParameterDistribution]
    early_terminate: Optional[Dict[str, Any]] = None
    run_cap: Optional[int] = None


# Sweep run with full details
class SweepRunDetail(SweepRun):
    """Detailed sweep run with run information."""
    run: Optional[Dict[str, Any]] = None  # Full run object


class SweepWithStats(Sweep):
    """Sweep with statistics."""
    stats: Optional[SweepStats] = None


# Parallel coordinates data for visualization
class ParallelCoordinatesData(BaseModel):
    """Data for parallel coordinates visualization."""
    sweep_id: UUID
    dimensions: List[str]  # Parameter names + metric name
    data: List[Dict[str, float]]  # Each run's values
    best_index: Optional[int] = None  # Index of best run
