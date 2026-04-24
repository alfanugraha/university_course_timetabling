"""
backend/app/routers/import_export.py
Endpoint untuk import/export data dari/ke file Excel.

POST /import/master        — upload db.xlsx, import data master
POST /import/jadwal        — upload file jadwal historis + sesi_id, import JadwalAssignment
GET  /sesi/{id}/export     — generate file Excel jadwal dan stream sebagai download
"""

import io
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import (
    EDITOR_ROLES_JURUSAN,
    EDITOR_ROLES_PRODI,
    VIEWER_ROLES,
    require_role,
)
from app.database import get_db
from app.models.sesi_jadwal import SesiJadwal
from app.services.excel_exporter import ExcelExporter
from app.services.excel_importer import ExcelImporter, ImportResult

router = APIRouter(tags=["import-export"])

# Roles allowed to export: all except dosen
EXPORT_ROLES = EDITOR_ROLES_PRODI + VIEWER_ROLES


def _result_to_dict(result: ImportResult) -> dict:
    """Convert ImportResult dataclass to JSON-serialisable dict."""
    return {
        "total": result.total,
        "inserted": result.inserted,
        "updated": result.updated,
        "skipped": result.skipped,
        "warnings": [
            {
                "row": w.row,
                "sheet": w.sheet,
                "value": str(w.value) if w.value is not None else None,
                "reason": w.reason,
            }
            for w in result.warnings
        ],
    }


@router.post("/import/master", status_code=status.HTTP_200_OK)
async def import_master(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """
    Import data master dari file db.xlsx.

    Memproses sheet: Prodi, Kurikulum, Mata Kuliah, Ruang Kuliah, Dosen.
    Menggunakan tolerant import — baris bermasalah dicatat sebagai warning.
    """
    contents = await file.read()
    file_obj = io.BytesIO(contents)

    importer = ExcelImporter(db_session=db)
    result = importer.import_master_db(file_obj)
    return _result_to_dict(result)


@router.post("/import/jadwal", status_code=status.HTTP_200_OK)
async def import_jadwal(
    file: UploadFile = File(...),
    sesi_id: uuid.UUID = Query(..., description="UUID SesiJadwal target"),
    db: Session = Depends(get_db),
    current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """
    Import jadwal dari file Excel historis ke SesiJadwal yang ditentukan.

    Membaca sheet jadwal, mem-parsing kolom Hari/Waktu → timeslot_id,
    Kode MK + Kelas → mk_kelas_id, Dosen I/II → dosen1_id/dosen2_id,
    Ruang → ruang_id (nullable).

    Upsert: baris dengan (sesi_id, mk_kelas_id) yang sudah ada dilewati.
    """
    # Validate sesi exists
    sesi = db.query(SesiJadwal).filter(SesiJadwal.id == sesi_id).first()
    if sesi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SesiJadwal dengan id '{sesi_id}' tidak ditemukan",
        )

    contents = await file.read()
    file_obj = io.BytesIO(contents)

    importer = ExcelImporter(db_session=db)
    result = importer.import_jadwal(file_obj, str(sesi_id))
    return _result_to_dict(result)


@router.get("/sesi/{sesi_id}/export")
def export_jadwal(
    sesi_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(EXPORT_ROLES)),
):
    """
    Export jadwal untuk satu sesi ke file Excel (.xlsx).

    Menghasilkan workbook dengan dua sheet:
    - Jadwal Utama: seluruh assignment terurut per hari/sesi
    - Rekap Beban SKS: ringkasan SKS per dosen

    Returns file sebagai attachment download.
    """
    sesi = db.get(SesiJadwal, sesi_id)
    if sesi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SesiJadwal dengan id '{sesi_id}' tidak ditemukan",
        )

    exporter = ExcelExporter(db_session=db)
    excel_bytes = exporter.export_jadwal(sesi_id)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize sesi nama for use in filename
    sesi_nama = sesi.nama.replace(" ", "_").replace("/", "-")
    filename = f"jadwal_{sesi_nama}_{timestamp}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
