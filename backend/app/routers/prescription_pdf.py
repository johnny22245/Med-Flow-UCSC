from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import os
import json
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

router = APIRouter(prefix="/api/prescription", tags=["prescription_pdf"])

# backend/ is two levels up from backend/app/routers/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CASE_FILE = os.path.join(BASE_DIR, "data", "cases", "case_summaries.json")


def _read_store():
    if not os.path.exists(CASE_FILE):
        return {}
    try:
        with open(CASE_FILE, "r") as f:
            return json.load(f) or {}
    except json.JSONDecodeError:
        return {}


def _draw_wrapped_text(c, text, x, y, max_width, line_height=14):
    """Very small word-wrap helper for ReportLab canvas."""
    if not text:
        return y
    words = str(text).split()
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, "Helvetica", 10) <= max_width:
            line = test
        else:
            c.drawString(x, y, line)
            y -= line_height
            line = w
    if line:
        c.drawString(x, y, line)
        y -= line_height
    return y

from reportlab.lib import colors


def draw_medflow_logo(c, x, y, size=26):
    green = colors.HexColor("#1FBF9A")
    dark = colors.HexColor("#0F3D3E")
    muted = colors.HexColor("#5F6B6D")

    cross_w = size
    cross_h = size
    arm = size * 0.28

    staff_w = max(1.6, size * 0.07)
    snake_w = max(1.2, size * 0.06)

    cx = x + cross_w * 0.45
    cy = y - cross_h * 0.55

    c.saveState()

    # Cross
    c.setFillColor(green)
    c.setStrokeColor(green)
    c.roundRect(cx - arm / 2, cy - cross_h * 0.45, arm, cross_h * 0.9, 3, fill=1, stroke=0)
    c.roundRect(cx - cross_w * 0.45, cy - arm / 2, cross_w * 0.9, arm, 3, fill=1, stroke=0)

    # Staff
    staff_x = x + cross_w * 0.45
    staff_top = y - cross_h * 0.18
    staff_bot = y - cross_h * 0.92

    c.setStrokeColor(dark)
    c.setLineWidth(staff_w)
    c.line(staff_x, staff_top, staff_x, staff_bot)

    # Serpent
    amp_r = cross_w * 0.26
    amp_l = cross_w * 0.18
    y1 = y - cross_h * 0.30
    y2 = y - cross_h * 0.55
    y3 = y - cross_h * 0.82

    c.setLineWidth(snake_w)
    p = c.beginPath()
    p.moveTo(staff_x - amp_l, y1)
    p.curveTo(staff_x + amp_r, y1 - 2, staff_x + amp_r, y2 + 2, staff_x - amp_l * 0.8, y2)
    p.curveTo(staff_x - amp_l * 1.4, y2 - 2, staff_x - amp_l * 1.4, y3 + 2, staff_x + amp_r * 0.6, y3)
    c.drawPath(p, stroke=1, fill=0)

    c.setFillColor(dark)
    c.circle(staff_x + cross_w * 0.06, y1, max(1.6, size * 0.06), fill=1, stroke=0)

    # Text
    text_x = x + cross_w * 1.6

    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(text_x, y - 10, "Med-Flow")

    c.setFont("Helvetica", 10)
    c.setFillColor(muted)
    c.drawString(text_x, y - 26, "Human–AI Clinical Decision Support")

    c.restoreState()


def draw_medflow_footer(c, left, bottom_y, right):
    """
    Branded footer with product positioning + disclaimer.
    """
    c.saveState()
    c.setStrokeColor(colors.HexColor("#1FBF9A"))
    c.setLineWidth(2)
    c.line(left, bottom_y + 16, right, bottom_y + 16)

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#0F3D3E"))
    c.drawString(left, bottom_y + 4, "Med-Flow • AI-generated draft for clinician review • Human-in-the-loop required")

    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(colors.HexColor("#6E7C7D"))
    c.drawRightString(right, bottom_y + 4, "Demo artifact — not for clinical use")
    c.restoreState()


