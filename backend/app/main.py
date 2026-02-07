from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.patients import router as patients_router

app = FastAPI(
    title="Med-Flow API (Dummy)",
    version="0.1.0",
    description="Local, privacy-preserving demo API using dummy fixtures and in-memory store."
)

# Dev CORS (Vite default). Tighten later.
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

@app.get("/health")
def health():
    return {"status": "ok"}
