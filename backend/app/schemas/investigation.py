from pydantic import BaseModel, Field
from typing import List, Optional

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


# ---------------------------
# existing investigation payload
# ---------------------------
class InvestigationPayload(BaseModel):
    patient_id: str
    labs: List[LabPanel]
    imaging: List[ImagingStudy]
    status: str


class InvestigationRecordResponse(BaseModel):
    patientId: str
    payload: Optional[InvestigationPayload] = None


# ---------------------------
# new test-ordering payloads
# ---------------------------
class OrderedTestItem(BaseModel):
    code: str
    name: str
    group: str
    source: str = "ai"
    priority: str = "routine"
    reason: str = ""
    selected: bool = True


class InvestigationOrdersPayload(BaseModel):
    patient_id: str
    suggested_tests: List[OrderedTestItem] = []
    ordered_tests: List[OrderedTestItem] = []
    notes: Optional[str] = None
    confirmed: bool = True
    confirmed_at: Optional[str] = None


class InvestigationOrdersResponse(BaseModel):
    patientId: str
    encounterId: str
    suggested_tests: List[OrderedTestItem]
    ordered_tests: List[OrderedTestItem]
    notes: Optional[str] = None
    confirmed: bool = True