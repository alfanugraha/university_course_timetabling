"""
backend/app/models/mata_kuliah.py
SQLAlchemy ORM model untuk entitas MataKuliah dan MataKuliahKelas.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin


class MataKuliah(BaseMixin, Base):
    __tablename__ = "mata_kuliah"

    kode: Mapped[str] = mapped_column(String(20), nullable=False)
    kurikulum_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kurikulum.id"),
        nullable=False,
    )
    nama: Mapped[str] = mapped_column(String(200), nullable=False)
    sks: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    semester: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    jenis: Mapped[str] = mapped_column(String(10), nullable=False)  # Wajib / Pilihan
    prasyarat: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("kode", "kurikulum_id", name="uq_mata_kuliah_kode_kurikulum"),
    )

    # Relationships
    kurikulum: Mapped["Kurikulum"] = relationship("Kurikulum", back_populates="mata_kuliahs")
    kelas_list: Mapped[list["MataKuliahKelas"]] = relationship(
        "MataKuliahKelas", back_populates="mata_kuliah", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MataKuliah id={self.id} kode={self.kode!r} nama={self.nama!r}>"


class MataKuliahKelas(BaseMixin, Base):
    __tablename__ = "mata_kuliah_kelas"

    mata_kuliah_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mata_kuliah.id"),
        nullable=False,
    )
    kelas: Mapped[str | None] = mapped_column(String(5), nullable=True)  # A, B, C, atau NULL
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    ket: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("mata_kuliah_id", "kelas", name="uq_mk_kelas"),
    )

    # Relationships
    mata_kuliah: Mapped["MataKuliah"] = relationship("MataKuliah", back_populates="kelas_list")

    def __repr__(self) -> str:
        return f"<MataKuliahKelas id={self.id} label={self.label!r}>"
