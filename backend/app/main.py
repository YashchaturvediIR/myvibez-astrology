from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.records import router as records_router
from app.services.persistence import init_db

from app.api.kundli import router as kundli_router
from app.api.places import router as places_router
from app.api.significators import router as significators_router
from app.api.property import router as property_router
from app.api.childbirth import router as childbirth_router
from app.api.grah_nirdeshan import router as grah_nirdeshan_router
from app.api.predictive_timing import router as predictive_timing_router


app = FastAPI(
    title="Personal Kundli API",
    version="1.1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# API ROUTES
# =========================

app.include_router(kundli_router, prefix="/api")
app.include_router(places_router, prefix="/api")
app.include_router(significators_router, prefix="/api")
app.include_router(property_router, prefix="/api")
app.include_router(childbirth_router, prefix="/api")
app.include_router(grah_nirdeshan_router, prefix="/api")
app.include_router(predictive_timing_router, prefix="/api")
app.include_router(records_router, prefix="/api")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


# =========================
# FRONTEND
# =========================

# Project root:
# project/
# ├── backend/
# │   └── app/
# │       └── main.py
# └── frontend/
#
# Therefore, go two levels up from main.py's directory.

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"


# Serve frontend AFTER API routes
app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend"
)
