"""
backend/app/routers/timeslot.py
CRUD endpoints untuk entitas Timeslot.

GET  /timeslot        — list semua timeslot (semua role terautentikasi)
POST /timeslot        — buat timeslot baru (admin only)
PUT  /timeslot/{id}   — update timeslot (admin only)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import require_role
from app.database import get_db
from app.models.timeslot import Timeslot
from app.schemas.timeslot import TimeslotCreate, TimeslotResponse, TimeslotUpdate

router = APIRouter(prefix="/timeslot", tags=["timeslot"])

_ADMIN_ONLY = ["admin"]


@router.get("", response_model=list[TimeslotResponse])
def list_timeslot(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return semua timeslot, diurutkan berdasarkan hari dan sesi."""
    return db.query(Timeslot).order_by(Timeslot.hari, Timeslot.sesi).all()


@router.post("", response_model=TimeslotResponse, status_code=status.HTTP_201_CREATED)
def create_timeslot(
    payload: TimeslotCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(_ADMIN_ONLY)),
):
    """Buat timeslot baru. Hanya admin."""
    existing = db.query(Timeslot).filter(Timeslot.kode == payload.kode).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Timeslot dengan kode '{payload.kode}' sudah ada",
        )

    timeslot = Timeslot(**payload.model_dump())
    db.add(timeslot)
    db.commit()
    db.refresh(timeslot)
    return timeslot


@router.put("/{timeslot_id}", response_model=TimeslotResponse)
def update_timeslot(
    timeslot_id: uuid.UUID,
    payload: TimeslotUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(_ADMIN_ONLY)),
):
    """Update timeslot. Hanya admin."""
    timeslot = db.get(Timeslot, timeslot_id)
    if timeslot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timeslot dengan id '{timeslot_id}' tidak ditemukan",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "kode" in update_data and update_data["kode"] != timeslot.kode:
        conflict = (
            db.query(Timeslot)
            .filter(Timeslot.kode == update_data["kode"], Timeslot.id != timeslot_id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Timeslot dengan kode '{update_data['kode']}' sudah ada",
            )

    for field, value in update_data.items():
        setattr(timeslot, field, value)

    db.commit()
    db.refresh(timeslot)
    return timeslot
