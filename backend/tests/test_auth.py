"""
backend/tests/test_auth.py
Unit tests for JWT utilities in app/core/auth.py.
"""

import uuid
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from app.config import settings
from app.core.auth import ALGORITHM, create_token, get_current_user, verify_token


# ---------------------------------------------------------------------------
# create_token
# ---------------------------------------------------------------------------

class TestCreateToken:
    def test_returns_string(self):
        token = create_token({"sub": str(uuid.uuid4()), "role": "admin"})
        assert isinstance(token, str)

    def test_payload_round_trip(self):
        user_id = str(uuid.uuid4())
        token = create_token({"sub": user_id, "role": "dosen"})
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        assert payload["sub"] == user_id
        assert payload["role"] == "dosen"

    def test_exp_is_set(self):
        token = create_token({"sub": "abc"})
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_custom_expiry(self):
        token = create_token({"sub": "abc"}, expires_delta=timedelta(hours=1))
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_original_data_not_mutated(self):
        data = {"sub": "abc", "role": "admin"}
        create_token(data)
        # exp should NOT have been added to the original dict
        assert "exp" not in data


# ---------------------------------------------------------------------------
# verify_token
# ---------------------------------------------------------------------------

class TestVerifyToken:
    def test_valid_token_returns_payload(self):
        user_id = str(uuid.uuid4())
        token = create_token({"sub": user_id, "role": "admin"})
        payload = verify_token(token)
        assert payload["sub"] == user_id

    def test_expired_token_raises_401(self):
        token = create_token({"sub": "abc"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        token = create_token({"sub": "abc"}) + "tampered"
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401

    def test_wrong_secret_raises_401(self):
        token = jwt.encode({"sub": "abc"}, "wrong-secret", algorithm=ALGORITHM)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401

    def test_missing_sub_raises_401(self):
        token = create_token({"role": "admin"})  # no sub
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401

    def test_garbage_string_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_token("not.a.jwt")
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    def _make_credentials(self, token: str):
        creds = MagicMock()
        creds.credentials = token
        return creds

    def _make_db(self, user):
        db = MagicMock()
        db.get.return_value = user
        return db

    def test_returns_active_user(self):
        user_id = uuid.uuid4()
        token = create_token({"sub": str(user_id), "role": "admin"})

        mock_user = MagicMock()
        mock_user.is_active = True

        result = get_current_user(
            credentials=self._make_credentials(token),
            db=self._make_db(mock_user),
        )
        assert result is mock_user

    def test_inactive_user_raises_401(self):
        user_id = uuid.uuid4()
        token = create_token({"sub": str(user_id), "role": "dosen"})

        mock_user = MagicMock()
        mock_user.is_active = False

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                credentials=self._make_credentials(token),
                db=self._make_db(mock_user),
            )
        assert exc_info.value.status_code == 401

    def test_user_not_found_raises_401(self):
        user_id = uuid.uuid4()
        token = create_token({"sub": str(user_id), "role": "admin"})

        db = MagicMock()
        db.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                credentials=self._make_credentials(token),
                db=db,
            )
        assert exc_info.value.status_code == 401

    def test_invalid_token_raises_401(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                credentials=self._make_credentials("bad.token.here"),
                db=db,
            )
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/login  (unit tests calling the handler directly)
# ---------------------------------------------------------------------------

import uuid as _uuid
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.routers.auth import login
from app.schemas.auth import LoginRequest


def _make_user(username="admin", role="admin", is_active=True):
    """Helper: build a mock User ORM object with a pre-set password_hash."""
    user = MagicMock()
    user.id = _uuid.uuid4()
    user.username = username
    user.password_hash = "$2b$12$fakehashvalue"  # not real bcrypt — verify is mocked
    user.role = role
    user.is_active = is_active
    return user


def _db_with_user(user):
    """Return a mock DB session whose query().filter().first() returns *user*."""
    mock_filter = MagicMock()
    mock_filter.first.return_value = user
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_filter
    db = MagicMock()
    db.query.return_value = mock_query
    return db


