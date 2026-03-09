import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class TriageSession(Base):
    __tablename__ = "triage_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    patient_id = Column(
        String,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    encounter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(String, nullable=False, default="in_progress")
    round_count = Column(Integer, nullable=False, default=0)

    # Original case text sent to triage agent
    initial_case = Column(Text, nullable=False)

    # [{"question": "...", "answer": "..."}]
    qa_history = Column(JSONB, nullable=False, default=list)

    # Full latest parsed model output
    latest_output = Column(JSONB, nullable=True)

    # Flattened useful fields for UI/workflow
    urgency = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    missing_info = Column(JSONB, nullable=False, default=list)
    suggested_tests = Column(JSONB, nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)