from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
import os
import json
from datetime import datetime

router = APIRouter(prefix="/api/case-summary", tags=["case_summary"])

# backend/ is two levels up from backend/app/routers/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CASES_DIR = os.path.join(BASE_DIR, "data", "cases")
CASE_FILE = os.path.join(CASES_DIR, "case_summaries.json")


def _ensure_store():
    os.makedirs(CASES_DIR, exist_ok=True)
    if not os.path.exists(CASE_FILE):
        with open(CASE_FILE, "w") as f:
            json.dump({}, f, indent=2)


def _read_store() -> Dict[str, Any]:
    _ensure_store()
    with open(CASE_FILE, "r") as f:
        try:
            return json.load(f) or {}
        except json.JSONDecodeError:
            return {}


def _write_store(data: Dict[str, Any]) -> None:
    _ensure_store()
    with open(CASE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# -------- Models --------
class MedItem(BaseModel):
    drug: str
    dose: str
    route: str
    frequency: str
    duration: str


class DiagnosisBlock(BaseModel):
    primary: str
    differential: List[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    rationale: List[str] = Field(default_factory=list)
    clinicianNote: Optional[str] = ""
    confirmed: bool = True


class TreatmentOrder(BaseModel):
    meds: List[MedItem] = Field(default_factory=list)
    notes: Optional[str] = ""


class SafetyDecision(BaseModel):
    decision: Literal["override", "abort_edit", "none"] = "none"
    overrideNote: Optional[str] = ""
    selectedSuggestion: Optional[str] = ""


class PatientSnapshot(BaseModel):
    id: str
    name: str
    age: int
    sex: str
    allergies: List[str] = Field(default_factory=list)
    meds: List[str] = Field(default_factory=list)


class FinalizeCasePayload(BaseModel):
    patient: PatientSnapshot
    diagnosis: DiagnosisBlock
    order: TreatmentOrder
    safety: SafetyDecision
    finalClinicianNote: Optional[str] = ""  # extra wrap-up note for summary


@router.get("/{patient_id}")
def get_case_summary(patient_id: str):
    store = _read_store()
    if patient_id not in store:
        raise HTTPException(status_code=404, detail="No case summary found for patient")
    return store[patient_id]


@router.post("/finalize")
def finalize_case(payload: FinalizeCasePayload):
    store = _read_store()

    record = {
        "patientId": payload.patient.id,
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "patient": payload.patient.model_dump(),
        "diagnosis": payload.diagnosis.model_dump(),
        "order": payload.order.model_dump(),
        "safety": payload.safety.model_dump(),
        "finalClinicianNote": payload.finalClinicianNote or "",
        "status": "finalized"
    }

    # Upsert by patientId (demo simplicity)
    store[payload.patient.id] = record
    _write_store(store)

    return {"ok": True, "patientId": payload.patient.id, "savedTo": CASE_FILE, "record": record}