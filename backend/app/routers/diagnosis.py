from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any
import json
import os

router = APIRouter(prefix="/api/diagnosis", tags=["diagnosis"])

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # backend/
FIXTURE_PATH = os.path.join(BASE_DIR, "data", "fixtures", "diagnosis.json")

# In-memory stores (demo)
SUGGESTIONS: Dict[str, Dict[str, Any]] = {}
CONFIRMED: Dict[str, Dict[str, Any]] = {}


def load_fixtures():
    global SUGGESTIONS
    if os.path.exists(FIXTURE_PATH):
        with open(FIXTURE_PATH, "r") as f:
            data = json.load(f)
        # Normalize: patient_id -> suggestion
        SUGGESTIONS = {pid: payload.get("suggestion", {}) for pid, payload in data.items()}


class DiagnosisSuggestion(BaseModel):
    primary: str
    differential: List[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    rationale: List[str] = Field(default_factory=list)


class DiagnosisConfirmPayload(BaseModel):
    patientId: str
    primary: str
    differential: List[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    rationale: List[str] = Field(default_factory=list)
    clinicianNote: Optional[str] = ""
    confirmed: bool = True


@router.on_event("startup")
def _startup():
    load_fixtures()


@router.get("/suggest/{patient_id}")
def get_suggestion(patient_id: str):
    # If already confirmed, return the confirmed dx (makes UI refresh simple)
    if patient_id in CONFIRMED:
        return {"patientId": patient_id, "confirmed": True, "diagnosis": CONFIRMED[patient_id]}

    sug = SUGGESTIONS.get(patient_id)
    if not sug:
        raise HTTPException(status_code=404, detail="No diagnosis suggestion fixture found for patient")
    return {"patientId": patient_id, "confirmed": False, "suggestion": sug}


@router.post("/confirm")
def confirm_diagnosis(payload: DiagnosisConfirmPayload):
    CONFIRMED[payload.patientId] = {
        "primary": payload.primary,
        "differential": payload.differential,
        "confidence": payload.confidence,
        "rationale": payload.rationale,
        "clinicianNote": payload.clinicianNote,
        "confirmed": payload.confirmed
    }
    return {"ok": True, "patientId": payload.patientId, "diagnosis": CONFIRMED[payload.patientId]}