class TestLoginEndpoint:
    def test_valid_credentials_returns_token(self):
        user = _make_user()
        db = _db_with_user(user)

        with patch("app.routers.auth.verify_password", return_value=True):
            result = login(LoginRequest(username="admin", password="secret"), db=db)

        assert result.access_token
        assert result.token_type == "bearer"
        assert result.user.username == "admin"
        assert result.user.role == "admin"

    def test_wrong_password_raises_401(self):
        user = _make_user()
        db = _db_with_user(user)

        with patch("app.routers.auth.verify_password", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                login(LoginRequest(username="admin", password="wrongpassword"), db=db)

        assert exc_info.value.status_code == 401

    def test_unknown_user_raises_401(self):
        db = _db_with_user(None)  # user not found

        with patch("app.routers.auth.verify_password", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                login(LoginRequest(username="nobody", password="secret"), db=db)

        assert exc_info.value.status_code == 401

    def test_inactive_user_raises_401(self):
        user = _make_user(is_active=False)
        db = _db_with_user(user)

        with patch("app.routers.auth.verify_password", return_value=True):
            with pytest.raises(HTTPException) as exc_info:
                login(LoginRequest(username="admin", password="secret"), db=db)

        assert exc_info.value.status_code == 401

    def test_response_contains_user_id(self):
        user = _make_user()
        db = _db_with_user(user)

        with patch("app.routers.auth.verify_password", return_value=True):
            result = login(LoginRequest(username="admin", password="secret"), db=db)

        assert result.user.id == user.id

    def test_last_login_updated_on_success(self):
        user = _make_user()
        db = _db_with_user(user)

        with patch("app.routers.auth.verify_password", return_value=True):
            login(LoginRequest(username="admin", password="secret"), db=db)

        db.commit.assert_called_once()
        assert user.last_login is not None


# ---------------------------------------------------------------------------
# GET /auth/me  (unit tests calling the handler directly)
# ---------------------------------------------------------------------------

import uuid as _uuid2
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.routers.auth import me


def _make_full_user(role="admin", prodi_id=None):
    """Build a mock User with all profile fields."""
    user = MagicMock()
    user.id = _uuid2.uuid4()
    user.username = "testuser"
    user.email = "test@example.com"
    user.role = role
    user.prodi_id = prodi_id
    user.is_active = True
    user.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user.last_login = datetime(2024, 6, 1, tzinfo=timezone.utc)
    return user


class TestMeEndpoint:
    def test_returns_full_profile(self):
        user = _make_full_user(role="admin")
        result = me(current_user=user)

        assert result.id == user.id
        assert result.username == user.username
        assert result.email == user.email
        assert result.role == user.role
        assert result.is_active is True
        assert result.created_at == user.created_at
        assert result.last_login == user.last_login

    def test_returns_profile_without_prodi(self):
        user = _make_full_user(role="admin", prodi_id=None)
        result = me(current_user=user)
        assert result.prodi_id is None

    def test_returns_profile_with_prodi(self):
        prodi_id = _uuid2.uuid4()
        user = _make_full_user(role="koordinator_prodi", prodi_id=prodi_id)
        result = me(current_user=user)
        assert result.prodi_id == prodi_id

    def test_returns_profile_without_last_login(self):
        user = _make_full_user()
        user.last_login = None
        result = me(current_user=user)
        assert result.last_login is None

    def test_all_roles_can_access(self):
        roles = [
            "admin", "ketua_jurusan", "sekretaris_jurusan",
            "koordinator_prodi", "dosen", "tendik_prodi", "tendik_jurusan",
        ]
        for role in roles:
            user = _make_full_user(role=role)
            result = me(current_user=user)
            assert result.role == role


# ---------------------------------------------------------------------------
# HTTP integration tests — POST /auth/login & GET /auth/me via TestClient
# ---------------------------------------------------------------------------

import uuid as _uuid3
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
from app.models.user import User as UserModel


def _build_orm_user(
    username: str = "admin",
    role: str = "admin",
    is_active: bool = True,
    password_hash: str = "$2b$12$placeholder",
) -> MagicMock:
    """Return a mock ORM User with all required attributes."""
    user = MagicMock(spec=UserModel)
    user.id = _uuid3.uuid4()
    user.username = username
    user.email = f"{username}@example.com"
    user.role = role
    user.is_active = is_active
    user.password_hash = password_hash
    user.prodi_id = None
    user.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user.last_login = None
    return user


def _make_db_override(user):
    """Return a get_db override whose query().filter().first() yields *user*."""
    def _override():
        mock_filter = MagicMock()
        mock_filter.first.return_value = user
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_filter
        db = MagicMock()
        db.query.return_value = mock_query
        # db.get() used by get_current_user
        db.get.return_value = user
        yield db
    return _override


class TestAuthHTTP:
    """Integration-level tests hitting the real FastAPI routes via TestClient."""

    # ------------------------------------------------------------------
    # 1. Login sukses — valid credentials → 200 + JWT token
    # ------------------------------------------------------------------

    def test_login_sukses_returns_token(self):
        user = _build_orm_user()
        app.dependency_overrides[get_db] = _make_db_override(user)
        try:
            with patch("app.routers.auth.verify_password", return_value=True):
                client = TestClient(app)
                resp = client.post(
                    "/auth/login",
                    json={"username": "admin", "password": "secret"},
                )
            assert resp.status_code == 200
            body = resp.json()
            assert "access_token" in body
            assert body["token_type"] == "bearer"
            assert body["user"]["username"] == "admin"
            assert body["user"]["role"] == "admin"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_login_sukses_token_is_valid_jwt(self):
        user = _build_orm_user()
        app.dependency_overrides[get_db] = _make_db_override(user)
        try:
            with patch("app.routers.auth.verify_password", return_value=True):
                client = TestClient(app)
                resp = client.post(
                    "/auth/login",
                    json={"username": "admin", "password": "secret"},
                )
            token = resp.json()["access_token"]
            # Token must be decodable with the app secret
            from jose import jwt as _jwt
            from app.config import settings
            from app.core.auth import ALGORITHM
            payload = _jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
            assert payload["sub"] == str(user.id)
            assert payload["role"] == "admin"
        finally:
            app.dependency_overrides.pop(get_db, None)

    # ------------------------------------------------------------------
    # 2. Login gagal — wrong password / wrong username → 401
    # ------------------------------------------------------------------

    def test_login_gagal_wrong_password(self):
        user = _build_orm_user()
        app.dependency_overrides[get_db] = _make_db_override(user)
        try:
            with patch("app.routers.auth.verify_password", return_value=False):
                client = TestClient(app)
                resp = client.post(
                    "/auth/login",
                    json={"username": "admin", "password": "salah"},
                )
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_login_gagal_wrong_username(self):
        # DB returns None — user not found
        app.dependency_overrides[get_db] = _make_db_override(None)
        try:
            client = TestClient(app)
            resp = client.post(
                "/auth/login",
                json={"username": "tidakada", "password": "secret"},
            )
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_login_gagal_inactive_user(self):
        user = _build_orm_user(is_active=False)
        app.dependency_overrides[get_db] = _make_db_override(user)
        try:
            with patch("app.routers.auth.verify_password", return_value=True):
                client = TestClient(app)
                resp = client.post(
                    "/auth/login",
                    json={"username": "admin", "password": "secret"},
                )
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.pop(get_db, None)

    # ------------------------------------------------------------------
    # 3. Token expired → GET /auth/me returns 401
    # ------------------------------------------------------------------

    def test_token_expired_returns_401(self):
        user = _build_orm_user()
        app.dependency_overrides[get_db] = _make_db_override(user)
        try:
            # Create a token that expired 1 second in the past
            expired_token = create_token(
                {"sub": str(user.id), "role": user.role},
                expires_delta=timedelta(seconds=-1),
            )
            client = TestClient(app)
            resp = client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {expired_token}"},
            )
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.pop(get_db, None)

    # ------------------------------------------------------------------
    # 4. Akses tanpa token → GET /auth/me returns 401/403
    # ------------------------------------------------------------------

    def test_akses_tanpa_token_returns_401(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/auth/me")
        # FastAPI HTTPBearer returns 403 when no credentials are provided
        assert resp.status_code in (401, 403)

    def test_akses_dengan_token_valid_returns_200(self):
        user = _build_orm_user()
        app.dependency_overrides[get_db] = _make_db_override(user)
        try:
            token = create_token({"sub": str(user.id), "role": user.role})
            client = TestClient(app)
            resp = client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["username"] == user.username
            assert body["role"] == user.role
        finally:
            app.dependency_overrides.pop(get_db, None)
