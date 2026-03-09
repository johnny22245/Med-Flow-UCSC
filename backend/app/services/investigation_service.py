from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.investigation_record import InvestigationRecord
from app.services.workflow_utils import advance_workflow
from app.services.encounter_service import get_active_encounter_id
from app.schemas.investigation import InvestigationPayload


def get_investigation(db: Session, patient_id: str) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        return {"patientId": patient_id, "payload": None}

    rec = db.execute(
        select(InvestigationRecord).where(InvestigationRecord.encounter_id == encounter_id)
    ).scalars().first()

    if not rec or not rec.results:
        return {"patientId": patient_id, "payload": None}

    # rec.results stores the InvestigationPayload dict
    return {"patientId": patient_id, "payload": rec.results}


def upsert_investigation_payload(db: Session, patient_id: str, payload: InvestigationPayload) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        raise ValueError(f"No active encounter for patient_id={patient_id}. Create patient first.")

    rec = db.execute(
        select(InvestigationRecord).where(InvestigationRecord.encounter_id == encounter_id)
    ).scalars().first()

    payload_dict = payload.model_dump()

    if rec:
        rec.results = payload_dict
    else:
        rec = InvestigationRecord(
            encounter_id=encounter_id,
            results=payload_dict,
            suggested_tests=[],
            ordered_tests=[],
            notes=None,
        )
        db.add(rec)
        
    
    advance_workflow(
        db,
        encounter_id,
        investigation_completed=True,
        stage="diagnosis",
    )
    db.commit()
    db.refresh(rec)

    return {"patientId": patient_id, "payload": rec.results}