"""
backend/tests/test_kurikulum.py
Unit tests for Kurikulum CRUD endpoints.

Covers:
  GET  /kurikulum        — list all kurikulum (authenticated)
  POST /kurikulum        — create kurikulum (admin only)
  PUT  /kurikulum/{id}   — update kurikulum (admin only)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
from app.models.kurikulum import Kurikulum as KurikulumModel
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


def _make_kurikulum(
    kode: str = "21S1MATH",
    tahun: str = "2021",
    prodi_id: uuid.UUID = None,
    is_active: bool = True,
) -> MagicMock:
    k = MagicMock(spec=KurikulumModel)
    k.id = uuid.uuid4()
    k.kode = kode
    k.tahun = tahun
    k.prodi_id = prodi_id or uuid.uuid4()
    k.is_active = is_active
    k.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return k


def _db_override(user: MagicMock, query_result=None, get_result=None):
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
        db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else get_result
        yield db

    return _override


def _token(user: MagicMock) -> str:
    return create_token({"sub": str(user.id), "role": user.role})


def _auth_header(user: MagicMock) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


# ---------------------------------------------------------------------------
# GET /kurikulum
# ---------------------------------------------------------------------------

class TestListKurikulum:
    def test_returns_list_for_authenticated_user(self):
        user = _make_user("dosen")
        k1 = _make_kurikulum("21S1MATH", "2021")
        k2 = _make_kurikulum("25S1MATH", "2025")

        app.dependency_overrides[get_db] = _db_override(user, query_result=[k1, k2])
        try:
            client = TestClient(app)
            resp = client.get("/kurikulum", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["kode"] == "21S1MATH"
            assert data[1]["kode"] == "25S1MATH"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_returns_empty_list_when_no_kurikulum(self):
        user = _make_user("admin")
        app.dependency_overrides[get_db] = _db_override(user, query_result=[])
        try:
            client = TestClient(app)
            resp = client.get("/kurikulum", headers=_auth_header(user))
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/kurikulum")
        assert resp.status_code in (401, 403)

    def test_response_contains_expected_fields(self):
        user = _make_user("koordinator_prodi")
        k = _make_kurikulum()
        app.dependency_overrides[get_db] = _db_override(user, query_result=[k])
        try:
            client = TestClient(app)
            resp = client.get("/kurikulum", headers=_auth_header(user))
            assert resp.status_code == 200
            item = resp.json()[0]
            for field in ("id", "kode", "tahun", "prodi_id", "is_active", "created_at"):
                assert field in item
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /kurikulum
# ---------------------------------------------------------------------------

class TestCreateKurikulum:
    _prodi_id = str(uuid.uuid4())
    _payload = {
        "kode": "21S1MATH",
        "tahun": "2021",
        "prodi_id": _prodi_id,
    }

    def test_admin_can_create_kurikulum(self):
        user = _make_user("admin")
        new_k = _make_kurikulum(kode="21S1MATH", tahun="2021")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None  # no duplicate

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_k.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/kurikulum", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_admin_gets_403(self):
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.post("/kurikulum", json=self._payload, headers=_auth_header(user))
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_duplicate_kode_returns_409(self):
        user = _make_user("admin")
        existing = _make_kurikulum(kode="21S1MATH")

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
            resp = client.post("/kurikulum", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/kurikulum", json=self._payload)
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PUT /kurikulum/{id}
# ---------------------------------------------------------------------------

class TestUpdateKurikulum:
    def test_admin_can_update_kurikulum(self):
        user = _make_user("admin")
        kurikulum_id = uuid.uuid4()
        existing = _make_kurikulum(kode="21S1MATH")
        existing.id = kurikulum_id

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
                f"/kurikulum/{kurikulum_id}",
                json={"tahun": "2022"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_admin_gets_403(self):
        kurikulum_id = uuid.uuid4()
        for role in ("dosen", "koordinator_prodi", "tendik_prodi"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.put(
                    f"/kurikulum/{kurikulum_id}",
                    json={"tahun": "2022"},
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        user = _make_user("admin")
        kurikulum_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/kurikulum/{kurikulum_id}",
                json={"tahun": "2022"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_duplicate_kode_on_update_returns_409(self):
        user = _make_user("admin")
        kurikulum_id = uuid.uuid4()
        existing = _make_kurikulum(kode="21S1MATH")
        existing.id = kurikulum_id
        other = _make_kurikulum(kode="25S1MATH")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = other  # kode conflict

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
                f"/kurikulum/{kurikulum_id}",
                json={"kode": "25S1MATH"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_soft_deactivate_via_is_active(self):
        user = _make_user("admin")
        kurikulum_id = uuid.uuid4()
        existing = _make_kurikulum()
        existing.id = kurikulum_id
        existing.is_active = True

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/kurikulum/{kurikulum_id}",
                json={"is_active": False},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert existing.is_active is False
        finally:
            app.dependency_overrides.pop(get_db, None)
