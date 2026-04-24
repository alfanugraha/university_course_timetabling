"""
backend/tests/test_sesi.py
Unit tests for SesiJadwal CRUD endpoints.

Covers:
  GET   /sesi              — list sesi (authenticated)
  POST  /sesi              — create sesi (EDITOR_ROLES_JURUSAN)
  PUT   /sesi/{id}         — update sesi + status transitions (EDITOR_ROLES_JURUSAN)
  PATCH /sesi/{id}/approve — approve / request_revision (ketua_jurusan)
  PATCH /sesi/{id}/publish — publish/arsip (ketua_jurusan)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
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


def _make_sesi(
    nama: str = "Genap 2025-2026",
    semester: str = "Genap",
    tahun_akademik: str = "2025-2026",
    status: str = "Draft",
) -> MagicMock:
    sesi = MagicMock(spec=SesiJadwalModel)
    sesi.id = uuid.uuid4()
    sesi.nama = nama
    sesi.semester = semester
    sesi.tahun_akademik = tahun_akademik
    sesi.status = status
    sesi.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return sesi


def _token(user: MagicMock) -> str:
    return create_token({"sub": str(user.id), "role": user.role})


def _auth_header(user: MagicMock) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


def _db_simple(user: MagicMock, query_result=None, get_result=None):
    """Simple DB override: query returns list, get returns get_result (or user for User model)."""
    def _override():
        mock_order = MagicMock()
        mock_order.all.return_value = query_result if query_result is not None else []

        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_order

        db = MagicMock()
        db.query.return_value = mock_query
        db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else get_result
        yield db

    return _override


# ---------------------------------------------------------------------------
# GET /sesi
# ---------------------------------------------------------------------------

class TestListSesi:
    def test_returns_list_for_authenticated_user(self):
        user = _make_user("dosen")
        s1 = _make_sesi("Genap 2025-2026")
        s2 = _make_sesi("Ganjil 2025-2026", semester="Ganjil")

        app.dependency_overrides[get_db] = _db_simple(user, query_result=[s1, s2])
        try:
            client = TestClient(app)
            resp = client.get("/sesi", headers=_auth_header(user))
            assert resp.status_code == 200
            assert len(resp.json()) == 2
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_returns_empty_list_when_no_sesi(self):
        user = _make_user("admin")
        app.dependency_overrides[get_db] = _db_simple(user, query_result=[])
        try:
            client = TestClient(app)
            resp = client.get("/sesi", headers=_auth_header(user))
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/sesi")
        assert resp.status_code in (401, 403)

    def test_response_contains_expected_fields(self):
        user = _make_user("ketua_jurusan")
        sesi = _make_sesi()
        app.dependency_overrides[get_db] = _db_simple(user, query_result=[sesi])
        try:
            client = TestClient(app)
            resp = client.get("/sesi", headers=_auth_header(user))
            assert resp.status_code == 200
            item = resp.json()[0]
            for field in ("id", "nama", "semester", "tahun_akademik", "status", "created_at"):
                assert field in item
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /sesi
# ---------------------------------------------------------------------------

_CREATE_PAYLOAD = {
    "nama": "Genap 2025-2026",
    "semester": "Genap",
    "tahun_akademik": "2025-2026",
}


class TestCreateSesi:
    def test_admin_can_create_sesi(self):
        user = _make_user("admin")
        new_sesi = _make_sesi()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: None
            # Simulate the created object having the right attributes after refresh
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", {
                "id": new_sesi.id,
                "nama": new_sesi.nama,
                "semester": new_sesi.semester,
                "tahun_akademik": new_sesi.tahun_akademik,
                "status": "Draft",
                "created_at": new_sesi.created_at,
                "_sa_instance_state": MagicMock(),
            })
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/sesi", json=_CREATE_PAYLOAD, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_sekretaris_jurusan_can_create_sesi(self):
        user = _make_user("sekretaris_jurusan")
        new_sesi = _make_sesi()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", {
                "id": new_sesi.id,
                "nama": new_sesi.nama,
                "semester": new_sesi.semester,
                "tahun_akademik": new_sesi.tahun_akademik,
                "status": "Draft",
                "created_at": new_sesi.created_at,
                "_sa_instance_state": MagicMock(),
            })
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/sesi", json=_CREATE_PAYLOAD, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_jurusan_can_create_sesi(self):
        user = _make_user("tendik_jurusan")
        new_sesi = _make_sesi()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", {
                "id": new_sesi.id,
                "nama": new_sesi.nama,
                "semester": new_sesi.semester,
                "tahun_akademik": new_sesi.tahun_akademik,
                "status": "Draft",
                "created_at": new_sesi.created_at,
                "_sa_instance_state": MagicMock(),
            })
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/sesi", json=_CREATE_PAYLOAD, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_gets_403(self):
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_simple(user)
            try:
                client = TestClient(app)
                resp = client.post("/sesi", json=_CREATE_PAYLOAD, headers=_auth_header(user))
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/sesi", json=_CREATE_PAYLOAD)
        assert resp.status_code in (401, 403)

    def test_duplicate_semester_tahun_returns_409(self):
        from sqlalchemy.exc import IntegrityError

        user = _make_user("admin")

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.commit.side_effect = IntegrityError("duplicate", {}, None)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/sesi", json=_CREATE_PAYLOAD, headers=_auth_header(user))
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# PUT /sesi/{id}
# ---------------------------------------------------------------------------

class TestUpdateSesi:
    def test_admin_can_update_nama(self):
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        existing = _make_sesi()
        existing.id = sesi_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi_id}",
                json={"nama": "Genap 2025-2026 (Revisi)"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_valid_status_transition_draft_to_aktif(self):
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        existing = _make_sesi(status="Draft")
        existing.id = sesi_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi_id}",
                json={"status": "Aktif"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert existing.status == "Aktif"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_valid_status_transition_aktif_to_arsip(self):
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        existing = _make_sesi(status="Aktif")
        existing.id = sesi_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi_id}",
                json={"status": "Arsip"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert existing.status == "Arsip"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_backward_transition_aktif_to_draft_returns_400(self):
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        existing = _make_sesi(status="Aktif")
        existing.id = sesi_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi_id}",
                json={"status": "Draft"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_backward_transition_arsip_to_aktif_returns_400(self):
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        existing = _make_sesi(status="Arsip")
        existing.id = sesi_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi_id}",
                json={"status": "Aktif"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_invalid_status_value_returns_422(self):
        user = _make_user("admin")
        sesi_id = uuid.uuid4()
        existing = _make_sesi()
        existing.id = sesi_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi_id}",
                json={"status": "InvalidStatus"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        user = _make_user("admin")
        sesi_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi_id}",
                json={"nama": "Updated"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_gets_403(self):
        sesi_id = uuid.uuid4()
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_simple(user)
            try:
                client = TestClient(app)
                resp = client.put(
                    f"/sesi/{sesi_id}",
                    json={"nama": "Updated"},
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# PATCH /sesi/{id}/approve
# ---------------------------------------------------------------------------

class TestApproveSesi:
    def test_ketua_jurusan_can_approve(self):
        user = _make_user("ketua_jurusan")
        sesi_id = uuid.uuid4()
        existing = _make_sesi(status="Draft")
        existing.id = sesi_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi_id}/approve",
                json={"action": "approve"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert existing.status == "Aktif"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_ketua_jurusan_can_request_revision(self):
        user = _make_user("ketua_jurusan")
        sesi_id = uuid.uuid4()
        existing = _make_sesi(status="Aktif")
        existing.id = sesi_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi_id}/approve",
                json={"action": "request_revision", "catatan": "Perlu perbaikan jadwal dosen X"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert existing.status == "Draft"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_ketua_gets_403(self):
        sesi_id = uuid.uuid4()
        for role in ("admin", "sekretaris_jurusan", "tendik_jurusan", "dosen"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_simple(user)
            try:
                client = TestClient(app)
                resp = client.patch(
                    f"/sesi/{sesi_id}/approve",
                    json={"action": "approve"},
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        user = _make_user("ketua_jurusan")
        sesi_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi_id}/approve",
                json={"action": "approve"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_invalid_action_returns_422(self):
        user = _make_user("ketua_jurusan")
        sesi_id = uuid.uuid4()
        existing = _make_sesi()
        existing.id = sesi_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi_id}/approve",
                json={"action": "invalid_action"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# PATCH /sesi/{id}/publish
# ---------------------------------------------------------------------------

class TestPublishSesi:
    def test_ketua_jurusan_can_publish_aktif_sesi(self):
        user = _make_user("ketua_jurusan")
        sesi_id = uuid.uuid4()
        existing = _make_sesi(status="Aktif")
        existing.id = sesi_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi_id}/publish",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert existing.status == "Arsip"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_publish_draft_sesi_returns_400(self):
        user = _make_user("ketua_jurusan")
        sesi_id = uuid.uuid4()
        existing = _make_sesi(status="Draft")
        existing.id = sesi_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi_id}/publish",
                headers=_auth_header(user),
            )
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_publish_already_arsip_returns_400(self):
        user = _make_user("ketua_jurusan")
        sesi_id = uuid.uuid4()
        existing = _make_sesi(status="Arsip")
        existing.id = sesi_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi_id}/publish",
                headers=_auth_header(user),
            )
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_ketua_gets_403(self):
        sesi_id = uuid.uuid4()
        for role in ("admin", "sekretaris_jurusan", "tendik_jurusan", "dosen"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_simple(user)
            try:
                client = TestClient(app)
                resp = client.patch(
                    f"/sesi/{sesi_id}/publish",
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        user = _make_user("ketua_jurusan")
        sesi_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi_id}/publish",
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# GET /sesi/{id}/preferences-summary
# ---------------------------------------------------------------------------

class TestPreferencesSummary:
    """Tests for GET /sesi/{id}/preferences-summary."""

    def _make_db_with_preferences(self, user, sesi, query_rows):
        """Build a DB mock that handles both get() and query() calls.

        The endpoint chain is:
          db.query(...).join(...).filter(...).group_by(...).order_by(...).all()
        We use a single MagicMock that returns itself for every chained call
        except .all(), which returns the desired rows.
        """
        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else sesi

            # A chainable mock: every method returns itself, .all() returns rows
            chain = MagicMock()
            chain.join.return_value = chain
            chain.filter.return_value = chain
            chain.group_by.return_value = chain
            chain.order_by.return_value = chain
            chain.all.return_value = query_rows

            db.query.return_value = chain
            yield db

        return _override

    def test_editor_can_access(self):
        for role in ("admin", "sekretaris_jurusan", "tendik_jurusan"):
            user = _make_user(role)
            sesi = _make_sesi()
            sesi_id = sesi.id

            app.dependency_overrides[get_db] = self._make_db_with_preferences(user, sesi, [])
            try:
                client = TestClient(app)
                resp = client.get(
                    f"/sesi/{sesi_id}/preferences-summary",
                    headers=_auth_header(user),
                )
                assert resp.status_code == 200, f"Expected 200 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_ketua_jurusan_can_access(self):
        user = _make_user("ketua_jurusan")
        sesi = _make_sesi()
        sesi_id = sesi.id

        app.dependency_overrides[get_db] = self._make_db_with_preferences(user, sesi, [])
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi_id}/preferences-summary",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthorized_role_gets_403(self):
        for role in ("dosen", "koordinator_prodi", "tendik_prodi"):
            user = _make_user(role)
            sesi = _make_sesi()
            sesi_id = sesi.id

            app.dependency_overrides[get_db] = self._make_db_with_preferences(user, sesi, [])
            try:
                client = TestClient(app)
                resp = client.get(
                    f"/sesi/{sesi_id}/preferences-summary",
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_sesi_not_found_returns_404(self):
        user = _make_user("admin")
        sesi_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi_id}/preferences-summary",
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_empty_preferences_returns_zeros(self):
        user = _make_user("admin")
        sesi = _make_sesi()
        sesi_id = sesi.id

        app.dependency_overrides[get_db] = self._make_db_with_preferences(user, sesi, [])
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi_id}/preferences-summary",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["sesi_id"] == str(sesi_id)
            assert data["total_preferensi"] == 0
            assert data["total_dilanggar"] == 0
            assert data["breakdown"] == []
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_response_aggregates_correctly(self):
        user = _make_user("admin")
        sesi = _make_sesi()
        sesi_id = sesi.id

        dosen1_id = uuid.uuid4()
        dosen2_id = uuid.uuid4()

        # Simulate two rows returned from the aggregation query
        row1 = MagicMock()
        row1.dosen_id = dosen1_id
        row1.kode = "D001"
        row1.nama = "Dosen Alpha"
        row1.total_preferensi = 3
        row1.total_dilanggar = 1

        row2 = MagicMock()
        row2.dosen_id = dosen2_id
        row2.kode = "D002"
        row2.nama = "Dosen Beta"
        row2.total_preferensi = 5
        row2.total_dilanggar = 2

        app.dependency_overrides[get_db] = self._make_db_with_preferences(
            user, sesi, [row1, row2]
        )
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi_id}/preferences-summary",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_preferensi"] == 8
            assert data["total_dilanggar"] == 3
            assert len(data["breakdown"]) == 2

            item1 = data["breakdown"][0]
            assert item1["dosen_id"] == str(dosen1_id)
            assert item1["kode"] == "D001"
            assert item1["nama"] == "Dosen Alpha"
            assert item1["total_preferensi"] == 3
            assert item1["total_dilanggar"] == 1
        finally:
            app.dependency_overrides.pop(get_db, None)
