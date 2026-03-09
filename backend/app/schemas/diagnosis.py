from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ConfidenceLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class DifferentialItem(BaseModel):
    dx: str = Field(..., description="Diagnosis name")
    prob: Optional[float] = Field(default=None, description="Optional probability 0..1")
    rationale: Optional[str] = Field(default=None, description="Short reason")


class DiagnosisUpsertRequest(BaseModel):
    ai_differential: Optional[List[DifferentialItem]] = None

    confirmed_diagnosis: Optional[str] = None
    confidence: Optional[ConfidenceLevel] = None
    reasoning: Optional[str] = None

    clinician_override: Optional[bool] = None
    override_reason: Optional[str] = None

    evidence: Optional[Dict[str, Any]] = None


class DiagnosisResponse(BaseModel):
    patientId: str
    ai_differential: List[Dict[str, Any]] = []
    confirmed_diagnosis: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    clinician_override: bool = False
    override_reason: Optional[str] = None
    evidence: Dict[str, Any] = {}