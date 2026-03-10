from pydantic import BaseModel

class ReportUploadResponse(BaseModel):
    patient_id: str
    encounter_id: str
    filename: str
    report_type: str
    message: str