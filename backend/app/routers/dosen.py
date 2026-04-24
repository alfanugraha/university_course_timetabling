"""
backend/app/routers/dosen.py
CRUD endpoints untuk entitas Dosen.

GET  /dosen                          — list semua dosen (semua role kecuali dosen)
POST /dosen                          — buat dosen baru (EDITOR_ROLES_JURUSAN)
PUT  /dosen/{id}                     — update dosen (EDITOR_ROLES_JURUSAN)
POST /dosen/{id}/unavailability      — tambah unavailability slot (EDITOR_ROLES_JURUSAN + dosen own)
GET  /dosen/{id}/unavailability      — list unavailability slot (EDITOR_ROLES_JURUSAN + dosen own)
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import EDITOR_ROLES_JURUSAN, EDITOR_ROLES_PRODI, VIEWER_ROLES, require_role
from app.database import get_db
from app.models.dosen import Dosen, DosenPreference, DosenUnavailability
from app.models.sesi_jadwal import SesiJadwal
from app.models.timeslot import Timeslot
from app.schemas.dosen import (
    DosenCreate,
    DosenPreferenceCreate,
    DosenPreferenceResponse,
    DosenPreferenceUpdate,
    DosenResponse,
    DosenUnavailabilityCreate,
    DosenUnavailabilityResponse,
    DosenUpdate,
)

# Roles yang boleh mengakses GET /dosen (semua kecuali role 'dosen')
VIEWER_DOSEN_ROLES = EDITOR_ROLES_JURUSAN + [
    r for r in EDITOR_ROLES_PRODI if r not in EDITOR_ROLES_JURUSAN
] + VIEWER_ROLES

router = APIRouter(prefix="/dosen", tags=["dosen"])


@router.get("", response_model=list[DosenResponse])
def list_dosen(
    homebase_prodi_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(VIEWER_DOSEN_ROLES)),
):
    """Return semua dosen dengan filter opsional."""
    q = db.query(Dosen)

    if homebase_prodi_id is not None:
        q = q.filter(Dosen.homebase_prodi_id == homebase_prodi_id)

    if status is not None:
        q = q.filter(Dosen.status == status)

    if search is not None:
        pattern = f"%{search}%"
        q = q.filter(
            (Dosen.nama.ilike(pattern)) | (Dosen.kode.ilike(pattern))
        )

    return q.order_by(Dosen.nama).all()


@router.post("", response_model=DosenResponse, status_code=status.HTTP_201_CREATED)
def create_dosen(
    payload: DosenCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Buat dosen baru. Hanya EDITOR_ROLES_JURUSAN."""
    existing = db.query(Dosen).filter(Dosen.kode == payload.kode).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dosen dengan kode '{payload.kode}' sudah ada",
        )

    dosen = Dosen(**payload.model_dump())
    db.add(dosen)
    db.commit()
    db.refresh(dosen)
    return dosen


