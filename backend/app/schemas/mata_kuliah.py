"""
backend/app/schemas/mata_kuliah.py
Pydantic v2 schemas untuk entitas MataKuliah dan MataKuliahKelas.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MataKuliahCreate(BaseModel):
    kode: str
    kurikulum_id: uuid.UUID
    nama: str
    sks: int
    semester: int
    jenis: str  # Wajib / Pilihan
    prasyarat: Optional[str] = None


class MataKuliahUpdate(BaseModel):
    kode: Optional[str] = None
    kurikulum_id: Optional[uuid.UUID] = None
    nama: Optional[str] = None
    sks: Optional[int] = None
    semester: Optional[int] = None
    jenis: Optional[str] = None
    prasyarat: Optional[str] = None


class KurikulumNested(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kode: str
    tahun: str
    prodi_id: uuid.UUID


class MataKuliahResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kode: str
    kurikulum_id: uuid.UUID
    nama: str
    sks: int
    semester: int
    jenis: str
    prasyarat: Optional[str]
    is_active: bool
    created_at: datetime
    kurikulum: Optional[KurikulumNested] = None


# ---------------------------------------------------------------------------
# MataKuliahKelas schemas
# ---------------------------------------------------------------------------

class MataKuliahKelasCreate(BaseModel):
    kelas: Optional[str] = None
    label: str
    ket: Optional[str] = None


class MataKuliahKelasUpdate(BaseModel):
    kelas: Optional[str] = None
    label: Optional[str] = None
    ket: Optional[str] = None


class MataKuliahKelasResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mata_kuliah_id: uuid.UUID
    kelas: Optional[str]
    label: str
    ket: Optional[str]
    created_at: datetime
