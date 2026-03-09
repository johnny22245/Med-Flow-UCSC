from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class SummaryUpsertRequest(BaseModel):
    summary_text: str = Field(..., description="Narrative case summary")
    summary_structured: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured summary JSON")
    status: Optional[str] = Field(default="draft", description="draft or final")
    clinician_signed: Optional[bool] = False
    sign_note: Optional[str] = None


class SummaryResponse(BaseModel):
    patientId: str
    summary_text: str
    summary_structured: Dict[str, Any] = {}
    status: str = "draft"
    clinician_signed: bool = False
    sign_note: Optional[str] = None
    