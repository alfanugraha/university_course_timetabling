"""
backend/app/models/timeslot.py
SQLAlchemy ORM model untuk entitas Timeslot.
15 slot tetap (3 sesi × 5 hari kerja). Tidak ada slot ad-hoc.
"""

from __future__ import annotations

import datetime

from sqlalchemy import SmallInteger, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseMixin


class Timeslot(BaseMixin, Base):
    __tablename__ = "timeslot"

    kode: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    hari: Mapped[str] = mapped_column(String(10), nullable=False)
    sesi: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    jam_mulai: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    jam_selesai: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    label: Mapped[str] = mapped_column(String(30), nullable=False)
    sks: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    def __repr__(self) -> str:
        return f"<Timeslot id={self.id} kode={self.kode!r} label={self.label!r}>"
