"""
backend/tests/test_ruang.py
Unit tests for Ruang CRUD endpoints.

Covers:
  GET  /ruang        — list ruang (authenticated)
  POST /ruang        — create ruang (EDITOR_ROLES_JURUSAN)
  PUT  /ruang/{id}   — update ruang (EDITOR_ROLES_JURUSAN)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
from app.models.ruang import Ruang as RuangModel
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


def _make_ruang(
    nama: str = "R.101",
    kapasitas: int = 45,
    lantai: int = 1,
    gedung: str = "Gedung A",
    jenis: str = "Kelas",
    is_active: bool = True,
) -> MagicMock:
    ruang = MagicMock(spec=RuangModel)
    ruang.id = uuid.uuid4()
    ruang.nama = nama
    ruang.kapasitas = kapasitas
    ruang.lantai = lantai
    ruang.gedung = gedung
    ruang.jenis = jenis
    ruang.is_active = is_active
    ruang.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return ruang


def _db_override(user: MagicMock, query_result=None, get_result=None):
    def _override():
        mock_order = MagicMock()
        mock_order.all.return_value = query_result if query_result is not None else []

        mock_filter = MagicMock()
        mock_filter.first.return_value = get_result
        mock_filter.order_by.return_value = mock_order

        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter

        db = MagicMock()
        db.query.return_value = mock_query
        db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else get_result
        yield db

    return _override


def _token(user: MagicMock) -> str:
    return create_token({"sub": str(user.id), "role": user.role})


def _auth_header(user: MagicMock) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


# ---------------------------------------------------------------------------
# GET /ruang
# ---------------------------------------------------------------------------

class TestListRuang:
    def test_returns_list_for_authenticated_user(self):
        user = _make_user("dosen")
        r1 = _make_ruang("LAB I", jenis="Lab")
        r2 = _make_ruang("R.101")

        app.dependency_overrides[get_db] = _db_override(user, query_result=[r1, r2])
        try:
            client = TestClient(app)
            resp = client.get("/ruang", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["nama"] == "LAB I"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_returns_empty_list_when_no_ruang(self):
        user = _make_user("admin")
        app.dependency_overrides[get_db] = _db_override(user, query_result=[])
        try:
            client = TestClient(app)
            resp = client.get("/ruang", headers=_auth_header(user))
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/ruang")
        assert resp.status_code in (401, 403)

    def test_response_contains_expected_fields(self):
        user = _make_user("koordinator_prodi")
        ruang = _make_ruang()
        app.dependency_overrides[get_db] = _db_override(user, query_result=[ruang])
        try:
            client = TestClient(app)
            resp = client.get("/ruang", headers=_auth_header(user))
            assert resp.status_code == 200
            item = resp.json()[0]
            for field in ("id", "nama", "kapasitas", "lantai", "gedung", "jenis", "is_active", "created_at"):
                assert field in item
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /ruang
# ---------------------------------------------------------------------------

class TestCreateRuang:
    _payload = {
        "nama": "R.101",
        "kapasitas": 40,
        "lantai": 1,
        "gedung": "Gedung A",
        "jenis": "Kelas",
    }

    def test_admin_can_create_ruang(self):
        user = _make_user("admin")
        new_ruang = _make_ruang(**{k: v for k, v in self._payload.items()})

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None  # no duplicate

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_ruang.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/ruang", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_sekretaris_jurusan_can_create_ruang(self):
        user = _make_user("sekretaris_jurusan")
        new_ruang = _make_ruang(**{k: v for k, v in self._payload.items()})

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_ruang.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/ruang", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_gets_403(self):
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.post("/ruang", json=self._payload, headers=_auth_header(user))
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_duplicate_nama_returns_409(self):
        user = _make_user("admin")
        existing = _make_ruang(nama="R.101")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = existing  # duplicate found

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/ruang", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/ruang", json=self._payload)
        assert resp.status_code in (401, 403)

    def test_default_kapasitas_applied(self):
        user = _make_user("admin")
        new_ruang = _make_ruang(nama="R.102", kapasitas=45)

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_ruang.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/ruang", json={"nama": "R.102"}, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# PUT /ruang/{id}
# ---------------------------------------------------------------------------

class TestUpdateRuang:
    def test_admin_can_update_ruang(self):
        user = _make_user("admin")
        ruang_id = uuid.uuid4()
        existing = _make_ruang(nama="R.101")
        existing.id = ruang_id

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None  # no nama conflict

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/ruang/{ruang_id}",
                json={"kapasitas": 50},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_jurusan_can_update_ruang(self):
        user = _make_user("tendik_jurusan")
        ruang_id = uuid.uuid4()
        existing = _make_ruang()
        existing.id = ruang_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/ruang/{ruang_id}",
                json={"gedung": "Gedung B"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_gets_403(self):
        ruang_id = uuid.uuid4()
        for role in ("dosen", "koordinator_prodi", "tendik_prodi"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.put(
                    f"/ruang/{ruang_id}",
                    json={"kapasitas": 50},
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        user = _make_user("admin")
        ruang_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/ruang/{ruang_id}",
                json={"kapasitas": 50},
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_duplicate_nama_on_update_returns_409(self):
        user = _make_user("admin")
        ruang_id = uuid.uuid4()
        existing = _make_ruang(nama="R.101")
        existing.id = ruang_id
        other_ruang = _make_ruang(nama="LAB I")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = other_ruang  # nama conflict

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/ruang/{ruang_id}",
                json={"nama": "LAB I"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_soft_deactivate_via_is_active(self):
        user = _make_user("admin")
        ruang_id = uuid.uuid4()
        existing = _make_ruang()
        existing.id = ruang_id
        existing.is_active = True

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/ruang/{ruang_id}",
                json={"is_active": False},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert existing.is_active is False
        finally:
            app.dependency_overrides.pop(get_db, None)
