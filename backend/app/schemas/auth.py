"""
backend/app/schemas/auth.py
Pydantic v2 schemas for authentication endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: uuid.UUID
    username: str
    role: str

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    """Full user profile returned by GET /auth/me."""

    id: uuid.UUID
    username: str
    email: Optional[str]
    role: str
    prodi_id: Optional[uuid.UUID]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo
