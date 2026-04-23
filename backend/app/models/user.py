"""
backend/app/models/user.py
SQLAlchemy ORM model untuk entitas User dengan enum role.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseMixin


class UserRole(str, enum.Enum):
    admin = "admin"
    ketua_jurusan = "ketua_jurusan"
    sekretaris_jurusan = "sekretaris_jurusan"
    koordinator_prodi = "koordinator_prodi"
    dosen = "dosen"
    tendik_prodi = "tendik_prodi"
    tendik_jurusan = "tendik_jurusan"


class User(BaseMixin, Base):
    __tablename__ = "user"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    # Store role as VARCHAR(30) — Python-level validation via UserRole enum
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    prodi_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prodi.id"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"
