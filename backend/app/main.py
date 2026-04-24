# backend/app/main.py
# FastAPI application entry point
# Semua router di-include di sini

import logging
import os
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import assignment, auth, conflict, dosen, import_export, kurikulum, mata_kuliah, prodi, report, ruang, sesi, timeslot, users

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Course Timetabling System (CTS)",
    description="Sistem Penjadwalan Kuliah — Jurusan Matematika FMIPA UNRI",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# CORS_ORIGINS env var: comma-separated list of allowed origins, e.g.:
#   https://cts-frontend.pages.dev,https://cts-frontend.alfa-nugraha4.workers.dev
# In development (env var not set) allow all origins so local docker compose works.
_raw_origins = os.environ.get("CORS_ORIGINS", "*")
_allow_all = _raw_origins.strip() == "*"
_origins = ["*"] if _allow_all else [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=not _allow_all,   # credentials + wildcard not allowed by spec
    allow_methods=["*"],
    allow_headers=["*"],
)
# ─────────────────────────────────────────────────────────────────────────────


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log unhandled exceptions with full traceback — DEV ONLY."""
    tb = traceback.format_exc()
    logger.error("Unhandled exception on %s %s:\n%s", request.method, request.url.path, tb)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {type(exc).__name__}: {exc}"},
    )

app.include_router(auth.router)
app.include_router(prodi.router)
app.include_router(kurikulum.router)
app.include_router(mata_kuliah.router)
app.include_router(ruang.router)
app.include_router(timeslot.router)
app.include_router(dosen.router)
app.include_router(users.router)
app.include_router(sesi.router)
app.include_router(assignment.router)
app.include_router(conflict.router)
app.include_router(report.router)
app.include_router(import_export.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
