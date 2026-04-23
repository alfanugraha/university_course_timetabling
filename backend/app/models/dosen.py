"""
backend/app/models/dosen.py
SQLAlchemy ORM model untuk entitas Dosen, DosenUnavailability, dan DosenPreference.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.prodi import Prodi
    from app.models.user import User


class Dosen(BaseMixin, Base):
    __tablename__ = "dosen"

    nidn: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    nip: Mapped[Optional[str]] = mapped_column(String(25), unique=True, nullable=True)
    kode: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    nama: Mapped[str] = mapped_column(String(200), nullable=False)
    jabfung: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    kjfd: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    homebase_prodi_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prodi.id"),
        nullable=True,
    )
    # Placeholder untuk batas BKD fase berikutnya; tidak divalidasi di Fase 1
    bkd_limit_sks: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    tgl_lahir: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Aktif", nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=True,
    )

    # Relationships
    homebase_prodi: Mapped[Optional["Prodi"]] = relationship(
        "Prodi", foreign_keys=[homebase_prodi_id]
    )
    user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[user_id]
    )
    unavailabilities: Mapped[List["DosenUnavailability"]] = relationship(
        "DosenUnavailability", back_populates="dosen", cascade="all, delete-orphan"
    )
    preferences: Mapped[List["DosenPreference"]] = relationship(
        "DosenPreference", back_populates="dosen", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Dosen id={self.id} kode={self.kode!r} nama={self.nama!r}>"


class DosenUnavailability(BaseMixin, Base):
    __tablename__ = "dosen_unavailability"

    dosen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dosen.id"), nullable=False
    )
    timeslot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timeslot.id"), nullable=False
    )
    sesi_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sesi_jadwal.id"), nullable=True
    )
    catatan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    dosen: Mapped["Dosen"] = relationship("Dosen", back_populates="unavailabilities")

    __table_args__ = (
        UniqueConstraint("dosen_id", "timeslot_id", "sesi_id", name="uq_dosen_unavail"),
    )

    def __repr__(self) -> str:
        return f"<DosenUnavailability dosen_id={self.dosen_id} timeslot_id={self.timeslot_id}>"


class DosenPreference(BaseMixin, Base):
    __tablename__ = "dosen_preference"

    dosen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dosen.id"), nullable=False
    )
    sesi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sesi_jadwal.id"), nullable=False
    )
    timeslot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timeslot.id"), nullable=False
    )
    fase: Mapped[str] = mapped_column(String(15), nullable=False)  # pre_schedule / post_draft
    catatan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_violated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    dosen: Mapped["Dosen"] = relationship("Dosen", back_populates="preferences")

    __table_args__ = (
        UniqueConstraint(
            "dosen_id", "sesi_id", "timeslot_id", "fase",
            name="uq_dosen_preference"
        ),
    )

    def __repr__(self) -> str:
        return f"<DosenPreference dosen_id={self.dosen_id} fase={self.fase!r}>"
