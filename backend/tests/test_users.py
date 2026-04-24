"""
backend/tests/test_users.py
Unit tests for User CRUD endpoints (admin only).

Covers:
  GET   /users                    — list users (admin only)
  POST  /users                    — create user (admin only)
  PUT   /users/{id}               — update user (admin only)
  PATCH /users/{id}/reset-password — reset password (admin only)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
from app.models.user import User as UserModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(role: str = "admin") -> MagicMock:
    user = MagicMock(spec=UserModel)
    user.id = uuid.uuid4()
    user.username = f"user_{role}"
    user.email = f"{role}@example.com"
    user.role = role
    user.is_active = True
    user.prodi_id = None
    user.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user.last_login = None
    return user


def _token(user: MagicMock) -> str:
    return create_token({"sub": str(user.id), "role": user.role})


def _auth_header(user: MagicMock) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


def _db_override(current_user: MagicMock, query_result=None, get_result=None):
    """Generic DB override for simple list/get scenarios."""
    def _override():
        mock_order = MagicMock()
        mock_order.all.return_value = query_result if query_result is not None else []

        mock_filter = MagicMock()
        mock_filter.first.return_value = get_result
        mock_filter.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_query.order_by.return_value = mock_order

        db = MagicMock()
        db.query.return_value = mock_query
        db.get.side_effect = lambda model, pk: current_user if model.__name__ == "User" else get_result
        yield db

    return _override


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------

class TestListUsers:
    def test_admin_can_list_users(self):
        admin = _make_user("admin")
        u1 = _make_user("dosen")
        u2 = _make_user("koordinator_prodi")

        app.dependency_overrides[get_db] = _db_override(admin, query_result=[u1, u2])
        try:
            client = TestClient(app)
            resp = client.get("/users", headers=_auth_header(admin))
            assert resp.status_code == 200
            assert len(resp.json()) == 2
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_admin_gets_403(self):
        for role in ("dosen", "sekretaris_jurusan", "koordinator_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user, query_result=[])
            try:
                client = TestClient(app)
                resp = client.get("/users", headers=_auth_header(user))
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_401_or_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/users")
        assert resp.status_code in (401, 403)

    def test_filter_by_role(self):
        admin = _make_user("admin")
        dosen_user = _make_user("dosen")

        app.dependency_overrides[get_db] = _db_override(admin, query_result=[dosen_user])
        try:
            client = TestClient(app)
            resp = client.get("/users?role=dosen", headers=_auth_header(admin))
            assert resp.status_code == 200
            assert len(resp.json()) == 1
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_filter_by_is_active(self):
        admin = _make_user("admin")
        inactive_user = _make_user("dosen")
        inactive_user.is_active = False

        app.dependency_overrides[get_db] = _db_override(admin, query_result=[inactive_user])
        try:
            client = TestClient(app)
            resp = client.get("/users?is_active=false", headers=_auth_header(admin))
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_response_contains_expected_fields(self):
        admin = _make_user("admin")
        u = _make_user("dosen")

        app.dependency_overrides[get_db] = _db_override(admin, query_result=[u])
        try:
            client = TestClient(app)
            resp = client.get("/users", headers=_auth_header(admin))
            assert resp.status_code == 200
            item = resp.json()[0]
            for field in ("id", "username", "email", "role", "is_active", "created_at"):
                assert field in item
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_returns_empty_list_when_no_users(self):
        admin = _make_user("admin")
        app.dependency_overrides[get_db] = _db_override(admin, query_result=[])
        try:
            client = TestClient(app)
            resp = client.get("/users", headers=_auth_header(admin))
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /users
# ---------------------------------------------------------------------------

class TestCreateUser:
    _payload = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "secret123",
        "role": "dosen",
    }

    def test_admin_can_create_user(self):
        admin = _make_user("admin")
        new_user = _make_user("dosen")
        new_user.username = "newuser"

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None  # no duplicate

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: admin if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_user.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            with patch("app.routers.users.hash_password", return_value="hashed"):
                resp = client.post("/users", json=self._payload, headers=_auth_header(admin))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_admin_gets_403(self):
        for role in ("dosen", "sekretaris_jurusan", "koordinator_prodi"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.post("/users", json=self._payload, headers=_auth_header(user))
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_duplicate_username_returns_409(self):
        admin = _make_user("admin")
        existing = _make_user("dosen")
        existing.username = "newuser"

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = existing  # duplicate found

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: admin if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/users", json=self._payload, headers=_auth_header(admin))
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_401_or_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/users", json=self._payload)
        assert resp.status_code in (401, 403)

    def test_create_user_with_prodi_id(self):
        admin = _make_user("admin")
        prodi_id = uuid.uuid4()
        new_user = _make_user("koordinator_prodi")
        new_user.prodi_id = prodi_id

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: admin if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_user.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            payload = {**self._payload, "role": "koordinator_prodi", "prodi_id": str(prodi_id)}
            with patch("app.routers.users.hash_password", return_value="hashed"):
                resp = client.post("/users", json=payload, headers=_auth_header(admin))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# PUT /users/{id}
# ---------------------------------------------------------------------------

class TestUpdateUser:
    def test_admin_can_update_user(self):
        admin = _make_user("admin")
        target_id = uuid.uuid4()
        target = _make_user("dosen")
        target.id = target_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: admin if (model.__name__ == "User" and pk == str(admin.id)) else target
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/users/{target_id}",
                json={"is_active": False},
                headers=_auth_header(admin),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_admin_gets_403(self):
        target_id = uuid.uuid4()
        for role in ("dosen", "sekretaris_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.put(
                    f"/users/{target_id}",
                    json={"is_active": False},
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        admin = _make_user("admin")
        target_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            # Return admin for auth lookup (str(admin.id)), None for target
            db.get.side_effect = lambda model, pk: admin if pk == str(admin.id) else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/users/{target_id}",
                json={"is_active": False},
                headers=_auth_header(admin),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_update_role(self):
        admin = _make_user("admin")
        target_id = uuid.uuid4()
        target = _make_user("dosen")
        target.id = target_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: admin if (model.__name__ == "User" and pk == str(admin.id)) else target
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/users/{target_id}",
                json={"role": "koordinator_prodi"},
                headers=_auth_header(admin),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# PATCH /users/{id}/reset-password
# ---------------------------------------------------------------------------

class TestResetPassword:
    def test_admin_can_reset_password(self):
        admin = _make_user("admin")
        target_id = uuid.uuid4()
        target = _make_user("dosen")
        target.id = target_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: admin if pk == str(admin.id) else target
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            with patch("app.routers.users.hash_password", return_value="hashed"):
                resp = client.patch(
                    f"/users/{target_id}/reset-password",
                    json={"new_password": "newpassword123"},
                    headers=_auth_header(admin),
                )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_admin_gets_403(self):
        target_id = uuid.uuid4()
        for role in ("dosen", "sekretaris_jurusan", "koordinator_prodi"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.patch(
                    f"/users/{target_id}/reset-password",
                    json={"new_password": "newpassword123"},
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        admin = _make_user("admin")
        target_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            # Return admin for auth lookup, None for target
            db.get.side_effect = lambda model, pk: admin if pk == str(admin.id) else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/users/{target_id}/reset-password",
                json={"new_password": "newpassword123"},
                headers=_auth_header(admin),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_401_or_403(self):
        target_id = uuid.uuid4()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.patch(
            f"/users/{target_id}/reset-password",
            json={"new_password": "newpassword123"},
        )
        assert resp.status_code in (401, 403)
