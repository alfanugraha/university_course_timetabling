"""
backend/app/schemas/prodi.py
Pydantic v2 schemas untuk entitas Prodi.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProdiCreate(BaseModel):
    kode: str
    strata: str
    nama: str
    singkat: str
    kategori: str
    is_active: bool = True


class ProdiUpdate(BaseModel):
    kode: Optional[str] = None
    strata: Optional[str] = None
    nama: Optional[str] = None
    singkat: Optional[str] = None
    kategori: Optional[str] = None
    is_active: Optional[bool] = None


class ProdiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kode: str
    strata: str
    nama: str
    singkat: str
    kategori: str
    is_active: bool
    created_at: datetime
