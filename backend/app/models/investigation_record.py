import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class InvestigationRecord(Base):
    __tablename__ = "investigation_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    encounter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # v0: one investigation record per encounter
    )

    # v0: store structured data as JSONB
    suggested_tests = Column(JSONB, nullable=False, default=list)  # AI suggestions
    ordered_tests = Column(JSONB, nullable=False, default=list)     # clinician-approved
    results = Column(JSONB, nullable=False, default=dict)           # lab/imaging results summary

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)