"""
backend/app/routers/ruang.py
CRUD endpoints untuk entitas Ruang.

GET  /ruang        — list semua ruang (semua role terautentikasi)
POST /ruang        — buat ruang baru (EDITOR_ROLES_JURUSAN)
PUT  /ruang/{id}   — update ruang (EDITOR_ROLES_JURUSAN)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import EDITOR_ROLES_JURUSAN, require_role
from app.database import get_db
from app.models.ruang import Ruang
from app.schemas.ruang import RuangCreate, RuangResponse, RuangUpdate

router = APIRouter(prefix="/ruang", tags=["ruang"])


@router.get("", response_model=list[RuangResponse])
def list_ruang(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return semua ruang. Default hanya yang aktif."""
    q = db.query(Ruang)
    if not include_inactive:
        q = q.filter(Ruang.is_active == True)  # noqa: E712
    return q.order_by(Ruang.nama).all()


@router.post("", response_model=RuangResponse, status_code=status.HTTP_201_CREATED)
def create_ruang(
    payload: RuangCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Buat ruang baru. Hanya EDITOR_ROLES_JURUSAN."""
    existing = db.query(Ruang).filter(Ruang.nama == payload.nama).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ruang dengan nama '{payload.nama}' sudah ada",
        )

    ruang = Ruang(**payload.model_dump())
    db.add(ruang)
    db.commit()
    db.refresh(ruang)
    return ruang


@router.put("/{ruang_id}", response_model=RuangResponse)
def update_ruang(
    ruang_id: uuid.UUID,
    payload: RuangUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Update ruang. Hanya EDITOR_ROLES_JURUSAN."""
    ruang = db.get(Ruang, ruang_id)
    if ruang is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ruang dengan id '{ruang_id}' tidak ditemukan",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "nama" in update_data and update_data["nama"] != ruang.nama:
        conflict = (
            db.query(Ruang)
            .filter(Ruang.nama == update_data["nama"], Ruang.id != ruang_id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ruang dengan nama '{update_data['nama']}' sudah ada",
            )

    for field, value in update_data.items():
        setattr(ruang, field, value)

    db.commit()
    db.refresh(ruang)
    return ruang
