import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Text, Boolean, Float, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class DiagnosisRecord(Base):
    __tablename__ = "diagnosis_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    encounter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # v0: one diagnosis record per encounter
    )

    # AI generated differential diagnosis list (flexible)
    ai_differential = Column(JSONB, nullable=False, default=list)

    # Clinician confirmed diagnosis
    confirmed_diagnosis = Column(String, nullable=True)

    # Optional confidence score (0..1)
    confidence = Column(String, nullable=True)

    # Explanation / reasoning (AI + clinician notes)
    reasoning = Column(Text, nullable=True)

    # Override metadata
    clinician_override = Column(Boolean, nullable=False, default=False)
    override_reason = Column(Text, nullable=True)

    # Optional: store supporting evidence (e.g., key labs/imaging snippets)
    evidence = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)