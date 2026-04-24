"""
backend/app/schemas/timeslot.py
Pydantic v2 schemas untuk entitas Timeslot.
"""

import uuid
from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TimeslotBase(BaseModel):
    kode: str
    hari: str
    sesi: int
    jam_mulai: time
    jam_selesai: time
    label: str
    sks: int = 3


class TimeslotCreate(TimeslotBase):
    pass


class TimeslotUpdate(BaseModel):
    kode: Optional[str] = None
    hari: Optional[str] = None
    sesi: Optional[int] = None
    jam_mulai: Optional[time] = None
    jam_selesai: Optional[time] = None
    label: Optional[str] = None
    sks: Optional[int] = None


class TimeslotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kode: str
    hari: str
    sesi: int
    jam_mulai: time
    jam_selesai: time
    label: str
    sks: int
    created_at: datetime
