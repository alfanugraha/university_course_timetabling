"""
backend/app/routers/sesi.py
CRUD endpoints untuk entitas SesiJadwal.

GET   /sesi              — list semua sesi (semua role terautentikasi)
POST  /sesi              — buat sesi baru (EDITOR_ROLES_JURUSAN)
PUT   /sesi/{id}         — update sesi + transisi status (EDITOR_ROLES_JURUSAN)
PATCH /sesi/{id}/approve — approve atau minta revisi (ketua_jurusan)
PATCH /sesi/{id}/publish — sahkan/arsipkan jadwal (ketua_jurusan)

Aturan transisi status:
  Draft → Aktif → Arsip  (tidak boleh mundur)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import EDITOR_ROLES_JURUSAN, VIEWER_ROLES, require_role
from app.database import get_db
from app.models.dosen import Dosen, DosenPreference
from app.models.sesi_jadwal import SesiJadwal
from app.schemas.sesi_jadwal import (
    ApproveRequest,
    DosenPreferenceSummaryItem,
    PreferencesSummaryResponse,
    SesiJadwalCreate,
    SesiJadwalResponse,
    SesiJadwalUpdate,
)

router = APIRouter(prefix="/sesi", tags=["sesi"])

_KETUA_JURUSAN = ["ketua_jurusan"]

# Urutan transisi yang valid: index lebih tinggi = lebih maju
_STATUS_ORDER = {"Draft": 0, "Aktif": 1, "Arsip": 2}


def _get_or_404(db: Session, sesi_id: uuid.UUID) -> SesiJadwal:
    sesi = db.get(SesiJadwal, sesi_id)
    if sesi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SesiJadwal dengan id '{sesi_id}' tidak ditemukan",
        )
    return sesi


# ---------------------------------------------------------------------------
# GET /sesi
# ---------------------------------------------------------------------------

@router.get("", response_model=list[SesiJadwalResponse])
def list_sesi(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return semua sesi jadwal, diurutkan berdasarkan tahun akademik dan semester."""
    return (
        db.query(SesiJadwal)
        .order_by(SesiJadwal.tahun_akademik.desc(), SesiJadwal.semester)
        .all()
    )


# ---------------------------------------------------------------------------
# POST /sesi
# ---------------------------------------------------------------------------

@router.post("", response_model=SesiJadwalResponse, status_code=status.HTTP_201_CREATED)
def create_sesi(
    payload: SesiJadwalCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Buat sesi jadwal baru. Hanya EDITOR_ROLES_JURUSAN."""
    sesi = SesiJadwal(
        nama=payload.nama,
        semester=payload.semester,
        tahun_akademik=payload.tahun_akademik,
        status="Draft",
    )
    db.add(sesi)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"SesiJadwal untuk semester '{payload.semester}' "
                f"tahun akademik '{payload.tahun_akademik}' sudah ada"
            ),
        )
    db.refresh(sesi)
    return sesi


# ---------------------------------------------------------------------------
# PUT /sesi/{id}
# ---------------------------------------------------------------------------

@router.put("/{sesi_id}", response_model=SesiJadwalResponse)
def update_sesi(
    sesi_id: uuid.UUID,
    payload: SesiJadwalUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Update sesi jadwal. Hanya EDITOR_ROLES_JURUSAN.
    Transisi status hanya boleh maju: Draft → Aktif → Arsip.
    """
    sesi = _get_or_404(db, sesi_id)
    update_data = payload.model_dump(exclude_unset=True)

    # Validasi transisi status
    if "status" in update_data:
        new_status = update_data["status"]
        current_order = _STATUS_ORDER.get(sesi.status, 0)
        new_order = _STATUS_ORDER.get(new_status, 0)
        if new_order < current_order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Transisi status tidak valid: '{sesi.status}' → '{new_status}'. "
                    "Status hanya boleh maju (Draft → Aktif → Arsip)."
                ),
            )

    for field, value in update_data.items():
        setattr(sesi, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kombinasi semester dan tahun akademik sudah digunakan oleh sesi lain",
        )
    db.refresh(sesi)
    return sesi


# ---------------------------------------------------------------------------
# PATCH /sesi/{id}/approve
# ---------------------------------------------------------------------------

@router.patch("/{sesi_id}/approve", response_model=SesiJadwalResponse)
def approve_sesi(
    sesi_id: uuid.UUID,
    payload: ApproveRequest,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(_KETUA_JURUSAN)),
):
    """Approve atau minta revisi sesi jadwal. Hanya ketua_jurusan.

    - action='approve'           → set status ke 'Aktif'
    - action='request_revision'  → kembalikan status ke 'Draft'
    """
    sesi = _get_or_404(db, sesi_id)

    if payload.action == "approve":
        sesi.status = "Aktif"
    else:  # request_revision
        sesi.status = "Draft"

    db.commit()
    db.refresh(sesi)
    return sesi


# ---------------------------------------------------------------------------
# PATCH /sesi/{id}/publish
# ---------------------------------------------------------------------------

@router.patch("/{sesi_id}/publish", response_model=SesiJadwalResponse)
def publish_sesi(
    sesi_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(_KETUA_JURUSAN)),
):
    """Sahkan/arsipkan jadwal. Hanya ketua_jurusan.
    Hanya boleh dilakukan jika status saat ini adalah 'Aktif'.
    """
    sesi = _get_or_404(db, sesi_id)

    if sesi.status != "Aktif":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Jadwal hanya bisa disahkan jika status 'Aktif'. "
                f"Status saat ini: '{sesi.status}'."
            ),
        )

    sesi.status = "Arsip"
    db.commit()
    db.refresh(sesi)
    return sesi


# ---------------------------------------------------------------------------
# GET /sesi/{id}/preferences-summary
# ---------------------------------------------------------------------------

@router.get("/{sesi_id}/preferences-summary", response_model=PreferencesSummaryResponse)
def preferences_summary(
    sesi_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN + VIEWER_ROLES)),
):
    """Ringkasan pelanggaran preferensi dosen untuk satu sesi.
    Akses: EDITOR_ROLES_JURUSAN + ketua_jurusan.
    """
    _get_or_404(db, sesi_id)

    # Aggregate per dosen: total preferences and total violated
    rows = (
        db.query(
            Dosen.id.label("dosen_id"),
            Dosen.kode.label("kode"),
            Dosen.nama.label("nama"),
            func.count(DosenPreference.id).label("total_preferensi"),
            func.sum(
                case((DosenPreference.is_violated == True, 1), else_=0)
            ).label("total_dilanggar"),
        )
        .join(DosenPreference, DosenPreference.dosen_id == Dosen.id)
        .filter(DosenPreference.sesi_id == sesi_id)
        .group_by(Dosen.id, Dosen.kode, Dosen.nama)
        .order_by(Dosen.nama)
        .all()
    )

    breakdown = [
        DosenPreferenceSummaryItem(
            dosen_id=row.dosen_id,
            kode=row.kode,
            nama=row.nama,
            total_preferensi=row.total_preferensi,
            total_dilanggar=int(row.total_dilanggar or 0),
        )
        for row in rows
    ]

    total_preferensi = sum(item.total_preferensi for item in breakdown)
    total_dilanggar = sum(item.total_dilanggar for item in breakdown)

    return PreferencesSummaryResponse(
        sesi_id=sesi_id,
        total_preferensi=total_preferensi,
        total_dilanggar=total_dilanggar,
        breakdown=breakdown,
    )
