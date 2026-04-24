"""
backend/tests/test_import_master.py
Unit tests for POST /import/master endpoint.

Covers:
  POST /import/master — upload Excel file, import master data, return ImportResult JSON
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
    ws.title = "Prodi"
    ws.append(["id_prodi", "strata", "nama_prodi", "kategori"])
    ws.append([1, "S-1", "Matematika", "saintek"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _db_override(user: MagicMock):
    """Build a get_db override that returns the given user for auth lookups."""
    def _override():
        db = MagicMock()
        db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
        yield db
    return _override


# ---------------------------------------------------------------------------
# Tests — happy path
# ---------------------------------------------------------------------------

class TestImportMasterHappyPath:
    def test_returns_200_with_import_result_json(self):
        """Valid xlsx upload by admin should return 200 with ImportResult fields."""
        user = _make_user("admin")
        xlsx_bytes = _make_xlsx_bytes()

        mock_result = ImportResult(
            total=5, inserted=3, updated=1, skipped=1,
            warnings=[
                ImportWarning(row=3, sheet="Prodi", value="bad_row", reason="strata kosong")
            ],
        )

        app.dependency_overrides[get_db] = _db_override(user)
        try:
            with patch("app.services.excel_importer.ExcelImporter.import_master_db",
                       return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    "/import/master",
                    files={"file": ("db.xlsx", xlsx_bytes,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["inserted"] == 3
        assert data["updated"] == 1
        assert data["skipped"] == 1
        assert len(data["warnings"]) == 1
        w = data["warnings"][0]
        assert w["row"] == 3
        assert w["sheet"] == "Prodi"
        assert w["value"] == "bad_row"
        assert w["reason"] == "strata kosong"

    def test_returns_all_import_result_keys(self):
        """Response JSON must contain all required ImportResult keys."""
        user = _make_user("admin")
        xlsx_bytes = _make_xlsx_bytes()

        mock_result = ImportResult(total=0, inserted=0, updated=0, skipped=0)

        app.dependency_overrides[get_db] = _db_override(user)
        try:
            with patch("app.services.excel_importer.ExcelImporter.import_master_db",
                       return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    "/import/master",
                    files={"file": ("db.xlsx", xlsx_bytes,
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

    def test_empty_warnings_list_when_no_issues(self):
        """When import has no warnings, warnings list should be empty."""
        user = _make_user("admin")
        xlsx_bytes = _make_xlsx_bytes()

        mock_result = ImportResult(total=10, inserted=10, updated=0, skipped=0)

        app.dependency_overrides[get_db] = _db_override(user)
        try:
            with patch("app.services.excel_importer.ExcelImporter.import_master_db",
                       return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    "/import/master",
                    files={"file": ("db.xlsx", xlsx_bytes,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200
        assert response.json()["warnings"] == []


# ---------------------------------------------------------------------------
# Tests — RBAC / access control
# ---------------------------------------------------------------------------

class TestImportMasterRBAC:
    def test_unauthenticated_returns_401(self):
        """Request without token should be rejected with 401."""
        xlsx_bytes = _make_xlsx_bytes()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/import/master",
            files={"file": ("db.xlsx", xlsx_bytes,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert response.status_code == 401

    def test_dosen_role_returns_403(self):
        """Dosen role should be forbidden (403) from importing master data."""
        user = _make_user("dosen")
        xlsx_bytes = _make_xlsx_bytes()

        app.dependency_overrides[get_db] = _db_override(user)
        try:
            client = TestClient(app)
            response = client.post(
                "/import/master",
                files={"file": ("db.xlsx", xlsx_bytes,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers=_auth_header(user),
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 403

    def test_sekretaris_jurusan_allowed(self):
        """sekretaris_jurusan role should be allowed to import master data."""
        user = _make_user("sekretaris_jurusan")
        xlsx_bytes = _make_xlsx_bytes()

        mock_result = ImportResult(total=2, inserted=2, updated=0, skipped=0)

        app.dependency_overrides[get_db] = _db_override(user)
        try:
            with patch("app.services.excel_importer.ExcelImporter.import_master_db",
                       return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    "/import/master",
                    files={"file": ("db.xlsx", xlsx_bytes,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200

    def test_tendik_jurusan_allowed(self):
        """tendik_jurusan role should be allowed to import master data."""
        user = _make_user("tendik_jurusan")
        xlsx_bytes = _make_xlsx_bytes()

        mock_result = ImportResult(total=1, inserted=1, updated=0, skipped=0)

        app.dependency_overrides[get_db] = _db_override(user)
        try:
            with patch("app.services.excel_importer.ExcelImporter.import_master_db",
                       return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    "/import/master",
                    files={"file": ("db.xlsx", xlsx_bytes,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200

    def test_koordinator_prodi_returns_403(self):
        """koordinator_prodi is not in EDITOR_ROLES_JURUSAN, should get 403."""
        user = _make_user("koordinator_prodi")
        xlsx_bytes = _make_xlsx_bytes()

        app.dependency_overrides[get_db] = _db_override(user)
        try:
            client = TestClient(app)
            response = client.post(
                "/import/master",
                files={"file": ("db.xlsx", xlsx_bytes,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers=_auth_header(user),
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Tests — warning value serialization
# ---------------------------------------------------------------------------

class TestImportMasterWarningSerialization:
    def test_warning_value_none_serialized_as_null(self):
        """ImportWarning with value=None should serialize as null in JSON."""
        user = _make_user("admin")
        xlsx_bytes = _make_xlsx_bytes()

        mock_result = ImportResult(
            total=1, inserted=0, updated=0, skipped=1,
            warnings=[ImportWarning(row=2, sheet="Prodi", value=None, reason="baris kosong")],
        )

        app.dependency_overrides[get_db] = _db_override(user)
        try:
            with patch("app.services.excel_importer.ExcelImporter.import_master_db",
                       return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    "/import/master",
                    files={"file": ("db.xlsx", xlsx_bytes,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200
        w = response.json()["warnings"][0]
        assert w["value"] is None

    def test_warning_value_tuple_serialized_as_string(self):
        """ImportWarning with tuple value should be serialized as string."""
        user = _make_user("admin")
        xlsx_bytes = _make_xlsx_bytes()

        mock_result = ImportResult(
            total=1, inserted=0, updated=0, skipped=1,
            warnings=[ImportWarning(row=5, sheet="Dosen", value=("ABD", "Dr. X", None),
                                    reason="kode dosen kosong")],
        )

        app.dependency_overrides[get_db] = _db_override(user)
        try:
            with patch("app.services.excel_importer.ExcelImporter.import_master_db",
                       return_value=mock_result):
                client = TestClient(app)
                response = client.post(
                    "/import/master",
                    files={"file": ("db.xlsx", xlsx_bytes,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200
        w = response.json()["warnings"][0]
        assert isinstance(w["value"], str)
