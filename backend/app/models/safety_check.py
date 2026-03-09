import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Text, Boolean, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class SafetyCheck(Base):
    __tablename__ = "safety_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    encounter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # v0: one safety record per encounter
    )

    # v0: store structured safety findings
    # e.g., drug-drug interactions, allergy warnings, contraindications, dose checks
    findings = Column(JSONB, nullable=False, default=list)

    # overall status: pending/needs_review/cleared/blocked
    status = Column(String, nullable=False, default="pending")

    # clinician signoff
    clinician_approved = Column(Boolean, nullable=False, default=False)
    approval_note = Column(Text, nullable=True)

    # optional: which rules/knowledge base/model produced this
    provenance = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)