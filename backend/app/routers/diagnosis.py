from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import diagnosis_service
from app.schemas.diagnosis import DiagnosisUpsertRequest

router = APIRouter(tags=["diagnosis"])


@router.get("/api/diagnosis/{patientId}")
def get_diagnosis(patientId: str, db: Session = Depends(get_db)):
    return diagnosis_service.get_diagnosis(db, patientId)


@router.post("/api/diagnosis/{patientId}")
def upsert_diagnosis(patientId: str, payload: DiagnosisUpsertRequest, db: Session = Depends(get_db)):
    try:
        return diagnosis_service.upsert_diagnosis(db, patientId, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))