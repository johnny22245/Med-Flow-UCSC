from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.patient import Patient
from app.models.triage_session import TriageSession
from app.schemas.triage import (
    TriageAnswerRequest,
    TriageResponse,
    TriageStartRequest,
    TriageChatMessage,
)
from app.services.encounter_service import get_active_encounter_id
from app.services.workflow_utils import advance_workflow

from app.agents.triage.langgraph_triage import triage_graph


def _build_initial_case(patient: Patient) -> str:
    intake = patient.intake or {}
    vitals = intake.get("vitals", {}) or {}

    lines = [
        f"Patient name: {patient.name}",
        f"Age: {patient.age}",
        f"Sex: {patient.sex}",
        f"Chief complaint: {intake.get('chief_complaint', '')}",
        f"Symptoms: {intake.get('symptoms_text', '')}",
        f"Duration: {intake.get('duration', '')}",
        f"Severity: {intake.get('severity_0_10', '')}/10",
        (
            "Vitals: "
            f"Temp {vitals.get('temp_c', 'NA')} C, "
            f"HR {vitals.get('hr_bpm', 'NA')} bpm, "
            f"BP {vitals.get('bp_sys', 'NA')}/{vitals.get('bp_dia', 'NA')} mmHg, "
            f"SpO2 {vitals.get('spo2_pct', 'NA')}%"
        ),
        f"Allergies: {', '.join(patient.allergies or []) if patient.allergies else 'None'}",
        f"Current medications: {', '.join(patient.meds or []) if patient.meds else 'None'}",
    ]

    return "\n".join(lines)


def _invoke_triage_graph(initial_case: str, qa_history: list, round_count: int) -> dict:
    state = {
        "initial_case": initial_case,
        "qa_history": qa_history,
        "round_count": round_count,
        "max_rounds": 2,
        "latest_raw_output": "",
        "triage_output": {},
        "status": "start",
        "doctor_approved": False,
    }
    return triage_graph.invoke(state)


def _extract_triage_data(graph_state: dict) -> dict:
    parsed = graph_state.get("triage_output", {}) or {}

    if not parsed.get("ok"):
        raise ValueError(
            f"Triage model output parse failed: {parsed.get('error', 'unknown parse error')}"
        )

    data = parsed.get("data", {}) or {}
    return data


def _extract_current_question(data: dict) -> str | None:
    questions = data.get("clarifying_questions") or []
    if not questions:
        return None

    first = questions[0]
    if isinstance(first, dict):
        return first.get("question")
    return str(first)


def _extract_summary_text(data: dict) -> str | None:
    summary = data.get("summary", {}) or {}

    parts = []

    presenting = summary.get("presenting_symptoms") or []
    if presenting:
        parts.append(f"Symptoms: {', '.join(presenting)}")

    concerns = summary.get("possible_concerns") or []
    if concerns:
        parts.append(f"Possible concerns: {', '.join(concerns)}")

    missing = summary.get("missing_info") or []
    if missing:
        parts.append(f"Missing info: {', '.join(missing)}")

    urgency = summary.get("urgency")
    if urgency:
        parts.append(f"Urgency: {urgency}")

    if not parts:
        return None

    return " | ".join(parts)


def _extract_urgency(data: dict) -> str | None:
    summary = data.get("summary", {}) or {}
    return summary.get("urgency")


def _extract_missing_info(data: dict) -> list[str]:
    summary = data.get("summary", {}) or {}
    return summary.get("missing_info") or []


def _extract_suggested_tests(data: dict) -> list[dict]:
    tests = data.get("suggested_tests") or []

    # normalize to UI-friendly shape
    normalized = []
    for item in tests:
        if isinstance(item, dict):
            normalized.append(item)
        else:
            normalized.append({
                "name": str(item),
                "reason": "",
                "selected": True,
            })

    return normalized


def _to_chat_history(session: TriageSession, current_question: str | None = None):
    messages = []

    for item in session.qa_history or []:
        q = item.get("question")
        a = item.get("answer")

        if q:
            messages.append(TriageChatMessage(role="assistant", text=q))
        if a:
            messages.append(TriageChatMessage(role="user", text=a))

    if current_question:
        messages.append(TriageChatMessage(role="assistant", text=current_question))

    return messages


