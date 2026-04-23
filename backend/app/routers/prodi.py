"""
backend/app/routers/prodi.py
CRUD endpoints untuk entitas Prodi.

GET  /prodi        — list semua prodi (semua role terautentikasi)
POST /prodi        — buat prodi baru (admin only)
PUT  /prodi/{id}   — update prodi (admin only)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import require_role
from app.database import get_db
from app.models.prodi import Prodi
from app.schemas.prodi import ProdiCreate, ProdiResponse, ProdiUpdate

router = APIRouter(prefix="/prodi", tags=["prodi"])


@router.get("", response_model=list[ProdiResponse])
def list_prodi(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return semua prodi (semua role terautentikasi)."""
    return db.query(Prodi).order_by(Prodi.kode).all()


@router.post("", response_model=ProdiResponse, status_code=status.HTTP_201_CREATED)
def create_prodi(
    payload: ProdiCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(["admin"])),
):
    """Buat prodi baru. Hanya admin."""
    existing = db.query(Prodi).filter(Prodi.kode == payload.kode).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Prodi dengan kode '{payload.kode}' sudah ada",
        )

    prodi = Prodi(**payload.model_dump())
    db.add(prodi)
    db.commit()
    db.refresh(prodi)
    return prodi


@router.put("/{prodi_id}", response_model=ProdiResponse)
def update_prodi(
    prodi_id: uuid.UUID,
    payload: ProdiUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(["admin"])),
):
    """Update prodi. Hanya admin."""
    prodi = db.get(Prodi, prodi_id)
    if prodi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prodi dengan id '{prodi_id}' tidak ditemukan",
        )

    # Check kode uniqueness if kode is being changed
    update_data = payload.model_dump(exclude_unset=True)
    if "kode" in update_data and update_data["kode"] != prodi.kode:
        conflict = (
            db.query(Prodi)
            .filter(Prodi.kode == update_data["kode"], Prodi.id != prodi_id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Prodi dengan kode '{update_data['kode']}' sudah ada",
            )

    for field, value in update_data.items():
        setattr(prodi, field, value)

    db.commit()
    db.refresh(prodi)
    return prodi
