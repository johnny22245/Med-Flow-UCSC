from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.case_service import get_case_snapshot

router = APIRouter(tags=["case"])


@router.get("/api/case/{patientId}")
def case_snapshot(patientId: str, db: Session = Depends(get_db)):
    return get_case_snapshot(db, patientId)