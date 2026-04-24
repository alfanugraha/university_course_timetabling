"""
backend/app/routers/conflict.py
Endpoints untuk conflict detection dan manajemen conflict log.

POST  /sesi/{id}/check-conflicts        — jalankan engine, simpan ke conflict_log
GET   /sesi/{id}/conflicts              — daftar konflik terbaru (filter jenis/severity)
PATCH /sesi/{id}/conflicts/{cid}/resolve — tandai konflik sebagai resolved
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import EDITOR_ROLES_JURUSAN, VIEWER_ROLES, require_role
from app.database import get_db
from app.models.conflict_log import ConflictLog
from app.models.sesi_jadwal import SesiJadwal
from app.schemas.conflict import (
    ConflictCheckSummary,
    ConflictListResponse,
    ConflictLogResponse,
    ConflictResolveResponse,
)
from app.services.conflict_engine import ConflictEngine, ConflictSeverity

router = APIRouter(prefix="/sesi", tags=["conflict"])

_ALL_VIEWER_ROLES = EDITOR_ROLES_JURUSAN + VIEWER_ROLES


def _get_sesi_or_404(db: Session, sesi_id: uuid.UUID) -> SesiJadwal:
    sesi = db.get(SesiJadwal, sesi_id)
    if sesi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SesiJadwal dengan id '{sesi_id}' tidak ditemukan",
        )
    return sesi


# ---------------------------------------------------------------------------
# POST /sesi/{id}/check-conflicts
# ---------------------------------------------------------------------------

@router.post(
    "/{sesi_id}/check-conflicts",
    response_model=ConflictCheckSummary,
    status_code=status.HTTP_200_OK,
)
def check_conflicts(
    sesi_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Jalankan conflict detection engine untuk sesi yang diberikan.

    - Hapus semua ConflictLog lama untuk sesi ini (fresh run)
    - Jalankan semua rule HC dan SC
    - Simpan setiap ConflictResult sebagai ConflictLog baru
    - Kembalikan ringkasan: jumlah ERROR, jumlah WARNING, dan daftar konflik

    Akses: EDITOR_ROLES_JURUSAN (admin, sekretaris_jurusan, tendik_jurusan)
    """
    _get_sesi_or_404(db, sesi_id)

    # Hapus conflict log lama untuk sesi ini (fresh run)
    db.query(ConflictLog).filter(ConflictLog.sesi_id == sesi_id).delete(
        synchronize_session=False
    )
    db.flush()

    # Jalankan engine
    engine = ConflictEngine(db)
    results = engine.run(sesi_id)

    # Simpan setiap hasil ke conflict_log
    logs: list[ConflictLog] = []
    for result in results:
        log = ConflictLog(
            sesi_id=sesi_id,
            jenis=result.jenis,
            severity=result.severity,
            assignment_ids=result.assignment_ids,
            pesan=result.pesan,
            detail=result.detail,
            is_resolved=False,
        )
        db.add(log)
        logs.append(log)

    db.commit()

    # Refresh semua log agar id dan checked_at terisi
    for log in logs:
        db.refresh(log)

    total_error = sum(1 for r in results if r.severity == ConflictSeverity.ERROR)
    total_warning = sum(1 for r in results if r.severity == ConflictSeverity.WARNING)

    conflict_responses = [ConflictLogResponse.model_validate(log) for log in logs]

    return ConflictCheckSummary(
        sesi_id=sesi_id,
        total_error=total_error,
        total_warning=total_warning,
        total=len(results),
        conflicts=conflict_responses,
    )


# ---------------------------------------------------------------------------
# GET /sesi/{id}/conflicts
# ---------------------------------------------------------------------------

@router.get(
    "/{sesi_id}/conflicts",
    response_model=ConflictListResponse,
)
def list_conflicts(
    sesi_id: uuid.UUID,
    jenis: Optional[str] = Query(None, description="Filter berdasarkan jenis konflik"),
    severity: Optional[str] = Query(None, description="Filter berdasarkan severity: ERROR atau WARNING"),
    is_resolved: Optional[bool] = Query(None, description="Filter berdasarkan status resolved"),
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(_ALL_VIEWER_ROLES)),
):
    """Kembalikan daftar konflik dari conflict_log untuk sesi yang diberikan.

    Filter opsional:
    - jenis: kode jenis konflik (misal: LECTURER_DOUBLE, ROOM_DOUBLE)
    - severity: ERROR atau WARNING
    - is_resolved: true/false

    Diurutkan: ERROR dulu, lalu WARNING; dalam tiap severity diurutkan by checked_at desc.

    Akses: EDITOR_ROLES_JURUSAN + ketua_jurusan
    """
    _get_sesi_or_404(db, sesi_id)

    q = db.query(ConflictLog).filter(ConflictLog.sesi_id == sesi_id)

    if jenis is not None:
        q = q.filter(ConflictLog.jenis == jenis)

    if severity is not None:
        severity_upper = severity.upper()
        if severity_upper not in ("ERROR", "WARNING"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parameter severity harus 'ERROR' atau 'WARNING'",
            )
        q = q.filter(ConflictLog.severity == severity_upper)

    if is_resolved is not None:
        q = q.filter(ConflictLog.is_resolved == is_resolved)

    # Urutkan: ERROR dulu, lalu WARNING; dalam tiap severity by checked_at desc
    from sqlalchemy import case as sa_case
    severity_order = sa_case(
        (ConflictLog.severity == "ERROR", 0),
        else_=1,
    )
    logs = q.order_by(severity_order, ConflictLog.checked_at.desc()).all()

    return ConflictListResponse(
        items=[ConflictLogResponse.model_validate(log) for log in logs],
        total=len(logs),
    )


# ---------------------------------------------------------------------------
# PATCH /sesi/{id}/conflicts/{cid}/resolve
# ---------------------------------------------------------------------------

@router.patch(
    "/{sesi_id}/conflicts/{conflict_id}/resolve",
    response_model=ConflictResolveResponse,
)
def resolve_conflict(
    sesi_id: uuid.UUID,
    conflict_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Tandai satu konflik sebagai resolved (toggle: resolved ↔ unresolved).

    Akses: EDITOR_ROLES_JURUSAN (admin, sekretaris_jurusan, tendik_jurusan)
    """
    _get_sesi_or_404(db, sesi_id)

    log = db.get(ConflictLog, conflict_id)
    if log is None or log.sesi_id != sesi_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ConflictLog dengan id '{conflict_id}' tidak ditemukan dalam sesi ini",
        )

    log.is_resolved = not log.is_resolved
    db.commit()
    db.refresh(log)

    status_label = "resolved" if log.is_resolved else "unresolved"
    return ConflictResolveResponse(
        id=log.id,
        is_resolved=log.is_resolved,
        pesan=f"Konflik berhasil ditandai sebagai {status_label}",
    )
