from fastapi import APIRouter, HTTPException
from app.schemas.investigation import InvestigationPayload
from app.services.investigation_service import investigation_service

router = APIRouter(prefix="/api/investigation", tags=["investigation"])

@router.get("/{patient_id}", response_model=InvestigationPayload)
def get_investigation(patient_id: str):
    data = investigation_service.get_by_patient_id(patient_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"No investigation data for patient_id={patient_id}")
    return data
