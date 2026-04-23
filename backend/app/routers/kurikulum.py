"""
backend/app/routers/kurikulum.py
CRUD endpoints untuk entitas Kurikulum.

GET  /kurikulum        — list semua kurikulum (semua role terautentikasi)
POST /kurikulum        — buat kurikulum baru (admin only)
PUT  /kurikulum/{id}   — update kurikulum (admin only)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import require_role
from app.database import get_db
from app.models.kurikulum import Kurikulum
from app.schemas.kurikulum import KurikulumCreate, KurikulumResponse, KurikulumUpdate

router = APIRouter(prefix="/kurikulum", tags=["kurikulum"])


@router.get("", response_model=list[KurikulumResponse])
def list_kurikulum(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return semua kurikulum (semua role terautentikasi)."""
    return db.query(Kurikulum).order_by(Kurikulum.kode).all()


@router.post("", response_model=KurikulumResponse, status_code=status.HTTP_201_CREATED)
def create_kurikulum(
    payload: KurikulumCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(["admin"])),
):
    """Buat kurikulum baru. Hanya admin."""
    existing = db.query(Kurikulum).filter(Kurikulum.kode == payload.kode).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Kurikulum dengan kode '{payload.kode}' sudah ada",
        )

    kurikulum = Kurikulum(**payload.model_dump())
    db.add(kurikulum)
    db.commit()
    db.refresh(kurikulum)
    return kurikulum


@router.put("/{kurikulum_id}", response_model=KurikulumResponse)
def update_kurikulum(
    kurikulum_id: uuid.UUID,
    payload: KurikulumUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(["admin"])),
):
    """Update kurikulum. Hanya admin."""
    kurikulum = db.get(Kurikulum, kurikulum_id)
    if kurikulum is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Kurikulum dengan id '{kurikulum_id}' tidak ditemukan",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "kode" in update_data and update_data["kode"] != kurikulum.kode:
        conflict = (
            db.query(Kurikulum)
            .filter(Kurikulum.kode == update_data["kode"], Kurikulum.id != kurikulum_id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Kurikulum dengan kode '{update_data['kode']}' sudah ada",
            )

    for field, value in update_data.items():
        setattr(kurikulum, field, value)

    db.commit()
    db.refresh(kurikulum)
    return kurikulum
