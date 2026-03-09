from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class Patient(Base):
    __tablename__ = "patients"

    # Client-provided MRN / internal id
    id = Column(String, primary_key=True)

    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String, nullable=False)

    intake = Column(JSONB, nullable=False)

    allergies = Column(JSONB, nullable=False, default=list)
    meds = Column(JSONB, nullable=False, default=list)

    extra = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)