from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base


class RunConfig(Base):
    __tablename__ = "run_configs"

    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True)
    key = Column(String(255), primary_key=True, nullable=False)
    value = Column(JSON, nullable=False)
