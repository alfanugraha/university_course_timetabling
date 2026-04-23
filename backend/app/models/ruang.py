"""
backend/app/models/ruang.py
SQLAlchemy ORM model untuk entitas Ruang (ruang/kelas kuliah).
"""

from __future__ import annotations

from sqlalchemy import Boolean, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseMixin


class Ruang(BaseMixin, Base):
    __tablename__ = "ruang"

    nama: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    kapasitas: Mapped[int] = mapped_column(SmallInteger, default=45, nullable=False)
    lantai: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    gedung: Mapped[str | None] = mapped_column(String(100), nullable=True)
    jenis: Mapped[str] = mapped_column(String(20), default="Kelas", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Ruang id={self.id} nama={self.nama!r} jenis={self.jenis!r}>"
