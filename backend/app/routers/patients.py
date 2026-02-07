from fastapi import APIRouter, HTTPException
from app.schemas.patients import PatientCreateRequest, PatientResponse
from app.services.patient_service import patient_store

router = APIRouter(tags=["patients"])


@router.post("/patients", response_model=PatientResponse)
def create_patient(req: PatientCreateRequest):
    """
    Create/update a patient profile + intake payload.
    - Uses dummy in-memory store.
    - Mirrors the frontend intake payload shape.
    """
    created = patient_store.upsert_patient(req)
    return created


@router.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: str):
    patient = patient_store.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/patients", response_model=list[PatientResponse])
def list_patients():
    """
    Small helper for demo debugging.
    """
    return patient_store.list_patients()
