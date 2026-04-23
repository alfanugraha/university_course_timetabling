"""
backend/app/models/prodi.py
SQLAlchemy ORM model untuk entitas Prodi (Program Studi).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.kurikulum import Kurikulum


class Prodi(BaseMixin, Base):
    __tablename__ = "prodi"

    kode: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    strata: Mapped[str] = mapped_column(String(5), nullable=False)
    nama: Mapped[str] = mapped_column(String(100), nullable=False)
    singkat: Mapped[str] = mapped_column(String(20), nullable=False)
    kategori: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    kurikulums: Mapped[List["Kurikulum"]] = relationship(
        "Kurikulum", back_populates="prodi"
    )

    def __repr__(self) -> str:
        return f"<Prodi id={self.id} kode={self.kode!r} nama={self.nama!r}>"
