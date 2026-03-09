from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.safety_check import SafetyCheck
from app.services.encounter_service import get_active_encounter_id
from app.services.workflow_utils import advance_workflow
from app.schemas.safety import SafetyUpsertRequest


def get_safety(db: Session, patient_id: str) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        return {
            "patientId": patient_id,
            "findings": [],
            "status": "pending",
            "clinician_approved": False,
            "approval_note": None,
            "provenance": {},
        }

    rec = db.execute(
        select(SafetyCheck).where(SafetyCheck.encounter_id == encounter_id)
    ).scalars().first()

    if not rec:
        return {
            "patientId": patient_id,
            "findings": [],
            "status": "pending",
            "clinician_approved": False,
            "approval_note": None,
            "provenance": {},
        }

    return {
        "patientId": patient_id,
        "findings": rec.findings or [],
        "status": rec.status or "pending",
        "clinician_approved": bool(rec.clinician_approved),
        "approval_note": rec.approval_note,
        "provenance": rec.provenance or {},
    }


def upsert_safety(db: Session, patient_id: str, payload: SafetyUpsertRequest) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        raise ValueError(f"No active encounter for patient_id={patient_id}. Create patient first.")

    rec = db.execute(
        select(SafetyCheck).where(SafetyCheck.encounter_id == encounter_id)
    ).scalars().first()

    findings_list = None
    if payload.findings is not None:
        findings_list = [f.model_dump() for f in payload.findings]

    if rec:
        if findings_list is not None:
            rec.findings = findings_list
        if payload.status is not None:
            rec.status = payload.status
        if payload.clinician_approved is not None:
            rec.clinician_approved = payload.clinician_approved
        if payload.approval_note is not None:
            rec.approval_note = payload.approval_note
        if payload.provenance is not None:
            rec.provenance = payload.provenance
    else:
        rec = SafetyCheck(
            encounter_id=encounter_id,
            findings=findings_list or [],
            status=payload.status or "pending",
            clinician_approved=payload.clinician_approved or False,
            approval_note=payload.approval_note,
            provenance=payload.provenance or {},
        )
        db.add(rec)

    # Default workflow progression:
    # If safety status is "cleared" OR clinician approves, move to summary.
    new_status = (payload.status or (rec.status if rec else "pending") or "pending").lower()
    approved = bool(payload.clinician_approved) if payload.clinician_approved is not None else bool(rec.clinician_approved)

    if new_status == "cleared" or approved:
        advance_workflow(
            db,
            encounter_id,
            safety_cleared=True,
            stage="summary",
        )

    db.commit()
    db.refresh(rec)

    return get_safety(db, patient_id)