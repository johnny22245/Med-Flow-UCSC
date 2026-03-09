from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TriageStartRequest(BaseModel):
    patient_id: str = Field(..., description="Patient id / MRN")


class TriageQAItem(BaseModel):
    question: str
    answer: str


class TriageAnswerRequest(BaseModel):
    answers: List[TriageQAItem] = Field(
        ...,
        description="Batch of answered clarifying questions"
    )


class TriageChatMessage(BaseModel):
    role: str
    text: str


class TriageResponse(BaseModel):
    session_id: str
    patient_id: str
    status: str
    thinking: bool = False

    current_question: Optional[str] = None
    chat_history: List[TriageChatMessage] = []

    summary: Optional[str] = None
    urgency: Optional[str] = None
    suggested_tests: List[Dict[str, Any]] = []
    missing_info: List[str] = []
    raw_output: Optional[Dict[str, Any]] = None