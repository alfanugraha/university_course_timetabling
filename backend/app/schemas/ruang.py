"""
backend/app/schemas/ruang.py
Pydantic v2 schemas untuk entitas Ruang.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RuangCreate(BaseModel):
    nama: str
    kapasitas: int = 45
    lantai: Optional[int] = None
    gedung: Optional[str] = None
    jenis: str = "Kelas"
    is_active: bool = True


class RuangUpdate(BaseModel):
    nama: Optional[str] = None
    kapasitas: Optional[int] = None
    lantai: Optional[int] = None
    gedung: Optional[str] = None
    jenis: Optional[str] = None
    is_active: Optional[bool] = None


class RuangResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nama: str
    kapasitas: int
    lantai: Optional[int]
    gedung: Optional[str]
    jenis: str
    is_active: bool
    created_at: datetime
