"""Run file model for storing files associated with runs."""

from uuid import uuid4
from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class RunFile(Base):
    """Files associated with a run.

    This model stores metadata about files uploaded during a run,
    such as model checkpoints, plots, or other artifacts.
    """
    __tablename__ = "run_files"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # File information
    name = Column(String(255), nullable=False)
    path = Column(String(512), nullable=False)  # Path within run directory
    size = Column(BigInteger, nullable=False)  # Size in bytes
    content_type = Column(String(100))  # MIME type

    # Storage information
    storage_key = Column(String(512), nullable=False, unique=True)

    # Hash for integrity verification
    md5_hash = Column(String(32))
    sha256_hash = Column(String(64))

    # Metadata
    description = Column(String(500))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    run = relationship("Run", back_populates="files")

    # Indexes
    __table_args__ = (
        Index('ix_run_files_run_id_name', 'run_id', 'name'),
        Index('ix_run_files_created_at', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<RunFile(id={self.id}, name={self.name}, run_id={self.run_id})>"
