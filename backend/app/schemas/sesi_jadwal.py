"""
backend/app/schemas/sesi_jadwal.py
Pydantic v2 schemas untuk entitas SesiJadwal.
"""

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class SesiJadwalCreate(BaseModel):
    nama: str
    semester: str
    tahun_akademik: str


class SesiJadwalUpdate(BaseModel):
    nama: Optional[str] = None
    semester: Optional[str] = None
    tahun_akademik: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("Draft", "Aktif", "Arsip"):
            raise ValueError("status harus salah satu dari: Draft, Aktif, Arsip")
        return v


class SesiJadwalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nama: str
    semester: str
    tahun_akademik: str
    status: str
    created_at: datetime


class ApproveRequest(BaseModel):
    action: Literal["approve", "request_revision"]
    catatan: Optional[str] = None


# ---------------------------------------------------------------------------
# Preferences summary schemas
# ---------------------------------------------------------------------------

class DosenPreferenceSummaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dosen_id: uuid.UUID
    kode: str
    nama: str
    total_preferensi: int
    total_dilanggar: int


class PreferencesSummaryResponse(BaseModel):
    sesi_id: uuid.UUID
    total_preferensi: int
    total_dilanggar: int
    breakdown: list[DosenPreferenceSummaryItem]
