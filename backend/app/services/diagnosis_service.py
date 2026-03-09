from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.diagnosis_record import DiagnosisRecord
from app.services.encounter_service import get_active_encounter_id
from app.services.workflow_utils import advance_workflow
from app.schemas.diagnosis import DiagnosisUpsertRequest
from app.models.workflow_state import WorkflowState


def get_diagnosis(db: Session, patient_id: str) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        return {
            "patientId": patient_id,
            "ai_differential": [],
            "confirmed_diagnosis": None,
            "confidence": None,
            "reasoning": None,
            "clinician_override": False,
            "override_reason": None,
            "evidence": {},
        }

    rec = db.execute(
        select(DiagnosisRecord).where(DiagnosisRecord.encounter_id == encounter_id)
    ).scalars().first()

    if not rec:
        return {
            "patientId": patient_id,
            "ai_differential": [],
            "confirmed_diagnosis": None,
            "confidence": None,
            "reasoning": None,
            "clinician_override": False,
            "override_reason": None,
            "evidence": {},
        }

    return {
        "patientId": patient_id,
        "ai_differential": rec.ai_differential or [],
        "confirmed_diagnosis": rec.confirmed_diagnosis,
        "confidence": rec.confidence,
        "reasoning": rec.reasoning,
        "clinician_override": bool(rec.clinician_override),
        "override_reason": rec.override_reason,
        "evidence": rec.evidence or {},
    }


def upsert_diagnosis(db: Session, patient_id: str, payload: DiagnosisUpsertRequest) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        raise ValueError(f"No active encounter for patient_id={patient_id}. Create patient first.")

    rec = db.execute(
        select(DiagnosisRecord).where(DiagnosisRecord.encounter_id == encounter_id)
    ).scalars().first()

    # Convert Pydantic objects -> plain dicts for JSONB
    differential_list = None
    if payload.ai_differential is not None:
        differential_list = [item.model_dump() for item in payload.ai_differential]

    if rec:
        if differential_list is not None:
            rec.ai_differential = differential_list

        if payload.confirmed_diagnosis is not None:
            rec.confirmed_diagnosis = payload.confirmed_diagnosis

        if payload.confidence is not None:
            rec.confidence = payload.confidence

        if payload.reasoning is not None:
            rec.reasoning = payload.reasoning

        if payload.clinician_override is not None:
            rec.clinician_override = payload.clinician_override

        if payload.override_reason is not None:
            rec.override_reason = payload.override_reason

        if payload.evidence is not None:
            rec.evidence = payload.evidence
    else:
        rec = DiagnosisRecord(
            encounter_id=encounter_id,
            ai_differential=differential_list or [],
            confirmed_diagnosis=payload.confirmed_diagnosis,
            confidence=payload.confidence,
            reasoning=payload.reasoning,
            clinician_override=payload.clinician_override or False,
            override_reason=payload.override_reason,
            evidence=payload.evidence or {},
        )
        db.add(rec)

    # -----------------------------------
    # Default workflow progression logic
    # -----------------------------------
    if rec.confirmed_diagnosis:
        advance_workflow(
            db,
            encounter_id,
            diagnosis_confirmed=True,
            stage="treatment",
        )

    db.commit()
    db.refresh(rec)

    return get_diagnosis(db, patient_id)
