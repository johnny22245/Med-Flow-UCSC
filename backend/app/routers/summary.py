from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import summary_service
from app.schemas.summary import SummaryUpsertRequest

router = APIRouter(tags=["summary"])


@router.get("/api/summary/{patientId}")
def get_summary(patientId: str, db: Session = Depends(get_db)):
    return summary_service.get_summary(db, patientId)


@router.post("/api/summary/{patientId}")
def upsert_summary(patientId: str, payload: SummaryUpsertRequest, db: Session = Depends(get_db)):
    try:
        return summary_service.upsert_summary(db, patientId, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))