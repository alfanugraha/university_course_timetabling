# backend/app/main.py
# FastAPI application entry point
# Semua router di-include di sini

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routers import assignment, auth, conflict, dosen, import_export, kurikulum, mata_kuliah, prodi, report, ruang, sesi, timeslot, users

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Course Timetabling System (CTS)",
    description="Sistem Penjadwalan Kuliah — Jurusan Matematika FMIPA UNRI",
    version="1.0.0",
)


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
