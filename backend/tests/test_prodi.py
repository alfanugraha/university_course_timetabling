"""
backend/tests/test_prodi.py
Unit tests for Prodi CRUD endpoints.

Covers:
  GET  /prodi        — list all prodi (authenticated)
  POST /prodi        — create prodi (admin only)
  PUT  /prodi/{id}   — update prodi (admin only)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
from app.models.prodi import Prodi as ProdiModel
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


def _make_prodi(
    kode: str = "S1MAT",
    nama: str = "S1 Matematika",
    strata: str = "S1",
    singkat: str = "MAT",
    kategori: str = "saintek",
    is_active: bool = True,
) -> MagicMock:
    prodi = MagicMock(spec=ProdiModel)
    prodi.id = uuid.uuid4()
    prodi.kode = kode
    prodi.nama = nama
    prodi.strata = strata
    prodi.singkat = singkat
    prodi.kategori = kategori
    prodi.is_active = is_active
    prodi.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return prodi


def _db_override(
    user: MagicMock,
    query_result=None,
    get_result=None,
):
    """Build a get_db override.

    - db.query(...).order_by(...).all() → query_result (list)
    - db.query(...).filter(...).first() → get_result (single object or None)
    - db.get(Model, id) → get_result
    """
    def _override():
        mock_order = MagicMock()
        mock_order.all.return_value = query_result if query_result is not None else []

        mock_filter = MagicMock()
        mock_filter.first.return_value = get_result

        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter

        db = MagicMock()
        db.query.return_value = mock_query
        db.get.return_value = get_result
        # db.get for user lookup (get_current_user)
        db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else get_result
        yield db

    return _override


def _token(user: MagicMock) -> str:
    return create_token({"sub": str(user.id), "role": user.role})


def _auth_header(user: MagicMock) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


# ---------------------------------------------------------------------------
# GET /prodi
# ---------------------------------------------------------------------------

class TestListProdi:
    def test_returns_list_for_authenticated_user(self):
        user = _make_user("dosen")
        prodi1 = _make_prodi("S1MAT", "S1 Matematika")
        prodi2 = _make_prodi("S2MAT", "S2 Matematika", strata="S2")

        app.dependency_overrides[get_db] = _db_override(user, query_result=[prodi1, prodi2])
        try:
            client = TestClient(app)
            resp = client.get("/prodi", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["kode"] == "S1MAT"
            assert data[1]["kode"] == "S2MAT"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_returns_empty_list_when_no_prodi(self):
        user = _make_user("admin")
        app.dependency_overrides[get_db] = _db_override(user, query_result=[])
        try:
            client = TestClient(app)
            resp = client.get("/prodi", headers=_auth_header(user))
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/prodi")
        assert resp.status_code in (401, 403)

    def test_response_contains_expected_fields(self):
        user = _make_user("koordinator_prodi")
        prodi = _make_prodi()
        app.dependency_overrides[get_db] = _db_override(user, query_result=[prodi])
        try:
            client = TestClient(app)
            resp = client.get("/prodi", headers=_auth_header(user))
            assert resp.status_code == 200
            item = resp.json()[0]
            for field in ("id", "kode", "nama", "strata", "singkat", "kategori", "is_active", "created_at"):
                assert field in item
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /prodi
# ---------------------------------------------------------------------------

class TestCreateProdi:
    _payload = {
        "kode": "S1MAT",
        "strata": "S1",
        "nama": "S1 Matematika",
        "singkat": "MAT",
        "kategori": "saintek",
    }

    def test_admin_can_create_prodi(self):
        user = _make_user("admin")
        new_prodi = _make_prodi(**{k: v for k, v in self._payload.items()})

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None  # no duplicate

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_prodi.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/prodi", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_admin_gets_403(self):
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.post("/prodi", json=self._payload, headers=_auth_header(user))
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_duplicate_kode_returns_409(self):
        user = _make_user("admin")
        existing = _make_prodi(kode="S1MAT")

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
            resp = client.post("/prodi", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/prodi", json=self._payload)
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PUT /prodi/{id}
# ---------------------------------------------------------------------------

class TestUpdateProdi:
    def test_admin_can_update_prodi(self):
        user = _make_user("admin")
        prodi_id = uuid.uuid4()
        existing = _make_prodi(kode="S1MAT")
        existing.id = prodi_id

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None  # no kode conflict

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
                f"/prodi/{prodi_id}",
                json={"nama": "S1 Matematika Updated"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_admin_gets_403(self):
        prodi_id = uuid.uuid4()
        for role in ("dosen", "koordinator_prodi", "tendik_prodi"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.put(
                    f"/prodi/{prodi_id}",
                    json={"nama": "Updated"},
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        user = _make_user("admin")
        prodi_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/prodi/{prodi_id}",
                json={"nama": "Updated"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_duplicate_kode_on_update_returns_409(self):
        user = _make_user("admin")
        prodi_id = uuid.uuid4()
        existing = _make_prodi(kode="S1MAT")
        existing.id = prodi_id
        other_prodi = _make_prodi(kode="S2MAT")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = other_prodi  # kode conflict

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
                f"/prodi/{prodi_id}",
                json={"kode": "S2MAT"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_soft_deactivate_via_is_active(self):
        user = _make_user("admin")
        prodi_id = uuid.uuid4()
        existing = _make_prodi()
        existing.id = prodi_id
        existing.is_active = True

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/prodi/{prodi_id}",
                json={"is_active": False},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            # Verify the attribute was set on the mock
            assert existing.is_active is False
        finally:
            app.dependency_overrides.pop(get_db, None)
