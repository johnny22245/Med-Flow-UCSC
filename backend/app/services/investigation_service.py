import json
from pathlib import Path
from typing import Dict, Any, Optional

_FIXTURE_PATH = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "investigation.json"

class InvestigationService:
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._seed_from_fixtures()

    def _seed_from_fixtures(self) -> None:
        if _FIXTURE_PATH.exists():
            self._store = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
        else:
            self._store = {}

    def get_by_patient_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(patient_id)

investigation_service = InvestigationService()
