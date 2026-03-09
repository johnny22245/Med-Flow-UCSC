from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import safety_service
from app.schemas.safety import SafetyUpsertRequest

router = APIRouter(tags=["safety"])


@router.get("/api/safety/{patientId}")
def get_safety(patientId: str, db: Session = Depends(get_db)):
    return safety_service.get_safety(db, patientId)


@router.post("/api/safety/{patientId}")
def upsert_safety(patientId: str, payload: SafetyUpsertRequest, db: Session = Depends(get_db)):
    try:
        return safety_service.upsert_safety(db, patientId, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))