@router.put("/{dosen_id}", response_model=DosenResponse)
def update_dosen(
    dosen_id: uuid.UUID,
    payload: DosenUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Update dosen. Hanya EDITOR_ROLES_JURUSAN."""
    dosen = db.get(Dosen, dosen_id)
    if dosen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dosen dengan id '{dosen_id}' tidak ditemukan",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "kode" in update_data and update_data["kode"] != dosen.kode:
        conflict = (
            db.query(Dosen)
            .filter(Dosen.kode == update_data["kode"], Dosen.id != dosen_id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dosen dengan kode '{update_data['kode']}' sudah ada",
            )

    for field, value in update_data.items():
        setattr(dosen, field, value)

    db.commit()
    db.refresh(dosen)
    return dosen


# Roles allowed to manage unavailability (jurusan editors + dosen own)
_UNAVAIL_ROLES = EDITOR_ROLES_JURUSAN + ["dosen"]


def _get_dosen_or_404(dosen_id: uuid.UUID, db: Session) -> Dosen:
    dosen = db.get(Dosen, dosen_id)
    if dosen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dosen dengan id '{dosen_id}' tidak ditemukan",
        )
    return dosen


def _check_own_access(current_user, dosen: Dosen) -> None:
    """Dosen role may only access their own data."""
    if current_user.role == "dosen" and dosen.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dosen hanya dapat mengakses data unavailability milik sendiri",
        )


@router.post(
    "/{dosen_id}/unavailability",
    response_model=DosenUnavailabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_unavailability(
    dosen_id: uuid.UUID,
    payload: DosenUnavailabilityCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(_UNAVAIL_ROLES)),
):
    """Tambah slot unavailability untuk dosen. EDITOR_ROLES_JURUSAN atau dosen (own)."""
    dosen = _get_dosen_or_404(dosen_id, db)
    _check_own_access(current_user, dosen)

    if dosen.status != "Aktif":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Dosen tidak aktif",
        )

    # Validate timeslot exists
    if db.get(Timeslot, payload.timeslot_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timeslot dengan id '{payload.timeslot_id}' tidak ditemukan",
        )

    # Validate sesi exists if provided
    if payload.sesi_id is not None and db.get(SesiJadwal, payload.sesi_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sesi jadwal dengan id '{payload.sesi_id}' tidak ditemukan",
        )

    unavail = DosenUnavailability(
        dosen_id=dosen_id,
        timeslot_id=payload.timeslot_id,
        sesi_id=payload.sesi_id,
        catatan=payload.catatan,
    )
    db.add(unavail)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unavailability untuk kombinasi dosen/timeslot/sesi ini sudah ada",
        )
    db.refresh(unavail)
    return unavail


@router.get(
    "/{dosen_id}/unavailability",
    response_model=list[DosenUnavailabilityResponse],
)
def list_unavailability(
    dosen_id: uuid.UUID,
    sesi_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role(_UNAVAIL_ROLES)),
):
    """List semua unavailability slot untuk dosen. EDITOR_ROLES_JURUSAN atau dosen (own)."""
    dosen = _get_dosen_or_404(dosen_id, db)
    _check_own_access(current_user, dosen)

    q = db.query(DosenUnavailability).filter(DosenUnavailability.dosen_id == dosen_id)

    if sesi_id is not None:
        q = q.filter(DosenUnavailability.sesi_id == sesi_id)

    return q.all()


# ---------------------------------------------------------------------------
# Preference endpoints
# ---------------------------------------------------------------------------

_PREF_ROLES = EDITOR_ROLES_JURUSAN + ["dosen"]


def _check_own_pref_access(current_user, dosen: Dosen) -> None:
    """Dosen role may only manage their own preferences."""
    if current_user.role == "dosen" and dosen.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dosen hanya dapat mengelola preferensi milik sendiri",
        )


@router.get(
    "/{dosen_id}/preferences",
    response_model=list[DosenPreferenceResponse],
)
def list_preferences(
    dosen_id: uuid.UUID,
    fase: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role(_PREF_ROLES)),
):
    """List semua preferensi dosen. EDITOR_ROLES_JURUSAN atau dosen (own)."""
    dosen = _get_dosen_or_404(dosen_id, db)
    _check_own_pref_access(current_user, dosen)

    q = db.query(DosenPreference).filter(DosenPreference.dosen_id == dosen_id)
    if fase is not None:
        q = q.filter(DosenPreference.fase == fase)
    return q.all()


@router.post(
    "/{dosen_id}/preferences",
    response_model=DosenPreferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_preference(
    dosen_id: uuid.UUID,
    payload: DosenPreferenceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(_PREF_ROLES)),
):
    """Tambah preferensi dosen. EDITOR_ROLES_JURUSAN atau dosen (own)."""
    dosen = _get_dosen_or_404(dosen_id, db)
    _check_own_pref_access(current_user, dosen)

    if db.get(SesiJadwal, payload.sesi_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sesi jadwal dengan id '{payload.sesi_id}' tidak ditemukan",
        )
    if db.get(Timeslot, payload.timeslot_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timeslot dengan id '{payload.timeslot_id}' tidak ditemukan",
        )

    pref = DosenPreference(
        dosen_id=dosen_id,
        sesi_id=payload.sesi_id,
        timeslot_id=payload.timeslot_id,
        fase=payload.fase,
        catatan=payload.catatan,
    )
    db.add(pref)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Preferensi untuk kombinasi dosen/sesi/timeslot/fase ini sudah ada",
        )
    db.refresh(pref)
    return pref


@router.put(
    "/{dosen_id}/preferences/{pref_id}",
    response_model=DosenPreferenceResponse,
)
def update_preference(
    dosen_id: uuid.UUID,
    pref_id: uuid.UUID,
    payload: DosenPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(_PREF_ROLES)),
):
    """Update preferensi dosen. EDITOR_ROLES_JURUSAN atau dosen (own)."""
    dosen = _get_dosen_or_404(dosen_id, db)
    _check_own_pref_access(current_user, dosen)

    pref = db.get(DosenPreference, pref_id)
    if pref is None or pref.dosen_id != dosen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preferensi dengan id '{pref_id}' tidak ditemukan",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "timeslot_id" in update_data and db.get(Timeslot, update_data["timeslot_id"]) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timeslot dengan id '{update_data['timeslot_id']}' tidak ditemukan",
        )

    for field, value in update_data.items():
        setattr(pref, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Preferensi untuk kombinasi dosen/sesi/timeslot/fase ini sudah ada",
        )
    db.refresh(pref)
    return pref


@router.delete(
    "/{dosen_id}/preferences/{pref_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_preference(
    dosen_id: uuid.UUID,
    pref_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(_PREF_ROLES)),
):
    """Hapus preferensi dosen. EDITOR_ROLES_JURUSAN atau dosen (own)."""
    dosen = _get_dosen_or_404(dosen_id, db)
    _check_own_pref_access(current_user, dosen)

    pref = db.get(DosenPreference, pref_id)
    if pref is None or pref.dosen_id != dosen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preferensi dengan id '{pref_id}' tidak ditemukan",
        )

    db.delete(pref)
    db.commit()
