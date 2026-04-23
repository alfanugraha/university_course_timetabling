"""
backend/app/schemas/kurikulum.py
Pydantic v2 schemas untuk entitas Kurikulum.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class KurikulumCreate(BaseModel):
    kode: str
    tahun: str
    prodi_id: uuid.UUID
    is_active: bool = True


class KurikulumUpdate(BaseModel):
    kode: Optional[str] = None
    tahun: Optional[str] = None
    prodi_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class KurikulumResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kode: str
    tahun: str
    prodi_id: uuid.UUID
    is_active: bool
    created_at: datetime
