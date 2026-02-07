from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, List

from app.schemas.patients import PatientCreateRequest, PatientResponse

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "patients.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PatientStore:
    """
    Dummy patient store:
    - loads initial fixture JSON
    - keeps everything in memory
    - supports upsert + fetch
    """

    def __init__(self) -> None:
        self._store: Dict[str, PatientResponse] = {}
        self._load_fixtures()

    def _load_fixtures(self) -> None:
        if not FIXTURE_PATH.exists():
            return
        raw = json.loads(FIXTURE_PATH.read_text())
        for item in raw.get("patients", []):
            # Ensure timestamps exist
            item.setdefault("created_at", now_iso())
            item.setdefault("updated_at", now_iso())
            p = PatientResponse.model_validate(item)
            self._store[p.id] = p

    def upsert_patient(self, req: PatientCreateRequest) -> PatientResponse:
        existing = self._store.get(req.id)
        created_at = existing.created_at if existing else now_iso()

        allergies = req.allergies if req.allergies is not None else (existing.allergies if existing else ["Aspirin"])
        meds = req.meds if req.meds is not None else (existing.meds if existing else ["Valproic Acid"])

        p = PatientResponse(
            id=req.id,
            name=req.name,
            age=req.age,
            sex=req.sex,
            allergies=allergies,
            meds=meds,
            intake=req.intake,
            created_at=created_at,
            updated_at=now_iso(),
        )
        self._store[p.id] = p
        return p

    def get_patient(self, patient_id: str) -> Optional[PatientResponse]:
        return self._store.get(patient_id)

    def list_patients(self) -> List[PatientResponse]:
        # Stable ordering for demos
        return sorted(self._store.values(), key=lambda x: x.updated_at, reverse=True)


patient_store = PatientStore()
