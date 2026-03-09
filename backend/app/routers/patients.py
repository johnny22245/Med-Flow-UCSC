from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.schemas.patients import PatientCreateRequest, PatientResponse
from app.services import patient_service
from app.db.session import get_db

router = APIRouter(tags=["patients"])


@router.post("/patients", response_model=PatientResponse)
def create_patient(req: PatientCreateRequest, db: Session = Depends(get_db)):
    return patient_service.upsert_patient(db, req)


@router.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = patient_service.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/patients", response_model=list[PatientResponse])
def list_patients(db: Session = Depends(get_db)):
    return patient_service.list_patients(db)