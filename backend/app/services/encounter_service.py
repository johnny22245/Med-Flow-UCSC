from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.encounter import Encounter


def get_active_encounter_id(db: Session, patient_id: str):
    enc = db.execute(
        select(Encounter)
        .where(Encounter.patient_id == patient_id)
        .where(Encounter.status == "active")
        .order_by(Encounter.created_at.desc())
        .limit(1)
    ).scalars().first()

    return enc.id if enc else None
