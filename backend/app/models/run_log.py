"""Run log model for storing execution logs."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Index, BigInteger
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class RunLog(Base):
    """Model for run logs."""

    __tablename__ = "run_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(PGUUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(10), nullable=False, default="INFO")  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(50), nullable=False)  # 'stdout', 'stderr', 'sdk', 'user'
    line_number = Column(BigInteger)  # Sequential line number within the run

    # Relationship
    run = relationship("Run", back_populates="logs")

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_run_logs_run_id", "run_id"),
        Index("ix_run_logs_run_id_timestamp", "run_id", "timestamp"),
        Index("ix_run_logs_level", "level"),
        Index("ix_run_logs_source", "source"),
    )

    def __repr__(self):
        return f"<RunLog {self.id} [{self.level}] {self.message[:50]}>"
