"""
backend/app/schemas/report.py
Pydantic v2 schemas untuk endpoint laporan (reports).
"""

import uuid
from typing import Optional

from pydantic import BaseModel


class DosenSksRekap(BaseModel):
    dosen_id: uuid.UUID
    dosen_nama: str
    dosen_kode: str
    total_sks: int
    breakdown: dict[str, int]
    bkd_limit_sks: Optional[int]
    bkd_flag: str  # "ok" | "near_limit" | "over_limit" | "no_limit"


class SksRekapResponse(BaseModel):
    sesi_id: uuid.UUID
    items: list[DosenSksRekap]
    total_dosen: int


# ---------------------------------------------------------------------------
# Room-map schemas
# ---------------------------------------------------------------------------

class RoomCellInfo(BaseModel):
    """Informasi MK yang menempati sel ruang × timeslot."""
    kode_mk: str
    nama_mk: str
    kelas: Optional[str]
    dosen: str  # nama dosen1 (+ dosen2 jika ada)


class RoomMapSlot(BaseModel):
    """Satu baris dalam matrix: satu timeslot dengan semua ruang."""
    hari: str
    sesi: int
    label: str
    rooms: dict[str, Optional[RoomCellInfo]]  # nama_ruang → info atau None


class RoomMapResponse(BaseModel):
    sesi_id: uuid.UUID
    rooms: list[str]          # daftar nama ruang aktif (urut)
    days: list[str]           # daftar hari unik (urut)
    slots: list[RoomMapSlot]  # semua 15 timeslot dengan isi per ruang
