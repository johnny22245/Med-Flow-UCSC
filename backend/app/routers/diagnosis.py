# backend/app/routers/diagnosis.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import diagnosis_service
from app.schemas.diagnosis import DiagnosisConfirmRequest

router = APIRouter(tags=["diagnosis"])


@router.get("/api/diagnosis/{patientId}")
def get_diagnosis(patientId: str, db: Session = Depends(get_db)):
    return diagnosis_service.get_diagnosis(db, patientId)


@router.post("/api/diagnosis/{patientId}")
def confirm_diagnosis(patientId: str, payload: DiagnosisConfirmRequest, db: Session = Depends(get_db)):
    if payload.patientId != patientId:
        raise HTTPException(status_code=400, detail="payload.patientId must match patientId in path")

    try:
        return diagnosis_service.confirm_diagnosis_from_ui(db, patientId, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))