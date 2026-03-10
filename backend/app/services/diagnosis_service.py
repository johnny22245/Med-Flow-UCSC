# backend/app/services/diagnosis_service.py

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.diagnosis_record import DiagnosisRecord
from app.models.encounter import Encounter
from app.models.investigation_record import InvestigationRecord
from app.schemas.diagnosis import DiagnosisConfirmRequest, DiagnosisUpsertRequest, DifferentialItem
from app.services.diagnosis_pipeline import (
    build_case_context_from_records,
    generate_diagnosis_suggestion,
)
from app.services.encounter_service import get_active_encounter_id
from app.services.workflow_utils import advance_workflow


def _split_reasoning_to_list(text: str | None) -> list[str]:
    if not text:
        return []
    lines = []
    for raw in str(text).splitlines():
        x = raw.strip().lstrip("-").strip()
        if x:
            lines.append(x)
    return lines


def _record_to_ui_response(patient_id: str, rec: DiagnosisRecord) -> dict:
    evidence = rec.evidence or {}
    clinician_note = evidence.get("clinician_note") or ""

    ai_differential = rec.ai_differential or []
    diff_names = []
    rationale = []

    for item in ai_differential:
        if isinstance(item, dict):
            dx = item.get("dx")
            why = item.get("rationale")
            if dx:
                diff_names.append(dx)
            if why:
                rationale.append(why)

    reasoning_lines = _split_reasoning_to_list(rec.reasoning)
    if reasoning_lines:
        rationale = reasoning_lines

    if rec.confirmed_diagnosis:
        return {
            "patientId": patient_id,
            "confirmed": True,
            "diagnosis": {
                "primary": rec.confirmed_diagnosis,
                "confidence": rec.confidence or "medium",
                "differential": diff_names,
                "rationale": rationale,
                "clinicianNote": clinician_note,
            },
        }

    primary = diff_names[0] if diff_names else ""
    return {
        "patientId": patient_id,
        "confirmed": False,
        "suggestion": {
            "primary": primary,
            "confidence": rec.confidence or "medium",
            "differential": diff_names,
            "rationale": rationale,
        },
    }


def _get_records_for_context(db: Session, encounter_id):
    investigation = db.execute(
        select(InvestigationRecord).where(InvestigationRecord.encounter_id == encounter_id)
    ).scalars().first()

    diagnosis = db.execute(
        select(DiagnosisRecord).where(DiagnosisRecord.encounter_id == encounter_id)
    ).scalars().first()

    return investigation, diagnosis


def get_diagnosis(db: Session, patient_id: str) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        return {
            "patientId": patient_id,
            "confirmed": False,
            "suggestion": None,
        }

    rec = db.execute(
        select(DiagnosisRecord).where(DiagnosisRecord.encounter_id == encounter_id)
    ).scalars().first()

    if rec:
        return _record_to_ui_response(patient_id, rec)

    investigation_rec, _ = _get_records_for_context(db, encounter_id)
    case = build_case_context_from_records(
        patient_id=patient_id,
        investigation_record=investigation_rec,
        diagnosis_record=None,
    )

    generated = generate_diagnosis_suggestion(case)

    ai_differential = []
    for idx, dx in enumerate(generated.get("differential") or []):
        ai_differential.append(
            {
                "dx": dx,
                "prob": None,
                "rationale": generated["rationale"][idx] if idx < len(generated.get("rationale") or []) else None,
            }
        )

    if not ai_differential and generated.get("primary"):
        ai_differential = [
            {
                "dx": generated["primary"],
                "prob": None,
                "rationale": None,
            }
        ]

    rec = DiagnosisRecord(
        encounter_id=encounter_id,
        ai_differential=ai_differential,
        confirmed_diagnosis=None,
        confidence=generated.get("confidence", "medium"),
        reasoning="\n".join(generated.get("rationale") or []),
        clinician_override=False,
        override_reason=None,
        evidence=generated.get("evidence") or {},
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return _record_to_ui_response(patient_id, rec)


def confirm_diagnosis_from_ui(db: Session, patient_id: str, payload: DiagnosisConfirmRequest) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        raise ValueError(f"No active encounter for patient_id={patient_id}. Create patient first.")

    rec = db.execute(
        select(DiagnosisRecord).where(DiagnosisRecord.encounter_id == encounter_id)
    ).scalars().first()

    ai_differential = []
    for dx in payload.differential:
        ai_differential.append({"dx": dx, "prob": None, "rationale": None})

    if payload.primary and payload.primary not in [x["dx"] for x in ai_differential]:
        ai_differential = [{"dx": payload.primary, "prob": None, "rationale": None}] + ai_differential

    evidence = {}
    if rec and rec.evidence:
        evidence.update(rec.evidence)
    evidence["clinician_note"] = payload.clinicianNote or ""
    evidence["confirmed_via_ui"] = True

    if rec:
        rec.ai_differential = ai_differential
        rec.confirmed_diagnosis = payload.primary
        rec.confidence = payload.confidence
        rec.reasoning = "\n".join(payload.rationale or [])
        rec.clinician_override = False
        rec.override_reason = payload.clinicianNote or None
        rec.evidence = evidence
    else:
        rec = DiagnosisRecord(
            encounter_id=encounter_id,
            ai_differential=ai_differential,
            confirmed_diagnosis=payload.primary,
            confidence=payload.confidence,
            reasoning="\n".join(payload.rationale or []),
            clinician_override=False,
            override_reason=payload.clinicianNote or None,
            evidence=evidence,
        )
        db.add(rec)

    advance_workflow(
        db,
        encounter_id,
        diagnosis_confirmed=True,
        stage="treatment",
    )

    db.commit()
    db.refresh(rec)

    return _record_to_ui_response(patient_id, rec)


# keep this function if any old internal code still imports it
def upsert_diagnosis(db: Session, patient_id: str, payload: DiagnosisUpsertRequest) -> dict:
    encounter_id = get_active_encounter_id(db, patient_id)
    if not encounter_id:
        raise ValueError(f"No active encounter for patient_id={patient_id}. Create patient first.")

    rec = db.execute(
        select(DiagnosisRecord).where(DiagnosisRecord.encounter_id == encounter_id)
    ).scalars().first()

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

    if rec.confirmed_diagnosis:
        advance_workflow(
            db,
            encounter_id,
            diagnosis_confirmed=True,
            stage="treatment",
        )

    db.commit()
    db.refresh(rec)
    return _record_to_ui_response(patient_id, rec)