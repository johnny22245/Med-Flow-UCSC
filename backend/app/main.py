import os
import multiprocessing as mp

os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

try:
    mp.set_start_method("spawn", force=True)
except RuntimeError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.routers.patients import router as patients_router
from app.routers.investigation import router as investigation_router
from app.routers.diagnosis import router as diagnosis_router
from app.routers.treatment import router as treatment_router
from app.routers.safety import router as safety_router
from app.routers.summary import router as summary_router
from app.routers.prescription_pdf import router as prescription_pdf_router
from app.routers.case import router as case_router


app = FastAPI(
    title="Med-Flow ~ AI-Human Healthcare",
    version="0.1.0",
    description="Local, privacy-preserving demo App with AI-Agents integration."
)

# Ensure directories exist
os.makedirs("data/static", exist_ok=True)
os.makedirs("data/reports", exist_ok=True)

# Serve demo static assets
app.mount("/static", StaticFiles(directory="data/static"), name="static")

# Serve uploaded reports
app.mount("/reports", StaticFiles(directory="data/reports"), name="reports")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients_router, prefix="/api")
app.include_router(investigation_router)
app.include_router(diagnosis_router)
app.include_router(treatment_router)
app.include_router(safety_router)
app.include_router(summary_router)
app.include_router(prescription_pdf_router)
app.include_router(case_router)

from app.routers.triage import router as triage_router
app.include_router(triage_router)


@app.get("/health")
def health():
    return {"status": "ok"}