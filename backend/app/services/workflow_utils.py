from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.workflow_state import WorkflowState


def get_workflow_state(db: Session, encounter_id) -> WorkflowState | None:
    return db.execute(
        select(WorkflowState).where(WorkflowState.encounter_id == encounter_id)
    ).scalars().first()


def advance_workflow(
    db: Session,
    encounter_id,
    *,
    stage: str | None = None,
    intake_completed: bool | None = None,
    investigation_completed: bool | None = None,
    diagnosis_confirmed: bool | None = None,
    treatment_drafted: bool | None = None,
    safety_cleared: bool | None = None,
    finalized: bool | None = None,
) -> None:
    wf = get_workflow_state(db, encounter_id)
    if not wf:
        return

    if stage is not None:
        wf.stage = stage
    if intake_completed is not None:
        wf.intake_completed = intake_completed
    if investigation_completed is not None:
        wf.investigation_completed = investigation_completed
    if diagnosis_confirmed is not None:
        wf.diagnosis_confirmed = diagnosis_confirmed
    if treatment_drafted is not None:
        wf.treatment_drafted = treatment_drafted
    if safety_cleared is not None:
        wf.safety_cleared = safety_cleared
    if finalized is not None:
        wf.finalized = finalized