"""
backend/app/schemas/assignment.py
Pydantic v2 schemas untuk entitas JadwalAssignment.
"""

import uuid
from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AssignmentCreate(BaseModel):
    mk_kelas_id: uuid.UUID
    dosen1_id: uuid.UUID
    dosen2_id: Optional[uuid.UUID] = None
    timeslot_id: uuid.UUID
    ruang_id: Optional[uuid.UUID] = None
    override_floor_priority: bool = False
    catatan: Optional[str] = None


class AssignmentUpdate(BaseModel):
    mk_kelas_id: Optional[uuid.UUID] = None
    dosen1_id: Optional[uuid.UUID] = None
    dosen2_id: Optional[uuid.UUID] = None
    timeslot_id: Optional[uuid.UUID] = None
    ruang_id: Optional[uuid.UUID] = None
    catatan: Optional[str] = None


class ProdiInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kode: str
    nama: str
    singkat: str


class TimeslotInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kode: str
    hari: str
    sesi: int
    jam_mulai: time
    jam_selesai: time
    label: str


class RuangInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nama: str
    kapasitas: int
    lantai: Optional[int]
    gedung: Optional[str]


class DosenInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kode: str
    nama: str


class MkKelasInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    kelas: Optional[str]
    mata_kuliah_kode: str
    mata_kuliah_nama: str
    semester: int
    sks: int
    prodi: ProdiInfo


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sesi_id: uuid.UUID
    mk_kelas_id: uuid.UUID
    dosen1_id: uuid.UUID
    dosen2_id: Optional[uuid.UUID]
    timeslot_id: uuid.UUID
    ruang_id: Optional[uuid.UUID]
    override_floor_priority: bool
    catatan: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Nested info
    mk_kelas: MkKelasInfo
    dosen1: DosenInfo
    dosen2: Optional[DosenInfo]
    timeslot: TimeslotInfo
    ruang: Optional[RuangInfo]


class AssignmentListResponse(BaseModel):
    items: list[AssignmentResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Team Teaching schemas
# ---------------------------------------------------------------------------

class TeamTeachingOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assignment_id: uuid.UUID
    dosen_id: uuid.UUID
    urutan_pra_uts: int
    urutan_pasca_uts: Optional[int]
    catatan: Optional[str]


class TeamTeachingResponse(BaseModel):
    items: list[TeamTeachingOrderOut]


class TeamTeachingSetItem(BaseModel):
    dosen_id: uuid.UUID
    urutan_pra_uts: int


class TeamTeachingSetRequest(BaseModel):
    orders: list[TeamTeachingSetItem]


class TeamTeachingSwapItem(BaseModel):
    dosen_id: uuid.UUID
    urutan_pasca_uts: int


class TeamTeachingSwapRequest(BaseModel):
    orders: list[TeamTeachingSwapItem]
