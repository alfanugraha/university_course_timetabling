"""
backend/app/models/conflict_log.py
SQLAlchemy ORM model untuk entitas ConflictLog.
Menyimpan hasil deteksi konflik dari conflict engine per sesi jadwal.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String

from app.models.base import Base, BaseMixin

if TYPE_CHECKING:
    from app.models.sesi_jadwal import SesiJadwal


class ConflictLog(BaseMixin, Base):
    __tablename__ = "conflict_log"

    sesi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sesi_jadwal.id"), nullable=False
    )
    jenis: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    assignment_ids: Mapped[List[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False
    )
    pesan: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    sesi: Mapped["SesiJadwal"] = relationship("SesiJadwal")

    def __repr__(self) -> str:
        return (
            f"<ConflictLog id={self.id} jenis={self.jenis!r} "
            f"severity={self.severity!r} sesi_id={self.sesi_id}>"
        )
