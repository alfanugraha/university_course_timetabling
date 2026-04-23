"""
backend/app/routers/mata_kuliah.py
CRUD endpoints untuk entitas MataKuliah dan MataKuliahKelas.

GET    /mata-kuliah                          — list dengan filter opsional (semua role terautentikasi)
POST   /mata-kuliah                          — buat MataKuliah baru (EDITOR_ROLES_JURUSAN)
PUT    /mata-kuliah/{id}                     — update MataKuliah (EDITOR_ROLES_JURUSAN)
DELETE /mata-kuliah/{id}                     — soft delete MataKuliah (EDITOR_ROLES_JURUSAN)
GET    /mata-kuliah/{id}/kelas               — list kelas untuk MataKuliah (semua role terautentikasi)
POST   /mata-kuliah/{id}/kelas               — buat kelas baru (EDITOR_ROLES_JURUSAN)
PUT    /mata-kuliah/{id}/kelas/{kelas_id}    — update kelas (EDITOR_ROLES_JURUSAN)
DELETE /mata-kuliah/{id}/kelas/{kelas_id}    — hapus kelas (EDITOR_ROLES_JURUSAN)
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import EDITOR_ROLES_JURUSAN, require_role
from app.database import get_db
from app.models.kurikulum import Kurikulum
from app.models.mata_kuliah import MataKuliah, MataKuliahKelas
from app.schemas.mata_kuliah import (
    MataKuliahCreate,
    MataKuliahKelasCreate,
    MataKuliahKelasResponse,
    MataKuliahKelasUpdate,
    MataKuliahResponse,
    MataKuliahUpdate,
)

router = APIRouter(prefix="/mata-kuliah", tags=["mata-kuliah"])


@router.get("", response_model=list[MataKuliahResponse])
def list_mata_kuliah(
    prodi_id: Optional[uuid.UUID] = Query(None),
    kurikulum_id: Optional[uuid.UUID] = Query(None),
    semester: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """List MataKuliah dengan filter opsional. Semua role terautentikasi."""
    q = db.query(MataKuliah).filter(MataKuliah.is_active == True)  # noqa: E712

    if prodi_id is not None:
        q = q.join(Kurikulum, MataKuliah.kurikulum_id == Kurikulum.id).filter(
            Kurikulum.prodi_id == prodi_id
        )

    if kurikulum_id is not None:
        q = q.filter(MataKuliah.kurikulum_id == kurikulum_id)

    if semester is not None:
        q = q.filter(MataKuliah.semester == semester)

    return q.order_by(MataKuliah.kode).all()


@router.post("", response_model=MataKuliahResponse, status_code=status.HTTP_201_CREATED)
def create_mata_kuliah(
    payload: MataKuliahCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Buat MataKuliah baru. Hanya EDITOR_ROLES_JURUSAN."""
    existing = (
        db.query(MataKuliah)
        .filter(
            MataKuliah.kode == payload.kode,
            MataKuliah.kurikulum_id == payload.kurikulum_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"MataKuliah dengan kode '{payload.kode}' sudah ada di kurikulum ini",
        )

    mk = MataKuliah(**payload.model_dump())
    db.add(mk)
    db.commit()
    db.refresh(mk)
    return mk


@router.put("/{mk_id}", response_model=MataKuliahResponse)
def update_mata_kuliah(
    mk_id: uuid.UUID,
    payload: MataKuliahUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Update MataKuliah. Hanya EDITOR_ROLES_JURUSAN."""
    mk = db.get(MataKuliah, mk_id)
    if mk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MataKuliah dengan id '{mk_id}' tidak ditemukan",
        )

    update_data = payload.model_dump(exclude_unset=True)

    # Check uniqueness if kode or kurikulum_id changes
    new_kode = update_data.get("kode", mk.kode)
    new_kurikulum_id = update_data.get("kurikulum_id", mk.kurikulum_id)
    if new_kode != mk.kode or new_kurikulum_id != mk.kurikulum_id:
        conflict = (
            db.query(MataKuliah)
            .filter(
                MataKuliah.kode == new_kode,
                MataKuliah.kurikulum_id == new_kurikulum_id,
                MataKuliah.id != mk_id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"MataKuliah dengan kode '{new_kode}' sudah ada di kurikulum ini",
            )

    for field, value in update_data.items():
        setattr(mk, field, value)

    db.commit()
    db.refresh(mk)
    return mk


@router.delete("/{mk_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mata_kuliah(
    mk_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Soft delete MataKuliah (set is_active=False). Hanya EDITOR_ROLES_JURUSAN."""
    mk = db.get(MataKuliah, mk_id)
    if mk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MataKuliah dengan id '{mk_id}' tidak ditemukan",
        )

    mk.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# MataKuliahKelas endpoints
# ---------------------------------------------------------------------------

@router.get("/{mk_id}/kelas", response_model=list[MataKuliahKelasResponse])
def list_kelas(
    mk_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """List semua kelas untuk MataKuliah tertentu. Semua role terautentikasi."""
    mk = db.get(MataKuliah, mk_id)
    if mk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MataKuliah dengan id '{mk_id}' tidak ditemukan",
        )
    return (
        db.query(MataKuliahKelas)
        .filter(MataKuliahKelas.mata_kuliah_id == mk_id)
        .order_by(MataKuliahKelas.kelas)
        .all()
    )


@router.post(
    "/{mk_id}/kelas",
    response_model=MataKuliahKelasResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_kelas(
    mk_id: uuid.UUID,
    payload: MataKuliahKelasCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Buat kelas baru untuk MataKuliah. Hanya EDITOR_ROLES_JURUSAN."""
    mk = db.get(MataKuliah, mk_id)
    if mk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MataKuliah dengan id '{mk_id}' tidak ditemukan",
        )

    existing = (
        db.query(MataKuliahKelas)
        .filter(
            MataKuliahKelas.mata_kuliah_id == mk_id,
            MataKuliahKelas.kelas == payload.kelas,
        )
        .first()
    )
    if existing:
        kelas_label = f"'{payload.kelas}'" if payload.kelas else "NULL"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Kelas {kelas_label} sudah ada untuk MataKuliah ini",
        )

    kelas = MataKuliahKelas(mata_kuliah_id=mk_id, **payload.model_dump())
    db.add(kelas)
    db.commit()
    db.refresh(kelas)
    return kelas


@router.put("/{mk_id}/kelas/{kelas_id}", response_model=MataKuliahKelasResponse)
def update_kelas(
    mk_id: uuid.UUID,
    kelas_id: uuid.UUID,
    payload: MataKuliahKelasUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Update kelas. Hanya EDITOR_ROLES_JURUSAN."""
    kelas = db.get(MataKuliahKelas, kelas_id)
    if kelas is None or kelas.mata_kuliah_id != mk_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Kelas dengan id '{kelas_id}' tidak ditemukan untuk MataKuliah ini",
        )

    update_data = payload.model_dump(exclude_unset=True)

    # Check uniqueness if kelas identifier changes
    new_kelas = update_data.get("kelas", kelas.kelas)
    if new_kelas != kelas.kelas:
        conflict = (
            db.query(MataKuliahKelas)
            .filter(
                MataKuliahKelas.mata_kuliah_id == mk_id,
                MataKuliahKelas.kelas == new_kelas,
                MataKuliahKelas.id != kelas_id,
            )
            .first()
        )
        if conflict:
            kelas_label = f"'{new_kelas}'" if new_kelas else "NULL"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Kelas {kelas_label} sudah ada untuk MataKuliah ini",
            )

    for field, value in update_data.items():
        setattr(kelas, field, value)

    db.commit()
    db.refresh(kelas)
    return kelas


@router.delete("/{mk_id}/kelas/{kelas_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kelas(
    mk_id: uuid.UUID,
    kelas_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Hapus kelas (hard delete). Hanya EDITOR_ROLES_JURUSAN."""
    kelas = db.get(MataKuliahKelas, kelas_id)
    if kelas is None or kelas.mata_kuliah_id != mk_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Kelas dengan id '{kelas_id}' tidak ditemukan untuk MataKuliah ini",
        )

    db.delete(kelas)
    db.commit()
