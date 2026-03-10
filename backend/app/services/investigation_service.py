from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone

from app.models.investigation_record import InvestigationRecord
from app.services.workflow_utils import advance_workflow
from app.services.encounter_service import get_active_encounter_id
from app.schemas.investigation import (
    InvestigationPayload,
    InvestigationOrdersPayload,
)


def get_investigation(db: Session, patient_id: str) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        return {"patientId": patient_id, "payload": None}

    rec = db.execute(
        select(InvestigationRecord).where(InvestigationRecord.encounter_id == encounter_id)
    ).scalars().first()

    if not rec or not rec.results:
        return {"patientId": patient_id, "payload": None}

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
        rec.updated_at = datetime.now(timezone.utc)
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


def upsert_investigation_orders(
    db: Session,
    patient_id: str,
    payload: InvestigationOrdersPayload,
) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        raise ValueError(f"No active encounter for patient_id={patient_id}. Create patient first.")

    rec = db.execute(
        select(InvestigationRecord).where(InvestigationRecord.encounter_id == encounter_id)
    ).scalars().first()

    suggested_tests = [item.model_dump() for item in payload.suggested_tests]
    ordered_tests = [item.model_dump() for item in payload.ordered_tests]

    if rec:
        rec.suggested_tests = suggested_tests
        rec.ordered_tests = ordered_tests
        rec.notes = payload.notes
        rec.updated_at = datetime.now(timezone.utc)
    else:
        rec = InvestigationRecord(
            encounter_id=encounter_id,
            suggested_tests=suggested_tests,
            ordered_tests=ordered_tests,
            results={},
            notes=payload.notes,
        )
        db.add(rec)

    # move workflow into investigation stage after test confirmation
    advance_workflow(
        db,
        encounter_id,
        stage="investigation",
    )

    db.commit()
    db.refresh(rec)

    return {
        "patientId": patient_id,
        "encounterId": str(encounter_id),
        "suggested_tests": rec.suggested_tests or [],
        "ordered_tests": rec.ordered_tests or [],
        "notes": rec.notes,
        "confirmed": True,
    }