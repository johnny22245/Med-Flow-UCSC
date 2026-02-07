from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Vitals(BaseModel):
    temp_c: float = Field(..., description="Temperature in Celsius")
    hr_bpm: int = Field(..., description="Heart rate in bpm")
    bp_sys: int = Field(..., description="Systolic BP")
    bp_dia: int = Field(..., description="Diastolic BP")
    spo2_pct: int = Field(..., description="SpO2 percent")


class IntakePayload(BaseModel):
    chief_complaint: str
    symptoms_text: str
    duration: str
    severity_0_10: int = Field(..., ge=0, le=10)
    vitals: Vitals
    consent: bool


class PatientCreateRequest(BaseModel):
    id: str = Field(..., description="MRN / internal patient id")
    name: str
    age: int
    sex: str

    intake: IntakePayload

    # Optional clinical context (dummy defaults)
    allergies: Optional[List[str]] = None
    meds: Optional[List[str]] = None

    # Extension point for later stages
    extra: Optional[Dict[str, Any]] = None


class PatientResponse(BaseModel):
    id: str
    name: str
    age: int
    sex: str

    allergies: List[str] = []
    meds: List[str] = []

    intake: IntakePayload
    created_at: str
    updated_at: str
