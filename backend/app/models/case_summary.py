import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Text, Boolean, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class CaseSummary(Base):
    __tablename__ = "case_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    encounter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # v0: one summary per encounter
    )

    # Human-readable narrative summary (SOAP-ish or discharge summary)
    summary_text = Column(Text, nullable=False)

    # Optional structured summary for UI / export
    summary_structured = Column(JSONB, nullable=False, default=dict)

    # Status: draft/final
    status = Column(String, nullable=False, default="draft")

    clinician_signed = Column(Boolean, nullable=False, default=False)
    sign_note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    