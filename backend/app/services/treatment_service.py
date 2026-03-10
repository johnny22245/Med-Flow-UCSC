# backend/app/services/treatment_service.py

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.diagnosis_record import DiagnosisRecord
from app.models.investigation_record import InvestigationRecord
from app.models.treatment_plan import TreatmentPlan
from app.schemas.treatment import TreatmentUpsertRequest
from app.services.diagnosis_pipeline import (
    build_case_context_from_records,
    generate_treatment_suggestion,
)
from app.services.encounter_service import get_active_encounter_id
from app.services.workflow_utils import advance_workflow


def _normalize_treatment_response(patient_id: str, plan: dict) -> dict:
    if not plan:
        return {"patientId": patient_id, "suggestedPlan": None}

    if plan.get("drafted") and plan.get("order"):
        return {
            "patientId": patient_id,
            "drafted": True,
            "order": plan.get("order") or {},
        }

    if plan.get("order") and not plan.get("suggestedPlan"):
        return {
            "patientId": patient_id,
            "drafted": True,
            "order": plan.get("order") or {},
        }

    if plan.get("suggestedPlan"):
        return {
            "patientId": patient_id,
            "suggestedPlan": plan.get("suggestedPlan"),
        }

    return {"patientId": patient_id, "suggestedPlan": None}


def get_treatment(db: Session, patient_id: str) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        return {"patientId": patient_id, "suggestedPlan": None}

    rec = db.execute(
        select(TreatmentPlan).where(TreatmentPlan.encounter_id == encounter_id)
    ).scalars().first()

    if rec and rec.plan:
        return _normalize_treatment_response(patient_id, rec.plan)

    diagnosis_rec = db.execute(
        select(DiagnosisRecord).where(DiagnosisRecord.encounter_id == encounter_id)
    ).scalars().first()

    if not diagnosis_rec or not diagnosis_rec.confirmed_diagnosis:
        return {
            "patientId": patient_id,
            "suggestedPlan": None,
            "message": "Confirm diagnosis first before generating treatment plan.",
        }

    investigation_rec = db.execute(
        select(InvestigationRecord).where(InvestigationRecord.encounter_id == encounter_id)
    ).scalars().first()

    case = build_case_context_from_records(
        patient_id=patient_id,
        investigation_record=investigation_rec,
        diagnosis_record=diagnosis_rec,
    )
    generated_plan = generate_treatment_suggestion(case)

    plan_payload = {
        "suggestedPlan": {
            "title": generated_plan.get("title"),
            "meds": generated_plan.get("meds") or [],
            "notes": generated_plan.get("notes") or [],
        },
        "evidence": generated_plan.get("evidence") or {},
    }

    rec = TreatmentPlan(
        encounter_id=encounter_id,
        plan=plan_payload,
        status="suggested",
        clinician_approved=False,
        approval_note=None,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return _normalize_treatment_response(patient_id, rec.plan)


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

    plan = payload.plan or {}
    is_real_draft = bool(plan.get("drafted") and plan.get("order"))

    if is_real_draft:
        advance_workflow(
            db,
            encounter_id,
            treatment_drafted=True,
            stage="safety",
        )

    db.commit()
    db.refresh(rec)

    return _normalize_treatment_response(patient_id, rec.plan)