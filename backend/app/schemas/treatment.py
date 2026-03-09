from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class TreatmentUpsertRequest(BaseModel):
    plan: Dict[str, Any] = Field(..., description="Treatment plan payload (meds/procedures/followup/etc.)")
    status: Optional[str] = Field(default="draft", description="draft or final")
    clinician_approved: Optional[bool] = False
    approval_note: Optional[str] = None


class TreatmentResponse(BaseModel):
    patientId: str
    plan: Dict[str, Any] = {}
    status: str = "draft"
    clinician_approved: bool = False
    approval_note: Optional[str] = None


class TreatmentDraftRequest(BaseModel):
    patientId: str
    drafted: Optional[bool] = True
    order: Dict[str, Any]