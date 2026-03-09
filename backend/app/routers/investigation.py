from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import investigation_service
from app.schemas.investigation import InvestigationPayload

router = APIRouter(tags=["investigation"])


@router.get("/api/investigation/{patientId}")
def get_investigation(patientId: str, db: Session = Depends(get_db)):
    return investigation_service.get_investigation(db, patientId)


@router.post("/api/investigation/{patientId}")
def save_investigation(patientId: str, payload: InvestigationPayload, db: Session = Depends(get_db)):
    # optional: enforce patient_id consistency
    if payload.patient_id != patientId:
        raise HTTPException(status_code=400, detail="payload.patient_id must match patientId in path")

    try:
        return investigation_service.upsert_investigation_payload(db, patientId, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))