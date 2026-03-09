from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class LabResult(BaseModel):
    name: str
    value: float
    unit: str
    ref_range: str
    flag: str = Field(..., description="N=normal, H=high, L=low")

class LabPanel(BaseModel):
    panel: str
    collected_at: str
    results: List[LabResult]

class AiBox(BaseModel):
    label: str
    x: float
    y: float
    w: float
    h: float
    confidence: float

class AiFindings(BaseModel):
    summary: str
    boxes: List[AiBox] = []

class ImagingStudy(BaseModel):
    study_id: str
    modality: str
    body_part: str
    acquired_at: str
    summary: str
    radiology_impression: str
    ai_findings: AiFindings
    image_url: str

class InvestigationPayload(BaseModel):
    patient_id: str
    labs: List[LabPanel]
    imaging: List[ImagingStudy]
    status: str
class InvestigationRecordResponse(BaseModel):
    patientId: str
    payload: Optional[InvestigationPayload] = None