from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.treatment_plan import TreatmentPlan
from app.services.encounter_service import get_active_encounter_id
from app.services.workflow_utils import advance_workflow
from app.schemas.treatment import TreatmentUpsertRequest


def get_treatment(db: Session, patient_id: str) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        return {"patientId": patient_id, "plan": {}, "status": "draft", "clinician_approved": False, "approval_note": None}

    rec = db.execute(
        select(TreatmentPlan).where(TreatmentPlan.encounter_id == encounter_id)
    ).scalars().first()

    if not rec:
        return {"patientId": patient_id, "plan": {}, "status": "draft", "clinician_approved": False, "approval_note": None}

    return {
        "patientId": patient_id,
        "plan": rec.plan or {},
        "status": rec.status or "draft",
        "clinician_approved": bool(rec.clinician_approved),
        "approval_note": rec.approval_note,
    }


def upsert_treatment(db: Session, patient_id: str, payload: TreatmentUpsertRequest) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        raise ValueError(f"No active encounter for patient_id={patient_id}. Create patient first.")

    rec = db.execute(
        select(TreatmentPlan).where(TreatmentPlan.encounter_id == encounter_id)
    ).scalars().first()

    if rec:
        rec.plan = payload.plan
        if payload.status is not None:
            rec.status = payload.status
        if payload.clinician_approved is not None:
            rec.clinician_approved = payload.clinician_approved
        if payload.approval_note is not None:
            rec.approval_note = payload.approval_note
    else:
        rec = TreatmentPlan(
            encounter_id=encounter_id,
            plan=payload.plan,
            status=payload.status or "draft",
            clinician_approved=payload.clinician_approved or False,
            approval_note=payload.approval_note,
        )
        db.add(rec)

    # Default workflow progression:
    # If any treatment plan is saved, we consider treatment drafted and move to safety.
    advance_workflow(
        db,
        encounter_id,
        treatment_drafted=True,
        stage="safety",
    )

    db.commit()
    db.refresh(rec)

    return get_treatment(db, patient_id)