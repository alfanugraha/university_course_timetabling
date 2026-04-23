"""
backend/app/models/sesi_jadwal.py
SQLAlchemy ORM model untuk entitas SesiJadwal (sesi penjadwalan per semester).
"""

from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseMixin


class SesiJadwal(BaseMixin, Base):
    __tablename__ = "sesi_jadwal"

    __table_args__ = (
        UniqueConstraint("semester", "tahun_akademik", name="uq_sesi_semester_tahun"),
    )

    nama: Mapped[str] = mapped_column(String(100), nullable=False)
    semester: Mapped[str] = mapped_column(String(10), nullable=False)
    tahun_akademik: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Draft", nullable=False)

    def __repr__(self) -> str:
        return f"<SesiJadwal id={self.id} nama={self.nama!r} status={self.status!r}>"
