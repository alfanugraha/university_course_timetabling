"""
backend/app/routers/users.py
CRUD endpoints untuk entitas User (admin only).

GET   /users                    — list semua user (admin only)
POST  /users                    — buat user baru (admin only)
PUT   /users/{id}               — update user (admin only); username tidak bisa diubah
PATCH /users/{id}/reset-password — reset password user (admin only)
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import require_role
from app.core.security import hash_password
from app.database import get_db
from app.models.user import User
from app.schemas.user import ResetPasswordRequest, UserCreate, UserResponse, UserUpdate

_ADMIN_ONLY = ["admin"]

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(_ADMIN_ONLY)),
):
    """List semua user. Hanya admin."""
    q = db.query(User)

    if role is not None:
        q = q.filter(User.role == role)

    if is_active is not None:
        q = q.filter(User.is_active == is_active)

    return q.order_by(User.username).all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(_ADMIN_ONLY)),
):
    """Buat user baru. Hanya admin. Password di-hash dengan bcrypt."""
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User dengan username '{payload.username}' sudah ada",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role.value,
        prodi_id=payload.prodi_id,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User dengan username atau email tersebut sudah ada",
        )
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(_ADMIN_ONLY)),
):
    """Update user. Hanya admin. Username tidak dapat diubah."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User dengan id '{user_id}' tidak ditemukan",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "role" and value is not None:
            setattr(user, field, value.value if hasattr(value, "value") else value)
        else:
            setattr(user, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email tersebut sudah digunakan oleh user lain",
        )
    db.refresh(user)
    return user


@router.patch("/{user_id}/reset-password", response_model=UserResponse)
def reset_password(
    user_id: uuid.UUID,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(_ADMIN_ONLY)),
):
    """Reset password user. Hanya admin. Password baru di-hash dengan bcrypt."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User dengan id '{user_id}' tidak ditemukan",
        )

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    return user
