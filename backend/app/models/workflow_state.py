from sqlalchemy import Column, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class WorkflowState(Base):
    __tablename__ = "workflow_state"

    encounter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        primary_key=True
    )

    stage = Column(String, nullable=False, default="intake")

    intake_completed = Column(Boolean, default=False)
    investigation_completed = Column(Boolean, default=False)
    diagnosis_confirmed = Column(Boolean, default=False)
    treatment_drafted = Column(Boolean, default=False)
    safety_cleared = Column(Boolean, default=False)

    finalized = Column(Boolean, default=False)

    updated_at = Column(DateTime(timezone=True), server_default=func.now())