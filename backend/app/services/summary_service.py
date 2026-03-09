from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.case_summary import CaseSummary
from app.services.encounter_service import get_active_encounter_id
from app.services.workflow_utils import advance_workflow
from app.schemas.summary import SummaryUpsertRequest


def get_summary(db: Session, patient_id: str) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        return {
            "patientId": patient_id,
            "summary_text": "",
            "summary_structured": {},
            "status": "draft",
            "clinician_signed": False,
            "sign_note": None,
        }

    rec = db.execute(
        select(CaseSummary).where(CaseSummary.encounter_id == encounter_id)
    ).scalars().first()

    if not rec:
        return {
            "patientId": patient_id,
            "summary_text": "",
            "summary_structured": {},
            "status": "draft",
            "clinician_signed": False,
            "sign_note": None,
        }

    return {
        "patientId": patient_id,
        "summary_text": rec.summary_text,
        "summary_structured": rec.summary_structured or {},
        "status": rec.status or "draft",
        "clinician_signed": bool(rec.clinician_signed),
        "sign_note": rec.sign_note,
    }


def upsert_summary(db: Session, patient_id: str, payload: SummaryUpsertRequest) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        raise ValueError(f"No active encounter for patient_id={patient_id}. Create patient first.")

    rec = db.execute(
        select(CaseSummary).where(CaseSummary.encounter_id == encounter_id)
    ).scalars().first()

    structured = payload.summary_structured or {}

    if rec:
        rec.summary_text = payload.summary_text
        rec.summary_structured = structured
        if payload.status is not None:
            rec.status = payload.status
        if payload.clinician_signed is not None:
            rec.clinician_signed = payload.clinician_signed
        if payload.sign_note is not None:
            rec.sign_note = payload.sign_note
    else:
        rec = CaseSummary(
            encounter_id=encounter_id,
            summary_text=payload.summary_text,
            summary_structured=structured,
            status=payload.status or "draft",
            clinician_signed=payload.clinician_signed or False,
            sign_note=payload.sign_note,
        )
        db.add(rec)

    # Default workflow progression:
    # If summary is saved as final OR clinician signed, finalize case.
    new_status = (payload.status or rec.status or "draft").lower()
    signed = bool(payload.clinician_signed) if payload.clinician_signed is not None else bool(rec.clinician_signed)

    if new_status == "final" or signed:
        advance_workflow(
            db,
            encounter_id,
            finalized=True,
            stage="final",
        )

    db.commit()
    db.refresh(rec)

    return get_summary(db, patient_id)