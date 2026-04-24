"""
backend/app/schemas/dosen.py
Pydantic v2 schemas untuk entitas Dosen.
"""

import uuid
from datetime import date, datetime, time
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class DosenCreate(BaseModel):
    kode: str
    nama: str
    nidn: Optional[str] = None
    nip: Optional[str] = None
    jabfung: Optional[str] = None
    kjfd: Optional[str] = None
    homebase_prodi_id: Optional[uuid.UUID] = None
    bkd_limit_sks: Optional[int] = None  # placeholder, tidak divalidasi
    tgl_lahir: Optional[date] = None
    status: str = "Aktif"
    user_id: Optional[uuid.UUID] = None


class DosenUpdate(BaseModel):
    kode: Optional[str] = None
    nama: Optional[str] = None
    nidn: Optional[str] = None
    nip: Optional[str] = None
    jabfung: Optional[str] = None
    kjfd: Optional[str] = None
    homebase_prodi_id: Optional[uuid.UUID] = None
    bkd_limit_sks: Optional[int] = None
    tgl_lahir: Optional[date] = None
    status: Optional[str] = None
    user_id: Optional[uuid.UUID] = None


class DosenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kode: str
    nama: str
    nidn: Optional[str]
    nip: Optional[str]
    jabfung: Optional[str]
    kjfd: Optional[str]
    homebase_prodi_id: Optional[uuid.UUID]
    bkd_limit_sks: Optional[int]
    tgl_lahir: Optional[date]
    status: str
    user_id: Optional[uuid.UUID]
    created_at: datetime


# ---------------------------------------------------------------------------
# DosenUnavailability schemas
# ---------------------------------------------------------------------------

class TimeslotBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kode: str
    hari: str
    sesi: int
    jam_mulai: time
    jam_selesai: time
    label: str


class SesiBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nama: str
    semester: str
    tahun_akademik: str


class DosenUnavailabilityCreate(BaseModel):
    timeslot_id: uuid.UUID
    sesi_id: Optional[uuid.UUID] = None
    catatan: Optional[str] = None


class DosenUnavailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dosen_id: uuid.UUID
    timeslot_id: uuid.UUID
    sesi_id: Optional[uuid.UUID]
    catatan: Optional[str]
    created_at: datetime
    timeslot: Optional[TimeslotBrief] = None
    sesi: Optional[SesiBrief] = None


# ---------------------------------------------------------------------------
# DosenPreference schemas
# ---------------------------------------------------------------------------

class DosenPreferenceCreate(BaseModel):
    sesi_id: uuid.UUID
    timeslot_id: uuid.UUID
    fase: Literal["pre_schedule", "post_draft"]
    catatan: Optional[str] = None


class DosenPreferenceUpdate(BaseModel):
    fase: Optional[Literal["pre_schedule", "post_draft"]] = None
    timeslot_id: Optional[uuid.UUID] = None
    catatan: Optional[str] = None


class DosenPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dosen_id: uuid.UUID
    sesi_id: uuid.UUID
    timeslot_id: uuid.UUID
    fase: str
    catatan: Optional[str]
    is_violated: bool
    created_at: datetime