@router.get("/pdf/{patient_id}")
def get_prescription_pdf(patient_id: str):
    """
    Generates a demo prescription PDF from the finalized case summary stored in:
    backend/data/cases/case_summaries.json

    Requires: Phase 9 "Finalize & Save" has been clicked (case summary exists).
    """
    store = _read_store()
    record = store.get(patient_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail="No finalized case summary found. Finalize the case first (Case Summary → Finalize & Save)."
        )

    patient = record.get("patient", {})
    diagnosis = record.get("diagnosis", {})
    order = record.get("order", {})
    safety = record.get("safety", {})
    final_note = record.get("finalClinicianNote", "")

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    left = 0.75 * inch
    right = width - 0.75 * inch
    y = height - 0.75 * inch

    # Header with logo
    draw_medflow_logo(c, left, y, size=26)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#5F6B6D"))
    c.drawRightString(right, y - 6, datetime.utcnow().strftime("Generated: %Y-%m-%d %H:%M UTC"))
    y -= 40

    c.setStrokeColor(colors.HexColor("#1FBF9A"))
    c.setLineWidth(2)
    c.line(left, y, right, y)
    y -= 18

    # Patient block
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "Patient")
    y -= 14
    c.setFont("Helvetica", 10)
    c.drawString(left, y, f"Name: {patient.get('name','—')}")
    c.drawString(left + 3.2 * inch, y, f"MRN: {patient.get('id','—')}")
    y -= 14
    c.drawString(left, y, f"Age/Sex: {patient.get('age','—')} / {patient.get('sex','—')}")
    y -= 14
    c.drawString(left, y, f"Allergies: {', '.join(patient.get('allergies', []) or []) or '—'}")
    y -= 18

    # Diagnosis block
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "Diagnosis")
    y -= 14
    c.setFont("Helvetica", 10)
    c.drawString(left, y, f"Primary: {diagnosis.get('primary','—')}")
    y -= 14
    c.drawString(left, y, f"Confidence: {diagnosis.get('confidence','—')}")
    y -= 18

    # Rx block
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "Rx (Medications)")
    y -= 14
    c.setFont("Helvetica", 10)

    meds = (order.get("meds") or [])
    if not meds:
        c.drawString(left, y, "—")
        y -= 14
    else:
        # Table-ish layout
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left, y, "Drug")
        c.drawString(left + 2.3 * inch, y, "Dose")
        c.drawString(left + 3.2 * inch, y, "Route")
        c.drawString(left + 3.8 * inch, y, "Frequency")
        c.drawString(left + 5.2 * inch, y, "Duration")
        y -= 12
        c.setFont("Helvetica", 9)

        for m in meds:
            if y < 1.2 * inch:
                c.showPage()
                y = height - 0.75 * inch
                c.setFont("Helvetica", 9)

            c.drawString(left, y, str(m.get("drug", "—"))[:32])
            c.drawString(left + 2.3 * inch, y, str(m.get("dose", "—"))[:14])
            c.drawString(left + 3.2 * inch, y, str(m.get("route", "—"))[:10])
            c.drawString(left + 3.8 * inch, y, str(m.get("frequency", "—"))[:18])
            c.drawString(left + 5.2 * inch, y, str(m.get("duration", "—"))[:14])
            y -= 12

        y -= 10

    # Order notes
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "Order Notes")
    y -= 14
    c.setFont("Helvetica", 10)
    y = _draw_wrapped_text(c, order.get("notes", "") or "—", left, y, max_width=(right - left))
    y -= 8

    # Safety disposition
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "Safety Disposition")
    y -= 14
    c.setFont("Helvetica", 10)
    c.drawString(left, y, f"Decision: {safety.get('decision', 'none')}")
    y -= 14
    sel = safety.get("selectedSuggestion", "") or "—"
    c.drawString(left, y, f"Selected suggestion: {sel}")
    y -= 14
    ov = safety.get("overrideNote", "") or "—"
    y = _draw_wrapped_text(c, f"Override note: {ov}", left, y, max_width=(right - left))
    y -= 8

    # Final clinician note
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "Final Clinician Note")
    y -= 14
    c.setFont("Helvetica", 10)
    y = _draw_wrapped_text(c, final_note or "—", left, y, max_width=(right - left))

    # Footer (branded)
    draw_medflow_footer(c, left, 0.55 * inch, right)
    c.showPage()
    c.save()

    pdf_bytes = buf.getvalue()
    buf.close()

    filename = f"prescription_{patient_id}.pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)