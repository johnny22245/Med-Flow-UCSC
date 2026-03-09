from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import treatment_service
from app.schemas.treatment import TreatmentUpsertRequest, TreatmentDraftRequest

router = APIRouter(tags=["treatment"])


@router.get("/api/treatment/{patientId}")
def get_treatment(patientId: str, db: Session = Depends(get_db)):
    return treatment_service.get_treatment(db, patientId)


# NEW: UI-friendly endpoint
@router.post("/api/treatment/draft")
def draft_treatment(payload: TreatmentDraftRequest, db: Session = Depends(get_db)):
    """
    Accepts the UI payload shape:
      { patientId, drafted, order: {...} }
    Converts it into TreatmentUpsertRequest:
      { plan: {...}, status: "draft", ... }
    """
    upsert_payload = TreatmentUpsertRequest(
        plan={
            "patientId": payload.patientId,  # optional, can be removed if you don't want duplication
            "drafted": payload.drafted,
            "order": payload.order,
        },
        status="draft",
        clinician_approved=False,
        approval_note=None,
    )

    try:
        return treatment_service.upsert_treatment(db, payload.patientId, upsert_payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/treatment/{patientId}")
def upsert_treatment(patientId: str, payload: TreatmentUpsertRequest, db: Session = Depends(get_db)):
    try:
        return treatment_service.upsert_treatment(db, patientId, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))