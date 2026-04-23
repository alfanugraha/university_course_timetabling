"""
backend/app/models/kurikulum.py
SQLAlchemy ORM model untuk entitas Kurikulum dengan relasi FK ke Prodi.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin


class Kurikulum(BaseMixin, Base):
    __tablename__ = "kurikulum"

    kode: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    tahun: Mapped[str] = mapped_column(String(4), nullable=False)
    prodi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prodi.id"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    prodi: Mapped["Prodi"] = relationship("Prodi", back_populates="kurikulums")
    mata_kuliahs: Mapped[list["MataKuliah"]] = relationship(
        "MataKuliah", back_populates="kurikulum", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Kurikulum id={self.id} kode={self.kode!r} tahun={self.tahun!r}>"