def start_triage(db: Session, req: TriageStartRequest) -> TriageResponse:
    patient = db.get(Patient, req.patient_id)
    if not patient:
        raise ValueError(f"Patient not found: {req.patient_id}")

    encounter_id = get_active_encounter_id(db, req.patient_id)
    if not encounter_id:
        raise ValueError(f"No active encounter for patient_id={req.patient_id}")

    initial_case = _build_initial_case(patient)

    session = TriageSession(
        patient_id=req.patient_id,
        encounter_id=encounter_id,
        status="in_progress",
        round_count=0,
        initial_case=initial_case,
        qa_history=[],
        latest_output=None,
        missing_info=[],
        suggested_tests=[],
    )
    db.add(session)
    db.flush()

    graph_state = _invoke_triage_graph(
        initial_case=initial_case,
        qa_history=[],
        round_count=0,
    )

    data = _extract_triage_data(graph_state)

    session.latest_output = data
    session.round_count = graph_state.get("round_count", 0)
    session.urgency = _extract_urgency(data)
    session.summary = _extract_summary_text(data)
    session.missing_info = _extract_missing_info(data)
    session.suggested_tests = _extract_suggested_tests(data)

    current_question = _extract_current_question(data)
    graph_status = graph_state.get("status")

    if graph_status == "needs_more_info" and current_question:
        session.status = "awaiting_answer"
    else:
        session.status = "completed"
        advance_workflow(
            db,
            encounter_id,
            stage="investigation",
        )

    db.commit()
    db.refresh(session)

    return TriageResponse(
        session_id=str(session.id),
        patient_id=session.patient_id,
        status=session.status,
        thinking=False,
        current_question=current_question if session.status == "awaiting_answer" else None,
        chat_history=_to_chat_history(
            session,
            current_question=current_question if session.status == "awaiting_answer" else None,
        ),
        summary=session.summary,
        urgency=session.urgency,
        suggested_tests=session.suggested_tests or [],
        missing_info=session.missing_info or [],
        raw_output=session.latest_output,
    )


def answer_triage(db: Session, session_id: str, req: TriageAnswerRequest) -> TriageResponse:
    session = db.execute(
        select(TriageSession).where(TriageSession.id == session_id)
    ).scalars().first()

    if not session:
        raise ValueError("Triage session not found")

    if session.status == "completed":
        raise ValueError("Triage session already completed")

    if not req.answers:
        raise ValueError("No triage answers provided")

    qa_history = list(session.qa_history or [])

    for item in req.answers:
        qa_history.append({
            "question": item.question,
            "answer": item.answer,
        })

    graph_state = _invoke_triage_graph(
        initial_case=session.initial_case,
        qa_history=qa_history,
        round_count=(session.round_count or 0) + 1,
    )

    data = _extract_triage_data(graph_state)

    session.qa_history = qa_history
    session.latest_output = data
    session.round_count = graph_state.get("round_count", session.round_count)
    session.urgency = _extract_urgency(data)
    session.summary = _extract_summary_text(data)
    session.missing_info = _extract_missing_info(data)
    session.suggested_tests = _extract_suggested_tests(data)

    next_question = _extract_current_question(data)
    graph_status = graph_state.get("status")

    if graph_status == "needs_more_info" and next_question:
        session.status = "awaiting_answer"
    else:
        session.status = "completed"
        advance_workflow(
            db,
            session.encounter_id,
            stage="investigation",
        )

    db.commit()
    db.refresh(session)

    return TriageResponse(
        session_id=str(session.id),
        patient_id=session.patient_id,
        status=session.status,
        thinking=False,
        current_question=next_question if session.status == "awaiting_answer" else None,
        chat_history=_to_chat_history(
            session,
            current_question=next_question if session.status == "awaiting_answer" else None,
        ),
        summary=session.summary,
        urgency=session.urgency,
        suggested_tests=session.suggested_tests or [],
        missing_info=session.missing_info or [],
        raw_output=session.latest_output,
    )