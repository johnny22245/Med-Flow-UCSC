from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SafetyFinding(BaseModel):
    type: str = Field(..., description="interaction | allergy | contraindication | dose | other")
    severity: str = Field(..., description="low | moderate | high | critical")
    message: str = Field(..., description="Human readable warning")
    evidence: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None


class SafetyUpsertRequest(BaseModel):
    findings: Optional[List[SafetyFinding]] = None
    status: Optional[str] = Field(default=None, description="pending | needs_review | cleared | blocked")
    clinician_approved: Optional[bool] = None
    approval_note: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None


class SafetyResponse(BaseModel):
    patientId: str
    findings: List[Dict[str, Any]] = []
    status: str = "pending"
    clinician_approved: bool = False
    approval_note: Optional[str] = None
    provenance: Dict[str, Any] = {}