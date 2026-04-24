"""
backend/app/schemas/conflict.py
Pydantic v2 schemas untuk conflict detection API.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ConflictLogResponse(BaseModel):
    """Schema untuk satu entri ConflictLog."""

    id: uuid.UUID
    sesi_id: uuid.UUID
    jenis: str
    severity: str
    assignment_ids: List[uuid.UUID]
    pesan: str
    detail: Optional[Dict[str, Any]] = None
    checked_at: datetime
    is_resolved: bool

    model_config = {"from_attributes": True}


class ConflictCheckSummary(BaseModel):
    """Ringkasan hasil check-conflicts: jumlah ERROR dan WARNING."""

    sesi_id: uuid.UUID
    total_error: int
    total_warning: int
    total: int
    conflicts: List[ConflictLogResponse]


class ConflictListResponse(BaseModel):
    """Daftar konflik dari conflict_log terbaru dengan pagination."""

    items: List[ConflictLogResponse]
    total: int


class ConflictResolveResponse(BaseModel):
    """Response setelah menandai konflik sebagai resolved."""

    id: uuid.UUID
    is_resolved: bool
    pesan: str

    model_config = {"from_attributes": True}
