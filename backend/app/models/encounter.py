from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class Encounter(Base):
    __tablename__ = "encounters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    patient_id = Column(
        String,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False
    )

    status = Column(String, nullable=False, default="active")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)