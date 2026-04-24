# backend/app/main.py
# FastAPI application entry point
# Semua router di-include di sini

from fastapi import FastAPI

from app.routers import assignment, auth, conflict, dosen, import_export, kurikulum, mata_kuliah, prodi, report, ruang, sesi, timeslot, users

app = FastAPI(
    title="Course Timetabling System (CTS)",
    description="Sistem Penjadwalan Kuliah — Jurusan Matematika FMIPA UNRI",
    version="1.0.0",
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
