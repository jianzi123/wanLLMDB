"""
Sweep models for hyperparameter optimization.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
import enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Boolean, JSON, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class SweepMethod(str, enum.Enum):
    """Sweep optimization method."""
    RANDOM = "random"
    GRID = "grid"
    BAYES = "bayes"


class SweepState(str, enum.Enum):
    """Sweep execution state."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELED = "canceled"


class MetricGoal(str, enum.Enum):
    """Optimization goal for metric."""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class Sweep(Base):
    """
    Sweep model for hyperparameter optimization.

    A sweep defines a hyperparameter search space and optimization strategy.
    Multiple runs can be associated with a sweep for systematic exploration.
    """
    __tablename__ = "sweeps"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Ownership
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Optimization configuration
    method = Column(SQLEnum(SweepMethod), nullable=False, default=SweepMethod.RANDOM)
    metric_name = Column(String(255), nullable=False)  # Target metric to optimize
    metric_goal = Column(SQLEnum(MetricGoal), nullable=False, default=MetricGoal.MAXIMIZE)

    # Hyperparameter space configuration
    # Example: {
    #   "learning_rate": {"distribution": "uniform", "min": 0.0001, "max": 0.01},
    #   "batch_size": {"values": [16, 32, 64, 128]},
    #   "optimizer": {"values": ["adam", "sgd", "rmsprop"]}
    # }
    config = Column(JSON, nullable=False, default=dict)

    # Early termination configuration (optional)
    # Example: {"type": "hyperband", "min_iter": 3, "eta": 3}
    early_terminate = Column(JSON, nullable=True)

    # State and statistics
    state = Column(SQLEnum(SweepState), nullable=False, default=SweepState.PENDING, index=True)
    run_count = Column(Integer, nullable=False, default=0)
    run_cap = Column(Integer, nullable=True)  # Maximum number of runs (optional)

    # Best results tracking
    best_run_id = Column(PGUUID(as_uuid=True), ForeignKey("runs.id"), nullable=True)
    best_value = Column(Float, nullable=True)

    # Optuna study configuration (for Bayesian optimization)
    # Stores Optuna study name and sampler configuration
    optuna_config = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="sweeps")
    user = relationship("User")
    best_run = relationship("Run", foreign_keys=[best_run_id])
    # Note: runs relationship is defined through Run.sweep_id


class SweepRun(Base):
    """
    Association table for sweep runs with additional metadata.

    Tracks the relationship between sweeps and runs, including
    suggested parameters and evaluation results.
    """
    __tablename__ = "sweep_runs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sweep_id = Column(PGUUID(as_uuid=True), ForeignKey("sweeps.id"), nullable=False, index=True)
    run_id = Column(PGUUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, index=True)

    # Optuna trial information (for Bayesian optimization)
    trial_number = Column(Integer, nullable=True)
    trial_state = Column(String(50), nullable=True)  # Optuna trial state

    # Suggested parameters for this run
    # These are the hyperparameters suggested by the optimization algorithm
    suggested_params = Column(JSON, nullable=True)

    # Evaluation result
    metric_value = Column(Float, nullable=True)
    is_best = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    evaluated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    sweep = relationship("Sweep")
    run = relationship("Run")
