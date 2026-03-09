from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.patient import Patient
from app.models.encounter import Encounter
from app.models.workflow_state import WorkflowState

from app.models.investigation_record import InvestigationRecord
from app.models.diagnosis_record import DiagnosisRecord
from app.models.treatment_plan import TreatmentPlan
from app.models.safety_check import SafetyCheck
from app.models.case_summary import CaseSummary


def get_case_snapshot(db: Session, patient_id: str) -> dict:
    patient = db.get(Patient, patient_id)

    enc = db.execute(
        select(Encounter)
        .where(Encounter.patient_id == patient_id)
        .where(Encounter.status == "active")
        .order_by(Encounter.created_at.desc())
        .limit(1)
    ).scalars().first()

    if not enc:
        return {
            "patientId": patient_id,
            "encounterId": None,
            "workflow": None,
            "records": {
                "patient_exists": bool(patient),
                "investigation_exists": False,
                "diagnosis_exists": False,
                "treatment_exists": False,
                "safety_exists": False,
                "summary_exists": False,
            },
        }

    wf = db.execute(
        select(WorkflowState).where(WorkflowState.encounter_id == enc.id)
    ).scalars().first()

    inv_exists = db.execute(
        select(InvestigationRecord.id).where(InvestigationRecord.encounter_id == enc.id)
    ).first() is not None

    dx_exists = db.execute(
        select(DiagnosisRecord.id).where(DiagnosisRecord.encounter_id == enc.id)
    ).first() is not None

    tx_exists = db.execute(
        select(TreatmentPlan.id).where(TreatmentPlan.encounter_id == enc.id)
    ).first() is not None

    safety_exists = db.execute(
        select(SafetyCheck.id).where(SafetyCheck.encounter_id == enc.id)
    ).first() is not None

    summary_exists = db.execute(
        select(CaseSummary.id).where(CaseSummary.encounter_id == enc.id)
    ).first() is not None

    return {
        "patientId": patient_id,
        "encounterId": str(enc.id),
        "workflow": None if not wf else {
            "stage": wf.stage,
            "intake_completed": wf.intake_completed,
            "investigation_completed": wf.investigation_completed,
            "diagnosis_confirmed": wf.diagnosis_confirmed,
            "treatment_drafted": wf.treatment_drafted,
            "safety_cleared": wf.safety_cleared,
            "finalized": wf.finalized,
        },
        "records": {
            "patient_exists": bool(patient),
            "investigation_exists": inv_exists,
            "diagnosis_exists": dx_exists,
            "treatment_exists": tx_exists,
            "safety_exists": safety_exists,
            "summary_exists": summary_exists,
        },
    }