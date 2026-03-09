import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Text, Boolean, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class TreatmentPlan(Base):
    __tablename__ = "treatment_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    encounter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # v0: one treatment plan per encounter
    )

    # v0: flexible plan payload (meds/procedures/followups)
    plan = Column(JSONB, nullable=False, default=dict)

    # draft/final
    status = Column(String, nullable=False, default="draft")

    clinician_approved = Column(Boolean, nullable=False, default=False)
    approval_note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)