from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.db.database import Base


class RunStateEnum(str, enum.Enum):
    RUNNING = "running"
    FINISHED = "finished"
    CRASHED = "crashed"
    KILLED = "killed"


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    state = Column(Enum(RunStateEnum), default=RunStateEnum.RUNNING, nullable=False, index=True)

    # Hyperparameter sweep association (optional)
    sweep_id = Column(UUID(as_uuid=True), ForeignKey("sweeps.id"), nullable=True, index=True)

    # Git information
    git_commit = Column(String(40), nullable=True)
    git_remote = Column(Text, nullable=True)
    git_branch = Column(String(255), nullable=True)

    # Environment information
    host = Column(String(255), nullable=True)
    os = Column(String(100), nullable=True)
    python_version = Column(String(50), nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Other metadata
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=False)

    # Created/Updated tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    files = relationship("RunFile", back_populates="run", cascade="all, delete-orphan")
    logs = relationship("RunLog", back_populates="run", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="run", foreign_keys="[Job.run_id]")  # Jobs associated with this run
