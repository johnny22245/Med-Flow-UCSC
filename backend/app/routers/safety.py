# backend/app/routers/safety.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
import os
import json

router = APIRouter(prefix="/api/safety", tags=["safety"])

# backend/ is two levels up from backend/app/routers/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIXTURE_PATH = os.path.join(BASE_DIR, "data", "fixtures", "safety.json")

# In-memory: per patient safety config + override decisions (demo)
SAFETY_FIXTURES: Dict[str, Dict[str, Any]] = {}
OVERRIDES: Dict[str, Dict[str, Any]] = {}  # patient_id -> override payload


def load_fixtures() -> None:
    global SAFETY_FIXTURES
    if not os.path.exists(FIXTURE_PATH):
        SAFETY_FIXTURES = {}
        return
    with open(FIXTURE_PATH, "r") as f:
        SAFETY_FIXTURES = json.load(f)


@router.on_event("startup")
def _startup():
    load_fixtures()


# ----- Models -----
Severity = Literal["low", "medium", "high"]

class MedItem(BaseModel):
    drug: str
    dose: str
    route: str
    frequency: str
    duration: str


class TreatmentOrder(BaseModel):
    meds: List[MedItem] = Field(default_factory=list)
    notes: Optional[str] = ""


class SafetyCheckPayload(BaseModel):
    patientId: str
    patientAllergies: List[str] = Field(default_factory=list)
    patientMeds: List[str] = Field(default_factory=list)   # current meds from patient profile
    order: TreatmentOrder


class SafetyOverridePayload(BaseModel):
    patientId: str
    decision: Literal["override", "abort_edit"]
    overrideNote: Optional[str] = ""
    selectedSuggestion: Optional[str] = ""


# ----- Helpers -----
def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _drug_in_list(drug: str, meds: List[str]) -> bool:
    d = _norm(drug)
    return any(_norm(x) == d for x in meds)


def _order_drugs(order: Dict[str, Any]) -> List[str]:
    meds = (order or {}).get("meds", [])
    return [m.get("drug", "") for m in meds if isinstance(m, dict)]


def _is_allergy_conflict(patient_allergies: List[str], order_drugs: List[str]) -> bool:
    allergies_norm = {_norm(a) for a in (patient_allergies or [])}
    for od in order_drugs:
        if _norm(od) in allergies_norm:
            return True
    return False


# ----- Endpoints -----
@router.post("/check")
def run_safety_check(payload: SafetyCheckPayload):
    """
    Demo safety check:
    - If any HIGH severity rule matches => status 'blocked' and requires doctor action.
    - We match against fixture interactions list for the patient.
    - Allergy conflicts detected via patientAllergies vs order meds.
    """
    fx = SAFETY_FIXTURES.get(payload.patientId)
    if not fx:
        raise HTTPException(status_code=404, detail="No safety fixture found for patient")

    rules = fx.get("rules", {"block_on_high_severity": True, "require_override_note": True})
    interactions = fx.get("interactions", [])
    safe_alts = fx.get("safe_alternatives", [])

    order_dict = payload.order.model_dump()
    order_drugs = _order_drugs(order_dict)

    alerts: List[Dict[str, Any]] = []

    # 1) Fixture-based DDI / custom checks
    # For demo: treat an interaction as triggered if:
    # - drugB is in the order AND (drugA is in patient current meds OR drugA is also in order)
    for it in interactions:
        drugA = it.get("drugA", "")
        drugB = it.get("drugB", "")
        severity = it.get("severity", "medium")
        it_type = it.get("type", "DDI")

        triggered = False
        if _drug_in_list(drugB, order_drugs):
            # drugA might be in patient current meds, or also in the order
            if _drug_in_list(drugA, payload.patientMeds) or _drug_in_list(drugA, order_drugs):
                triggered = True

        # Special case: ALLERGY rule in fixture can be triggered by allergies too.
        if it_type == "ALLERGY" and _drug_in_list(drugB, order_drugs):
            # if patient is allergic to drugA (usually same as drugB)
            if _drug_in_list(drugA, payload.patientAllergies):
                triggered = True

        if triggered:
            alerts.append({
                "type": it_type,
                "drugA": drugA,
                "drugB": drugB,
                "severity": severity,
                "message": it.get("message", ""),
                "suggestions": it.get("suggestions", []),
            })

    # 2) Generic allergy check (even if not present in fixture interactions)
    if _is_allergy_conflict(payload.patientAllergies, order_drugs):
        # Only add if not already present as ALLERGY alert
        has_allergy_alert = any(_norm(a.get("type","")) == "allergy" for a in alerts)
        if not has_allergy_alert:
            alerts.append({
                "type": "ALLERGY",
                "drugA": "Patient Allergy",
                "drugB": "Order contains allergen",
                "severity": "high",
                "message": "Order includes a medication matching the patient's allergy list (demo). Remove/replace the drug.",
                "suggestions": ["Remove allergen drug", "Choose alternative medication"],
            })

    # Decide status
    block_on_high = bool(rules.get("block_on_high_severity", True))
    highest = "low"
    sev_rank = {"low": 1, "medium": 2, "high": 3}
    for a in alerts:
        s = a.get("severity", "medium")
        if sev_rank.get(s, 2) > sev_rank.get(highest, 1):
            highest = s

    status = "ok"
    if alerts:
        if (highest == "high" and block_on_high) or highest in ["medium", "high"]:
            status = "blocked"
        else:
            status = "warn"

    return {
        "patientId": payload.patientId,
        "status": status,
        "highestSeverity": highest,
        "alerts": alerts,
        "safeAlternatives": safe_alts,
        "rules": rules,
        "previousOverride": OVERRIDES.get(payload.patientId)  # for refresh convenience
    }


@router.post("/decision")
def submit_safety_decision(payload: SafetyOverridePayload):
    """
    Stores doctor decision:
    - abort_edit: go back to treatment stage
    - override: proceed (requires note if fixture requires_override_note)
    """
    fx = SAFETY_FIXTURES.get(payload.patientId)
    if not fx:
        raise HTTPException(status_code=404, detail="No safety fixture found for patient")

    rules = fx.get("rules", {"require_override_note": True})
    require_note = bool(rules.get("require_override_note", True))

    if payload.decision == "override":
        if require_note and not (payload.overrideNote or "").strip():
            raise HTTPException(status_code=400, detail="Override note is required")

    OVERRIDES[payload.patientId] = payload.model_dump()
    return {"ok": True, "patientId": payload.patientId, "decision": payload.decision}


@router.post("/reset/{patient_id}")
def reset_safety(patient_id: str):
    if patient_id in OVERRIDES:
        del OVERRIDES[patient_id]
    return {"ok": True, "patientId": patient_id, "overrideCleared": True}