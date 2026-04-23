# backend/app/main.py
# FastAPI application entry point
# Semua router di-include di sini

from fastapi import FastAPI

from app.routers import auth, kurikulum, mata_kuliah, prodi, ruang

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


@app.get("/health")
def health_check():
    return {"status": "ok"}
