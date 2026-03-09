from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.patient import Patient
from app.models.encounter import Encounter
from app.models.workflow_state import WorkflowState
from app.schemas.patients import PatientCreateRequest, PatientResponse

from app.services.encounter_service import get_active_encounter_id
from app.services.workflow_utils import get_workflow_state, advance_workflow

def _to_response(p: Patient) -> PatientResponse:
    return PatientResponse(
        id=p.id,
        name=p.name,
        age=p.age,
        sex=p.sex,
        allergies=p.allergies or [],
        meds=p.meds or [],
        intake=p.intake,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
    )


def upsert_patient(db: Session, req: PatientCreateRequest) -> PatientResponse:
    # find existing
    p = db.get(Patient, req.id)

    if p:
        # update
        p.name = req.name
        p.age = req.age
        p.sex = req.sex
        p.intake = req.intake.model_dump()
        
        # Mark intake complete if consent is true (do NOT move stage backwards)
        if req.intake and req.intake.consent is True:
            encounter_id = get_active_encounter_id(db, p.id)
            if encounter_id:
                wf = get_workflow_state(db, encounter_id)
                # only advance stage if still in intake
                if wf and (wf.stage == "intake" or wf.stage is None):
                    advance_workflow(
                        db,
                        encounter_id,
                        intake_completed=True,
                        stage="triage",
                    )
                else:
                    # still mark intake completed even if already beyond intake
                    advance_workflow(
                        db,
                        encounter_id,
                        intake_completed=True,
                    )
        
        # only overwrite if explicitly provided
        if req.allergies is not None:
            p.allergies = req.allergies
        if req.meds is not None:
            p.meds = req.meds
        if req.extra is not None:
            p.extra = req.extra
    else:
        p = Patient(
            id=req.id,
            name=req.name,
            age=req.age,
            sex=req.sex,
            intake=req.intake.model_dump(),
            allergies=req.allergies or [],
            meds=req.meds or [],
            extra=req.extra,
        )
        db.add(p)
        db.flush()

        # create active encounter + workflow state for this patient
        enc = Encounter(patient_id=p.id, status="active")
        db.add(enc)
        db.flush()

        wf = WorkflowState(encounter_id=enc.id, stage="intake")
        db.add(wf)
        # Mark intake complete if consent is true (safe stage advance)
        if req.intake and req.intake.consent is True:
            advance_workflow(
                db,
                enc.id,
                intake_completed=True,
                stage="triage",
            )

    db.commit()
    db.refresh(p)
    return _to_response(p)


def get_patient(db: Session, patient_id: str) -> PatientResponse | None:
    p = db.get(Patient, patient_id)
    if not p:
        return None
    return _to_response(p)


def list_patients(db: Session) -> list[PatientResponse]:
    rows = db.execute(select(Patient).order_by(Patient.created_at.desc())).scalars().all()
    return [_to_response(p) for p in rows]