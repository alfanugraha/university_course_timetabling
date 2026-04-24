"""
backend/app/schemas/user.py
Pydantic v2 schemas untuk entitas User.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    role: UserRole
    prodi_id: Optional[uuid.UUID] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRole] = None
    prodi_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: Optional[str]
    role: str
    prodi_id: Optional[uuid.UUID]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]


class ResetPasswordRequest(BaseModel):
    new_password: str
