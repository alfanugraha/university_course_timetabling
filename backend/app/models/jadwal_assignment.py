"""
backend/app/models/jadwal_assignment.py
SQLAlchemy ORM model untuk entitas JadwalAssignment dan TeamTeachingOrder.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.dosen import Dosen
    from app.models.mata_kuliah import MataKuliahKelas
    from app.models.ruang import Ruang
    from app.models.sesi_jadwal import SesiJadwal
    from app.models.timeslot import Timeslot


class JadwalAssignment(BaseMixin, Base):
    __tablename__ = "jadwal_assignment"

    sesi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sesi_jadwal.id"), nullable=False
    )
    mk_kelas_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mata_kuliah_kelas.id"), nullable=False
    )
    dosen1_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dosen.id"), nullable=False
    )
    dosen2_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dosen.id"), nullable=True
    )
    timeslot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timeslot.id"), nullable=False
    )
    ruang_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ruang.id"), nullable=True
    )
    override_floor_priority: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    catatan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    sesi: Mapped["SesiJadwal"] = relationship("SesiJadwal")
    dosen1: Mapped["Dosen"] = relationship("Dosen", foreign_keys=[dosen1_id])
    dosen2: Mapped[Optional["Dosen"]] = relationship("Dosen", foreign_keys=[dosen2_id])
    mk_kelas: Mapped["MataKuliahKelas"] = relationship("MataKuliahKelas")
    timeslot: Mapped["Timeslot"] = relationship("Timeslot")
    ruang: Mapped[Optional["Ruang"]] = relationship("Ruang")
    team_teaching_orders: Mapped[List["TeamTeachingOrder"]] = relationship(
        "TeamTeachingOrder", back_populates="assignment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("sesi_id", "mk_kelas_id", name="uq_assignment_sesi_mk_kelas"),
        # Indexes untuk conflict detection queries
        Index("idx_assignment_dosen1", "sesi_id", "dosen1_id", "timeslot_id"),
        Index("idx_assignment_dosen2", "sesi_id", "dosen2_id", "timeslot_id"),
        Index("idx_assignment_ruang", "sesi_id", "ruang_id", "timeslot_id"),
    )

    def __repr__(self) -> str:
        return f"<JadwalAssignment id={self.id} sesi_id={self.sesi_id} mk_kelas_id={self.mk_kelas_id}>"


class TeamTeachingOrder(BaseMixin, Base):
    __tablename__ = "team_teaching_order"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jadwal_assignment.id"), nullable=False
    )
    dosen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dosen.id"), nullable=False
    )
    urutan_pra_uts: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    urutan_pasca_uts: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    catatan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    assignment: Mapped["JadwalAssignment"] = relationship(
        "JadwalAssignment", back_populates="team_teaching_orders"
    )
    dosen: Mapped["Dosen"] = relationship("Dosen", foreign_keys=[dosen_id])

    __table_args__ = (
        UniqueConstraint("assignment_id", "dosen_id", name="uq_team_teaching_order"),
    )

    def __repr__(self) -> str:
        return (
            f"<TeamTeachingOrder id={self.id} assignment_id={self.assignment_id} "
            f"dosen_id={self.dosen_id} urutan_pra_uts={self.urutan_pra_uts}>"
        )
