from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.db.database import Base


class VisibilityEnum(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    visibility = Column(Enum(VisibilityEnum), default=VisibilityEnum.PRIVATE, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    artifacts = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")
    sweeps = relationship("Sweep", back_populates="project", cascade="all, delete-orphan")

    # Note: organization_id will be added later when we implement organizations
