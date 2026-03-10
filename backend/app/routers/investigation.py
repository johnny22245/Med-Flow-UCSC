import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import get_db
from app.models.encounter import Encounter
from app.models.investigation_record import InvestigationRecord
from app.schemas.investigation import (
    InvestigationPayload,
    InvestigationOrdersPayload,
)
from app.schemas.report_upload import ReportUploadResponse
from app.services import investigation_service
from app.services.encounter_service import get_active_encounter_id
from app.services.imaging_inference import analyze_uploaded_image, is_image_file


router = APIRouter(tags=["investigation"])

REPORT_DIR = "data/reports"


class AnalyzeImagingRequest(BaseModel):
    filename: str


class BoxPayload(BaseModel):
    xmin: int
    ymin: int
    xmax: int
    ymax: int


class ConfirmImagingRequest(BaseModel):
    filename: str
    clinician_note: str | None = None
    clinician_box: BoxPayload | None = None


def _utc_now():
    return datetime.now(timezone.utc)


def _normalize_filename(name: str) -> str:
    return (name or "").strip()


def _get_active_investigation_record(db: Session, patient_id: str) -> InvestigationRecord:
    encounter = (
        db.query(Encounter)
        .filter(Encounter.patient_id == patient_id)
        .order_by(Encounter.created_at.desc())
        .first()
    )
    if not encounter:
        raise HTTPException(
            status_code=404,
            detail=f"No active encounter for patient_id={patient_id}",
        )

    record = (
        db.query(InvestigationRecord)
        .filter(InvestigationRecord.encounter_id == encounter.id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No investigation record found for patient_id={patient_id}",
        )

    return record


def _find_uploaded_report(record: InvestigationRecord, filename: str) -> dict:
    wanted = _normalize_filename(filename).lower()
    results = dict(record.results or {})
    uploaded_reports = list(results.get("uploaded_reports") or [])

    for item in uploaded_reports:
        item_name = _normalize_filename(item.get("filename", "")).lower()
        if item_name == wanted:
            return item

    raise HTTPException(
        status_code=404,
        detail=f"Uploaded report not found: {filename}",
    )


@router.get("/api/investigation/{patientId}")
def get_investigation(patientId: str, db: Session = Depends(get_db)):
    return investigation_service.get_investigation(db, patientId)


@router.post("/api/investigation/{patientId}")
def save_investigation(
    patientId: str,
    payload: InvestigationPayload,
    db: Session = Depends(get_db),
):
    if payload.patient_id != patientId:
        raise HTTPException(
            status_code=400,
            detail="payload.patient_id must match patientId in path",
        )

    try:
        return investigation_service.upsert_investigation_payload(db, patientId, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/investigation/{patientId}/orders")
def save_investigation_orders(
    patientId: str,
    payload: InvestigationOrdersPayload,
    db: Session = Depends(get_db),
):
    if payload.patient_id != patientId:
        raise HTTPException(
            status_code=400,
            detail="payload.patient_id must match patientId in path",
        )

    try:
        return investigation_service.upsert_investigation_orders(db, patientId, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/investigation/{patient_id}/upload", response_model=ReportUploadResponse)
async def upload_report(
    patient_id: str,
    report_type: str = Form(...),
    test_code: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    encounter_id = get_active_encounter_id(db, patient_id)

    if not encounter_id:
        raise HTTPException(
            status_code=400,
            detail=f"No active encounter for patient_id={patient_id}",
        )

    contents = await file.read()

    os.makedirs(REPORT_DIR, exist_ok=True)
    patient_dir = os.path.join(REPORT_DIR, patient_id)
    os.makedirs(patient_dir, exist_ok=True)

    filename = _normalize_filename(file.filename) or f"{test_code}_{report_type}.bin"
    file_path = os.path.join(patient_dir, filename)
    public_url = f"/reports/{patient_id}/{filename}"

    with open(file_path, "wb") as f:
        f.write(contents)

    report_record = {
        "test_code": test_code,
        "filename": filename,
        "report_type": report_type,
        "size": len(contents),
        "path": file_path,
        "url": public_url,
        "uploaded_at": _utc_now().isoformat(),
    }

    rec = db.query(InvestigationRecord).filter_by(encounter_id=encounter_id).first()

    if not rec:
        rec = InvestigationRecord(
            encounter_id=encounter_id,
            suggested_tests=[],
            ordered_tests=[],
            results={"uploaded_reports": [report_record]},
            notes=None,
        )
        db.add(rec)
    else:
        results = dict(rec.results or {})
        reports = list(results.get("uploaded_reports") or [])
        reports.append(report_record)
        results["uploaded_reports"] = reports
        rec.results = results
        rec.updated_at = _utc_now()
        flag_modified(rec, "results")

    db.commit()
    db.refresh(rec)

    return {
        "patient_id": patient_id,
        "encounter_id": str(encounter_id),
        "filename": filename,
        "report_type": report_type,
        "message": "Report uploaded successfully",
    }


@router.post("/api/investigation/{patient_id}/imaging/analyze")
def analyze_imaging(
    patient_id: str,
    body: AnalyzeImagingRequest,
    db: Session = Depends(get_db),
):
    filename = _normalize_filename(body.filename)

    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")

    record = _get_active_investigation_record(db, patient_id)
    report = _find_uploaded_report(record, filename)

    if not is_image_file(report.get("filename", "")):
        raise HTTPException(
            status_code=400,
            detail="Selected report is not a supported image file.",
        )

    try:
        imaging_result = analyze_uploaded_image(patient_id, report)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Imaging analysis failed: {str(e)}")

    results = dict(record.results or {})
    imaging_ai = dict(results.get("imaging_ai") or {})
    imaging_ai[filename] = imaging_result
    results["imaging_ai"] = imaging_ai

    record.results = results
    record.updated_at = _utc_now()
    flag_modified(record, "results")

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "ok": True,
        "patient_id": patient_id,
        "filename": filename,
        "imaging_ai": imaging_result,
    }


@router.post("/api/investigation/{patient_id}/imaging/confirm")
def confirm_imaging(
    patient_id: str,
    body: ConfirmImagingRequest,
    db: Session = Depends(get_db),
):
    filename = _normalize_filename(body.filename)

    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")

    record = _get_active_investigation_record(db, patient_id)

    results = dict(record.results or {})
    imaging_ai = dict(results.get("imaging_ai") or {})

    target_key = None
    for key in imaging_ai.keys():
        if _normalize_filename(key).lower() == filename.lower():
            target_key = key
            break

    if target_key is None:
        raise HTTPException(
            status_code=404,
            detail=f"No AI imaging result found for {filename}",
        )

    entry = dict(imaging_ai[target_key] or {})
    entry["clinician_note"] = body.clinician_note or ""
    entry["status"] = "clinician_updated" if body.clinician_box else "reviewed"
    entry["reviewed_at"] = _utc_now().isoformat()

    if body.clinician_box:
        entry["clinician_box"] = body.clinician_box.model_dump()

    imaging_ai[target_key] = entry
    results["imaging_ai"] = imaging_ai

    record.results = results
    record.notes = body.clinician_note or record.notes
    record.updated_at = _utc_now()
    flag_modified(record, "results")

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "ok": True,
        "patient_id": patient_id,
        "filename": target_key,
        "imaging_ai": entry,
    }