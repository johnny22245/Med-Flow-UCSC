# backend/app/routers/treatment.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
import os

router = APIRouter(prefix="/api/treatment", tags=["treatment"])

# --- Fixture path: backend/data/fixtures/treatment.json ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # backend/
FIXTURE_PATH = os.path.join(BASE_DIR, "data", "fixtures", "treatment.json")

# --- In-memory stores (demo) ---
SUGGESTED_PLANS: Dict[str, Dict[str, Any]] = {}
DRAFT_ORDERS: Dict[str, Dict[str, Any]] = {}


def load_fixtures() -> None:
    """Load suggested treatment plans from backend/data/fixtures/treatment.json"""
    global SUGGESTED_PLANS
    if not os.path.exists(FIXTURE_PATH):
        SUGGESTED_PLANS = {}
        return

    with open(FIXTURE_PATH, "r") as f:
        raw = json.load(f)

    # Normalize: patient_id -> suggestedPlan
    SUGGESTED_PLANS = {pid: payload.get("suggestedPlan", {}) for pid, payload in raw.items()}


@router.on_event("startup")
def _startup():
    load_fixtures()


# --- Models ---
class MedItem(BaseModel):
    drug: str
    dose: str
    route: str
    frequency: str
    duration: str


class SuggestedPlan(BaseModel):
    title: str
    meds: List[MedItem] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class TreatmentOrder(BaseModel):
    meds: List[MedItem] = Field(default_factory=list)
    notes: Optional[str] = ""


class DraftTreatmentPayload(BaseModel):
    patientId: str
    drafted: bool = True
    order: TreatmentOrder


# --- Endpoints ---
@router.get("/plan/{patient_id}")
def get_treatment_plan(patient_id: str):
    """
    Returns a suggested plan for the patient, unless a draft order already exists.
    If drafted exists: returns drafted order (drafted=true) so UI can rehydrate on refresh.
    """
    if patient_id in DRAFT_ORDERS:
        return {
            "patientId": patient_id,
            "drafted": True,
            "order": DRAFT_ORDERS[patient_id],
        }

    plan = SUGGESTED_PLANS.get(patient_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No treatment plan fixture found for patient")

    return {
        "patientId": patient_id,
        "drafted": False,
        "suggestedPlan": plan,
    }


@router.post("/draft")
def draft_treatment_order(payload: DraftTreatmentPayload):
    """
    Stores a draft treatment order in-memory (demo).
    """
    DRAFT_ORDERS[payload.patientId] = {
        "meds": [m.model_dump() for m in payload.order.meds],
        "notes": payload.order.notes or "",
        "drafted": payload.drafted,
    }

    return {
        "ok": True,
        "patientId": payload.patientId,
        "drafted": True,
        "order": DRAFT_ORDERS[payload.patientId],
    }


@router.post("/reset/{patient_id}")
def reset_treatment_order(patient_id: str):
    """
    Demo helper: clears drafted order so the suggested plan shows again.
    """
    if patient_id in DRAFT_ORDERS:
        del DRAFT_ORDERS[patient_id]
    return {"ok": True, "patientId": patient_id, "draftCleared": True}