"""
backend/tests/test_import_jadwal.py
Unit tests for POST /import/jadwal endpoint.

Covers:
  POST /import/jadwal — multipart upload + sesi_id query param;
  jalankan importer jadwal; kembalikan ImportResult JSON
"""

import io
import uuid
from unittest.mock import MagicMock, patch

import openpyxl
import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
from app.models.sesi_jadwal import SesiJadwal
from app.models.user import User as UserModel
from app.services.excel_importer import ImportResult, ImportWarning


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


def _token(user: MagicMock) -> str:
    return create_token({"sub": str(user.id), "role": user.role})


def _auth_header(user: MagicMock) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


def _make_xlsx_bytes() -> bytes:
    """Build a minimal valid xlsx file in memory."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Jadwal"
    ws.append(["Hari", "", "", "Ruang", "Waktu", "", "", "Kode MK", "Kode MK 2025"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_sesi(sesi_id: uuid.UUID) -> MagicMock:
    sesi = MagicMock(spec=SesiJadwal)
    sesi.id = sesi_id
    return sesi


def _db_override_with_sesi(user: MagicMock, sesi: MagicMock):
    """get_db override that returns user for auth and sesi for SesiJadwal query."""
    def _override():
        db = MagicMock()

        def _query_side_effect(model):
            q = MagicMock()
            if model is SesiJadwal:
                filter_mock = MagicMock()
                filter_mock.first.return_value = sesi
                q.filter.return_value = filter_mock
            else:
                filter_mock = MagicMock()
                filter_mock.first.return_value = None
                q.filter.return_value = filter_mock
            return q

        db.query.side_effect = _query_side_effect
        db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
        yield db

    return _override


def _db_override_sesi_not_found(user: MagicMock):
    """get_db override where SesiJadwal is not found."""
    def _override():
        db = MagicMock()

        def _query_side_effect(model):
            q = MagicMock()
            filter_mock = MagicMock()
            filter_mock.first.return_value = None
            q.filter.return_value = filter_mock
            return q

        db.query.side_effect = _query_side_effect
        db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
        yield db

    return _override


# ---------------------------------------------------------------------------
# Tests — happy path
# ---------------------------------------------------------------------------

class TestImportJadwalHappyPath:
    def test_returns_200_with_import_result_json(self):
        """Valid xlsx upload with valid sesi_id should return 200 with ImportResult fields."""
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        sesi = _make_sesi(sesi_id)
        xlsx_bytes = _make_xlsx_bytes()

        mock_result = ImportResult(
            total=10, inserted=8, updated=1, skipped=1,
            warnings=[
                ImportWarning(row=5, sheet="Jadwal", value="UNKNOWN_MK", reason="kode_mk tidak ditemukan")
            ],
        )

        app.dependency_overrides[get_db] = _db_override_with_sesi(user, sesi)
        try:
            with patch("app.services.excel_importer.ExcelImporter.import_jadwal",
                       return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    f"/import/jadwal?sesi_id={sesi_id}",
                    files={"file": ("jadwal.xlsx", xlsx_bytes,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["inserted"] == 8
        assert data["updated"] == 1
        assert data["skipped"] == 1
        assert len(data["warnings"]) == 1
        w = data["warnings"][0]
        assert w["row"] == 5
        assert w["sheet"] == "Jadwal"
        assert w["value"] == "UNKNOWN_MK"
        assert w["reason"] == "kode_mk tidak ditemukan"

    def test_returns_all_import_result_keys(self):
        """Response JSON must contain all required ImportResult keys."""
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        sesi = _make_sesi(sesi_id)
        xlsx_bytes = _make_xlsx_bytes()

        mock_result = ImportResult(total=0, inserted=0, updated=0, skipped=0)

        app.dependency_overrides[get_db] = _db_override_with_sesi(user, sesi)
        try:
            with patch("app.services.excel_importer.ExcelImporter.import_jadwal",
                       return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    f"/import/jadwal?sesi_id={sesi_id}",
                    files={"file": ("jadwal.xlsx", xlsx_bytes,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200
        data = response.json()
        for key in ("total", "inserted", "updated", "skipped", "warnings"):
            assert key in data, f"Missing key: {key}"
        assert isinstance(data["warnings"], list)

    def test_empty_warnings_when_no_issues(self):
        """When import has no warnings, warnings list should be empty."""
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        sesi = _make_sesi(sesi_id)
        xlsx_bytes = _make_xlsx_bytes()

        mock_result = ImportResult(total=5, inserted=5, updated=0, skipped=0)

        app.dependency_overrides[get_db] = _db_override_with_sesi(user, sesi)
        try:
            with patch("app.services.excel_importer.ExcelImporter.import_jadwal",
                       return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    f"/import/jadwal?sesi_id={sesi_id}",
                    files={"file": ("jadwal.xlsx", xlsx_bytes,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200
        assert response.json()["warnings"] == []


# ---------------------------------------------------------------------------
# Tests — sesi_id validation
# ---------------------------------------------------------------------------

class TestImportJadwalSesiValidation:
    def test_missing_sesi_id_returns_422(self):
        """Request without sesi_id query param should return 422."""
        user = _make_user("admin")
        xlsx_bytes = _make_xlsx_bytes()

        app.dependency_overrides[get_db] = _db_override_sesi_not_found(user)
        try:
            client = TestClient(app)
            response = client.post(
                "/import/jadwal",
                files={"file": ("jadwal.xlsx", xlsx_bytes,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers=_auth_header(user),
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 422

    def test_invalid_uuid_sesi_id_returns_422(self):
        """Non-UUID sesi_id should return 422 (FastAPI validation)."""
        user = _make_user("admin")
        xlsx_bytes = _make_xlsx_bytes()

        app.dependency_overrides[get_db] = _db_override_sesi_not_found(user)
        try:
            client = TestClient(app)
            response = client.post(
                "/import/jadwal?sesi_id=not-a-uuid",
                files={"file": ("jadwal.xlsx", xlsx_bytes,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers=_auth_header(user),
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 422

    def test_sesi_not_found_returns_404(self):
        """Valid UUID sesi_id that doesn't exist in DB should return 404."""
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        xlsx_bytes = _make_xlsx_bytes()

        app.dependency_overrides[get_db] = _db_override_sesi_not_found(user)
        try:
            client = TestClient(app)
            response = client.post(
                f"/import/jadwal?sesi_id={sesi_id}",
                files={"file": ("jadwal.xlsx", xlsx_bytes,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers=_auth_header(user),
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 404
        assert str(sesi_id) in response.json()["detail"]


# ---------------------------------------------------------------------------
# Tests — RBAC / access control
# ---------------------------------------------------------------------------

class TestImportJadwalRBAC:
    def test_unauthenticated_returns_401(self):
        """Request without token should be rejected with 401."""
        sesi_id = uuid.uuid4()
        xlsx_bytes = _make_xlsx_bytes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            f"/import/jadwal?sesi_id={sesi_id}",
            files={"file": ("jadwal.xlsx", xlsx_bytes,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert response.status_code == 401

    def test_dosen_role_returns_403(self):
        """Dosen role should be forbidden (403) from importing jadwal."""
        user = _make_user("dosen")
        sesi_id = uuid.uuid4()
        xlsx_bytes = _make_xlsx_bytes()

        app.dependency_overrides[get_db] = _db_override_sesi_not_found(user)
        try:
            client = TestClient(app)
            response = client.post(
                f"/import/jadwal?sesi_id={sesi_id}",
                files={"file": ("jadwal.xlsx", xlsx_bytes,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers=_auth_header(user),
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 403

    def test_koordinator_prodi_returns_403(self):
        """koordinator_prodi is not in EDITOR_ROLES_JURUSAN, should get 403."""
        user = _make_user("koordinator_prodi")
        sesi_id = uuid.uuid4()
        xlsx_bytes = _make_xlsx_bytes()

        app.dependency_overrides[get_db] = _db_override_sesi_not_found(user)
        try:
            client = TestClient(app)
            response = client.post(
                f"/import/jadwal?sesi_id={sesi_id}",
                files={"file": ("jadwal.xlsx", xlsx_bytes,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers=_auth_header(user),
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 403

    def test_sekretaris_jurusan_allowed(self):
        """sekretaris_jurusan role should be allowed to import jadwal."""
        user = _make_user("sekretaris_jurusan")
        sesi_id = uuid.uuid4()
        sesi = _make_sesi(sesi_id)
        xlsx_bytes = _make_xlsx_bytes()

        mock_result = ImportResult(total=2, inserted=2, updated=0, skipped=0)

        app.dependency_overrides[get_db] = _db_override_with_sesi(user, sesi)
        try:
            with patch("app.services.excel_importer.ExcelImporter.import_jadwal",
                       return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    f"/import/jadwal?sesi_id={sesi_id}",
                    files={"file": ("jadwal.xlsx", xlsx_bytes,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200

    def test_tendik_jurusan_allowed(self):
        """tendik_jurusan role should be allowed to import jadwal."""
        user = _make_user("tendik_jurusan")
        sesi_id = uuid.uuid4()
        sesi = _make_sesi(sesi_id)
        xlsx_bytes = _make_xlsx_bytes()

        mock_result = ImportResult(total=1, inserted=1, updated=0, skipped=0)

        app.dependency_overrides[get_db] = _db_override_with_sesi(user, sesi)
        try:
            with patch("app.services.excel_importer.ExcelImporter.import_jadwal",
                       return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    f"/import/jadwal?sesi_id={sesi_id}",
                    files={"file": ("jadwal.xlsx", xlsx_bytes,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200
