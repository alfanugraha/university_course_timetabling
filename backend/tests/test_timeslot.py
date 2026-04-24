"""
backend/tests/test_timeslot.py
Unit tests for Timeslot CRUD endpoints.

Covers:
  GET  /timeslot        — list timeslot (authenticated)
  POST /timeslot        — create timeslot (admin only)
  PUT  /timeslot/{id}   — update timeslot (admin only)
"""

import uuid
from datetime import datetime, time, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
from app.models.timeslot import Timeslot as TimeslotModel
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


def _make_timeslot(
    kode: str = "mon_s1",
    hari: str = "Senin",
    sesi: int = 1,
    jam_mulai: time = time(7, 30),
    jam_selesai: time = time(10, 0),
    label: str = "Senin 07:30–10:00",
    sks: int = 3,
) -> MagicMock:
    ts = MagicMock(spec=TimeslotModel)
    ts.id = uuid.uuid4()
    ts.kode = kode
    ts.hari = hari
    ts.sesi = sesi
    ts.jam_mulai = jam_mulai
    ts.jam_selesai = jam_selesai
    ts.label = label
    ts.sks = sks
    ts.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return ts


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
# GET /timeslot
# ---------------------------------------------------------------------------

class TestListTimeslot:
    def test_returns_list_for_authenticated_user(self):
        user = _make_user("dosen")
        ts1 = _make_timeslot("mon_s1", "Senin", 1)
        ts2 = _make_timeslot("mon_s2", "Senin", 2)

        app.dependency_overrides[get_db] = _db_override(user, query_result=[ts1, ts2])
        try:
            client = TestClient(app)
            resp = client.get("/timeslot", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["kode"] == "mon_s1"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_returns_empty_list_when_no_timeslot(self):
        user = _make_user("admin")
        app.dependency_overrides[get_db] = _db_override(user, query_result=[])
        try:
            client = TestClient(app)
            resp = client.get("/timeslot", headers=_auth_header(user))
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/timeslot")
        assert resp.status_code in (401, 403)

    def test_response_contains_expected_fields(self):
        user = _make_user("koordinator_prodi")
        ts = _make_timeslot()
        app.dependency_overrides[get_db] = _db_override(user, query_result=[ts])
        try:
            client = TestClient(app)
            resp = client.get("/timeslot", headers=_auth_header(user))
            assert resp.status_code == 200
            item = resp.json()[0]
            for field in ("id", "kode", "hari", "sesi", "jam_mulai", "jam_selesai", "label", "sks", "created_at"):
                assert field in item
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /timeslot
# ---------------------------------------------------------------------------

class TestCreateTimeslot:
    _payload = {
        "kode": "mon_s1",
        "hari": "Senin",
        "sesi": 1,
        "jam_mulai": "07:30:00",
        "jam_selesai": "10:00:00",
        "label": "Senin 07:30–10:00",
        "sks": 3,
    }

    def test_admin_can_create_timeslot(self):
        user = _make_user("admin")
        new_ts = _make_timeslot()

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None  # no duplicate

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_ts.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/timeslot", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_admin_gets_403(self):
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan",
                     "sekretaris_jurusan", "tendik_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.post("/timeslot", json=self._payload, headers=_auth_header(user))
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_duplicate_kode_returns_409(self):
        user = _make_user("admin")
        existing = _make_timeslot(kode="mon_s1")

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
            resp = client.post("/timeslot", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/timeslot", json=self._payload)
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PUT /timeslot/{id}
# ---------------------------------------------------------------------------

class TestUpdateTimeslot:
    def test_admin_can_update_timeslot(self):
        user = _make_user("admin")
        ts_id = uuid.uuid4()
        existing = _make_timeslot(kode="mon_s1")
        existing.id = ts_id

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
                f"/timeslot/{ts_id}",
                json={"label": "Senin 07:30–10:00 (updated)"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_admin_gets_403(self):
        ts_id = uuid.uuid4()
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "sekretaris_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.put(
                    f"/timeslot/{ts_id}",
                    json={"label": "updated"},
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        user = _make_user("admin")
        ts_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/timeslot/{ts_id}",
                json={"label": "updated"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_duplicate_kode_on_update_returns_409(self):
        user = _make_user("admin")
        ts_id = uuid.uuid4()
        existing = _make_timeslot(kode="mon_s1")
        existing.id = ts_id
        other_ts = _make_timeslot(kode="mon_s2")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = other_ts  # kode conflict

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
                f"/timeslot/{ts_id}",
                json={"kode": "mon_s2"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)
