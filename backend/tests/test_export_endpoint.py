"""
backend/tests/test_export_endpoint.py
Unit tests for GET /sesi/{sesi_id}/export endpoint.

Covers:
  GET /sesi/{id}/export — generate Excel file dan stream sebagai download
"""

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
from app.models.sesi_jadwal import SesiJadwal
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


def _token(user: MagicMock) -> str:
    return create_token({"sub": str(user.id), "role": user.role})


def _auth_header(user: MagicMock) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


def _make_sesi(sesi_id: uuid.UUID, nama: str = "Genap 2024/2025") -> MagicMock:
    sesi = MagicMock(spec=SesiJadwal)
    sesi.id = sesi_id
    sesi.nama = nama
    return sesi


def _db_with_sesi(user: MagicMock, sesi: MagicMock):
    """get_db override that returns the given sesi on db.get(SesiJadwal, ...)."""
    def _override():
        db = MagicMock()
        db.get.side_effect = lambda model, pk: (
            user if getattr(model, "__name__", None) == "User"
            else sesi if model is SesiJadwal
            else None
        )
        yield db
    return _override


def _db_sesi_not_found(user: MagicMock):
    """get_db override where SesiJadwal is not found."""
    def _override():
        db = MagicMock()
        db.get.side_effect = lambda model, pk: (
            user if getattr(model, "__name__", None) == "User" else None
        )
        yield db
    return _override


# Minimal valid xlsx bytes
_XLSX_BYTES = b""
with patch("app.services.excel_exporter.ExcelExporter.export_jadwal"):
    import openpyxl as _openpyxl, io as _io
    _wb = _openpyxl.Workbook()
    _buf = _io.BytesIO()
    _wb.save(_buf)
    _XLSX_BYTES = _buf.getvalue()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestExportJadwalHappyPath:
    def test_returns_200_with_xlsx_content_type(self):
        """Valid sesi_id should return 200 with xlsx content-type."""
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        sesi = _make_sesi(sesi_id)

        app.dependency_overrides[get_db] = _db_with_sesi(user, sesi)
        try:
            with patch(
                "app.services.excel_exporter.ExcelExporter.export_jadwal",
                return_value=_XLSX_BYTES,
            ):
                client = TestClient(app)
                response = client.get(
                    f"/sesi/{sesi_id}/export",
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200
        assert "spreadsheetml.sheet" in response.headers["content-type"]

    def test_content_disposition_is_attachment(self):
        """Response must have Content-Disposition: attachment with .xlsx filename."""
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        sesi = _make_sesi(sesi_id, nama="Genap 2024/2025")

        app.dependency_overrides[get_db] = _db_with_sesi(user, sesi)
        try:
            with patch(
                "app.services.excel_exporter.ExcelExporter.export_jadwal",
                return_value=_XLSX_BYTES,
            ):
                client = TestClient(app)
                response = client.get(
                    f"/sesi/{sesi_id}/export",
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert ".xlsx" in disposition

    def test_filename_contains_sesi_nama(self):
        """Filename in Content-Disposition must contain sanitized sesi nama."""
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        sesi = _make_sesi(sesi_id, nama="Genap 2024/2025")

        app.dependency_overrides[get_db] = _db_with_sesi(user, sesi)
        try:
            with patch(
                "app.services.excel_exporter.ExcelExporter.export_jadwal",
                return_value=_XLSX_BYTES,
            ):
                client = TestClient(app)
                response = client.get(
                    f"/sesi/{sesi_id}/export",
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        disposition = response.headers.get("content-disposition", "")
        # Spaces replaced with _, / replaced with -
        assert "Genap_2024-2025" in disposition

    def test_filename_starts_with_jadwal(self):
        """Filename must start with 'jadwal_'."""
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        sesi = _make_sesi(sesi_id)

        app.dependency_overrides[get_db] = _db_with_sesi(user, sesi)
        try:
            with patch(
                "app.services.excel_exporter.ExcelExporter.export_jadwal",
                return_value=_XLSX_BYTES,
            ):
                client = TestClient(app)
                response = client.get(
                    f"/sesi/{sesi_id}/export",
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        disposition = response.headers.get("content-disposition", "")
        assert "jadwal_" in disposition

    def test_response_body_is_non_empty_bytes(self):
        """Response body must be non-empty bytes (the xlsx content)."""
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        sesi = _make_sesi(sesi_id)

        app.dependency_overrides[get_db] = _db_with_sesi(user, sesi)
        try:
            with patch(
                "app.services.excel_exporter.ExcelExporter.export_jadwal",
                return_value=_XLSX_BYTES,
            ):
                client = TestClient(app)
                response = client.get(
                    f"/sesi/{sesi_id}/export",
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert len(response.content) > 0


# ---------------------------------------------------------------------------
# 404 — sesi not found
# ---------------------------------------------------------------------------

class TestExportJadwalNotFound:
    def test_sesi_not_found_returns_404(self):
        """Unknown sesi_id should return 404."""
        user = _make_user("admin")
        sesi_id = uuid.uuid4()

        app.dependency_overrides[get_db] = _db_sesi_not_found(user)
        try:
            client = TestClient(app)
            response = client.get(
                f"/sesi/{sesi_id}/export",
                headers=_auth_header(user),
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 404
        assert str(sesi_id) in response.json()["detail"]

    def test_invalid_uuid_returns_422(self):
        """Non-UUID path param should return 422."""
        user = _make_user("admin")
        app.dependency_overrides[get_db] = _db_sesi_not_found(user)
        try:
            client = TestClient(app)
            response = client.get(
                "/sesi/not-a-uuid/export",
                headers=_auth_header(user),
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------

class TestExportJadwalRBAC:
    def test_unauthenticated_returns_401(self):
        """Request without token should return 401."""
        sesi_id = uuid.uuid4()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(f"/sesi/{sesi_id}/export")
        assert response.status_code == 401

    def test_dosen_role_returns_403(self):
        """dosen role must be forbidden (403)."""
        user = _make_user("dosen")
        sesi_id = uuid.uuid4()

        app.dependency_overrides[get_db] = _db_sesi_not_found(user)
        try:
            client = TestClient(app)
            response = client.get(
                f"/sesi/{sesi_id}/export",
                headers=_auth_header(user),
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 403

    @pytest.mark.parametrize("role", [
        "admin",
        "sekretaris_jurusan",
        "tendik_jurusan",
        "koordinator_prodi",
        "tendik_prodi",
        "ketua_jurusan",
    ])
    def test_allowed_roles_can_export(self, role):
        """All roles except dosen should be allowed to export."""
        user = _make_user(role)
        sesi_id = uuid.uuid4()
        sesi = _make_sesi(sesi_id)

        app.dependency_overrides[get_db] = _db_with_sesi(user, sesi)
        try:
            with patch(
                "app.services.excel_exporter.ExcelExporter.export_jadwal",
                return_value=_XLSX_BYTES,
            ):
                client = TestClient(app)
                response = client.get(
                    f"/sesi/{sesi_id}/export",
                    headers=_auth_header(user),
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200
