from sqlalchemy import Column, ForeignKey, JSON, DateTime, Interval
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.database import Base


class RunSummary(Base):
    __tablename__ = "run_summaries"

    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    metrics = Column(JSON, default=dict, nullable=False)
    system_metrics = Column(JSON, default=dict, nullable=False)
    duration = Column(Interval, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
