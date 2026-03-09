from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.triage import (
    TriageStartRequest,
    TriageAnswerRequest,
    TriageResponse,
)
from app.services import triage_service

router = APIRouter(prefix="/api/triage", tags=["triage"])


@router.post("/start", response_model=TriageResponse)
def start_triage(req: TriageStartRequest, db: Session = Depends(get_db)):
    try:
        return triage_service.start_triage(db, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/answer", response_model=TriageResponse)
def answer_triage(
    session_id: str,
    req: TriageAnswerRequest,
    db: Session = Depends(get_db),
):
    try:
        return triage_service.answer_triage(db, session_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))