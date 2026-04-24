"""
backend/tests/test_conflict_api.py
Unit tests for conflict detection API endpoints.

Covers:
  POST  /sesi/{id}/check-conflicts        — T4.2.1
  GET   /sesi/{id}/conflicts              — T4.2.2
  PATCH /sesi/{id}/conflicts/{cid}/resolve — T4.2.3
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
from app.models.conflict_log import ConflictLog as ConflictLogModel
from app.models.sesi_jadwal import SesiJadwal as SesiJadwalModel
from app.models.user import User as UserModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(role: str = "admin") -> MagicMock:
    user = MagicMock(spec=UserModel)
    user.id = uuid.uuid4()
    user.username = f"user_{role}"
    user.role = role
    user.is_active = True
    return user


def _make_sesi(status: str = "Aktif") -> MagicMock:
    sesi = MagicMock(spec=SesiJadwalModel)
    sesi.id = uuid.uuid4()
    sesi.nama = "Genap 2025-2026"
    sesi.semester = "Genap"
    sesi.tahun_akademik = "2025-2026"
    sesi.status = status
    sesi.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return sesi


def _make_conflict_log(
    sesi_id: uuid.UUID,
    jenis: str = "LECTURER_DOUBLE",
    severity: str = "ERROR",
    is_resolved: bool = False,
) -> MagicMock:
    log = MagicMock(spec=ConflictLogModel)
    log.id = uuid.uuid4()
    log.sesi_id = sesi_id
    log.jenis = jenis
    log.severity = severity
    log.assignment_ids = [uuid.uuid4()]
    log.pesan = f"Konflik {jenis}"
    log.detail = {"info": "test"}
    log.checked_at = datetime(2025, 4, 1, tzinfo=timezone.utc)
    log.is_resolved = is_resolved
    return log


def _token(user: MagicMock) -> str:
    return create_token({"sub": str(user.id), "role": user.role})


def _auth_header(user: MagicMock) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


# ---------------------------------------------------------------------------
# T4.2.1 — POST /sesi/{id}/check-conflicts
# ---------------------------------------------------------------------------

class TestCheckConflicts:

    def test_check_conflicts_returns_summary(self):
        """Happy path: engine berjalan, hasil disimpan, ringkasan dikembalikan."""
        user = _make_user("admin")
        sesi = _make_sesi()

        from app.services.conflict_engine import ConflictResult, ConflictJenis, ConflictSeverity

        fake_result = ConflictResult(
            jenis=ConflictJenis.LECTURER_DOUBLE,
            severity=ConflictSeverity.ERROR,
            assignment_ids=[uuid.uuid4()],
            pesan="Dosen double booking",
            detail={"dosen_id": str(uuid.uuid4())},
        )

        saved_log = _make_conflict_log(sesi.id, jenis="LECTURER_DOUBLE", severity="ERROR")

        def _db_override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: (
                user if model.__name__ == "User" else sesi
            )
            # Mock delete query chain
            db.query.return_value.filter.return_value.delete.return_value = 0
            db.flush = MagicMock()
            db.add = MagicMock()
            db.commit = MagicMock()
            db.refresh = MagicMock()
            yield db

        app.dependency_overrides[get_db] = _db_override

        with patch(
            "app.routers.conflict.ConflictEngine"
        ) as MockEngine:
            mock_engine_instance = MagicMock()
            mock_engine_instance.run.return_value = [fake_result]
            MockEngine.return_value = mock_engine_instance

            # Patch ConflictLog constructor to return our saved_log mock
            with patch("app.routers.conflict.ConflictLog", return_value=saved_log):
                client = TestClient(app)
                resp = client.post(
                    f"/sesi/{sesi.id}/check-conflicts",
                    headers=_auth_header(user),
                )

        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["sesi_id"] == str(sesi.id)
        assert data["total_error"] == 1
        assert data["total_warning"] == 0
        assert data["total"] == 1

    def test_check_conflicts_sesi_not_found_returns_404(self):
        """Sesi tidak ditemukan → 404."""
        user = _make_user("admin")

        def _db_override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: (
                user if model.__name__ == "User" else None
            )
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.post(
            f"/sesi/{uuid.uuid4()}/check-conflicts",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 404

    def test_check_conflicts_forbidden_for_dosen(self):
        """Role dosen tidak boleh menjalankan check-conflicts → 403."""
        user = _make_user("dosen")

        def _db_override():
            db = MagicMock()
            db.get.return_value = user
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.post(
            f"/sesi/{uuid.uuid4()}/check-conflicts",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 403

    def test_check_conflicts_no_conflicts_returns_zero_counts(self):
        """Engine tidak menemukan konflik → total_error=0, total_warning=0."""
        user = _make_user("sekretaris_jurusan")
        sesi = _make_sesi()

        def _db_override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: (
                user if model.__name__ == "User" else sesi
            )
            db.query.return_value.filter.return_value.delete.return_value = 0
            db.flush = MagicMock()
            db.add = MagicMock()
            db.commit = MagicMock()
            db.refresh = MagicMock()
            yield db

        app.dependency_overrides[get_db] = _db_override

        with patch("app.routers.conflict.ConflictEngine") as MockEngine:
            mock_engine_instance = MagicMock()
            mock_engine_instance.run.return_value = []
            MockEngine.return_value = mock_engine_instance

            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/check-conflicts",
                headers=_auth_header(user),
            )

        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_error"] == 0
        assert data["total_warning"] == 0
        assert data["total"] == 0
        assert data["conflicts"] == []

    def test_check_conflicts_unauthenticated_returns_401(self):
        """Tanpa token → 401."""
        client = TestClient(app)
        resp = client.post(f"/sesi/{uuid.uuid4()}/check-conflicts")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# T4.2.2 — GET /sesi/{id}/conflicts
# ---------------------------------------------------------------------------

class TestListConflicts:

    def test_list_conflicts_returns_all(self):
        """Happy path: kembalikan semua konflik untuk sesi."""
        user = _make_user("admin")
        sesi = _make_sesi()
        log1 = _make_conflict_log(sesi.id, jenis="LECTURER_DOUBLE", severity="ERROR")
        log2 = _make_conflict_log(sesi.id, jenis="STUDENT_CONFLICT", severity="WARNING")

        def _db_override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: (
                user if model.__name__ == "User" else sesi
            )
            mock_q = MagicMock()
            mock_q.filter.return_value = mock_q
            mock_q.order_by.return_value = mock_q
            mock_q.all.return_value = [log1, log2]
            db.query.return_value = mock_q
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/conflicts",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_conflicts_filter_by_severity(self):
        """Filter severity=ERROR hanya mengembalikan ERROR."""
        user = _make_user("admin")
        sesi = _make_sesi()
        log_error = _make_conflict_log(sesi.id, severity="ERROR")

        def _db_override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: (
                user if model.__name__ == "User" else sesi
            )
            mock_q = MagicMock()
            mock_q.filter.return_value = mock_q
            mock_q.order_by.return_value = mock_q
            mock_q.all.return_value = [log_error]
            db.query.return_value = mock_q
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/conflicts?severity=ERROR",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["severity"] == "ERROR"

    def test_list_conflicts_invalid_severity_returns_400(self):
        """severity tidak valid → 400."""
        user = _make_user("admin")
        sesi = _make_sesi()

        def _db_override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: (
                user if model.__name__ == "User" else sesi
            )
            mock_q = MagicMock()
            mock_q.filter.return_value = mock_q
            mock_q.order_by.return_value = mock_q
            mock_q.all.return_value = []
            db.query.return_value = mock_q
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/conflicts?severity=INVALID",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 400

    def test_list_conflicts_sesi_not_found_returns_404(self):
        """Sesi tidak ditemukan → 404."""
        user = _make_user("admin")

        def _db_override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: (
                user if model.__name__ == "User" else None
            )
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.get(
            f"/sesi/{uuid.uuid4()}/conflicts",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 404

    def test_list_conflicts_ketua_jurusan_can_access(self):
        """ketua_jurusan dapat mengakses daftar konflik."""
        user = _make_user("ketua_jurusan")
        sesi = _make_sesi()

        def _db_override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: (
                user if model.__name__ == "User" else sesi
            )
            mock_q = MagicMock()
            mock_q.filter.return_value = mock_q
            mock_q.order_by.return_value = mock_q
            mock_q.all.return_value = []
            db.query.return_value = mock_q
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/conflicts",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200

    def test_list_conflicts_dosen_forbidden(self):
        """Role dosen tidak boleh mengakses daftar konflik → 403."""
        user = _make_user("dosen")

        def _db_override():
            db = MagicMock()
            db.get.return_value = user
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.get(
            f"/sesi/{uuid.uuid4()}/conflicts",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# T4.2.3 — PATCH /sesi/{id}/conflicts/{cid}/resolve
# ---------------------------------------------------------------------------

class TestResolveConflict:

    def test_resolve_conflict_toggles_to_resolved(self):
        """Konflik yang belum resolved → ditandai resolved."""
        user = _make_user("admin")
        sesi = _make_sesi()
        log = _make_conflict_log(sesi.id, is_resolved=False)

        def _db_override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: (
                user if model.__name__ == "User"
                else sesi if model.__name__ == "SesiJadwal"
                else log
            )
            db.commit = MagicMock()
            db.refresh = MagicMock()
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.patch(
            f"/sesi/{sesi.id}/conflicts/{log.id}/resolve",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(log.id)
        assert data["is_resolved"] is True
        assert "resolved" in data["pesan"]

    def test_resolve_conflict_toggles_back_to_unresolved(self):
        """Konflik yang sudah resolved → ditandai unresolved (toggle)."""
        user = _make_user("admin")
        sesi = _make_sesi()
        log = _make_conflict_log(sesi.id, is_resolved=True)

        def _db_override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: (
                user if model.__name__ == "User"
                else sesi if model.__name__ == "SesiJadwal"
                else log
            )
            db.commit = MagicMock()
            db.refresh = MagicMock()
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.patch(
            f"/sesi/{sesi.id}/conflicts/{log.id}/resolve",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_resolved"] is False
        assert "unresolved" in data["pesan"]

    def test_resolve_conflict_not_found_returns_404(self):
        """ConflictLog tidak ditemukan → 404."""
        user = _make_user("admin")
        sesi = _make_sesi()

        def _db_override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: (
                user if model.__name__ == "User"
                else sesi if model.__name__ == "SesiJadwal"
                else None
            )
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.patch(
            f"/sesi/{sesi.id}/conflicts/{uuid.uuid4()}/resolve",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 404

    def test_resolve_conflict_wrong_sesi_returns_404(self):
        """ConflictLog ada tapi milik sesi lain → 404."""
        user = _make_user("admin")
        sesi = _make_sesi()
        other_sesi_id = uuid.uuid4()
        log = _make_conflict_log(other_sesi_id)  # milik sesi lain

        def _db_override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: (
                user if model.__name__ == "User"
                else sesi if model.__name__ == "SesiJadwal"
                else log
            )
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.patch(
            f"/sesi/{sesi.id}/conflicts/{log.id}/resolve",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 404

    def test_resolve_conflict_forbidden_for_koordinator_prodi(self):
        """koordinator_prodi tidak boleh resolve konflik → 403."""
        user = _make_user("koordinator_prodi")

        def _db_override():
            db = MagicMock()
            db.get.return_value = user
            yield db

        app.dependency_overrides[get_db] = _db_override

        client = TestClient(app)
        resp = client.patch(
            f"/sesi/{uuid.uuid4()}/conflicts/{uuid.uuid4()}/resolve",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 403

    def test_resolve_conflict_unauthenticated_returns_401(self):
        """Tanpa token → 401."""
        client = TestClient(app)
        resp = client.patch(
            f"/sesi/{uuid.uuid4()}/conflicts/{uuid.uuid4()}/resolve"
        )
        assert resp.status_code == 401
