"""
backend/tests/test_mata_kuliah.py
Unit tests for MataKuliah CRUD endpoints.

Covers:
  GET    /mata-kuliah              — list (no filter, prodi filter, kurikulum filter, semester filter)
  POST   /mata-kuliah              — create (happy path + duplicate 409)
  PUT    /mata-kuliah/{id}         — update (happy path + not found)
  DELETE /mata-kuliah/{id}         — soft delete (happy path + verify is_active=False)
  Role access                      — non-editor cannot POST/PUT/DELETE
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
from app.models.kurikulum import Kurikulum as KurikulumModel
from app.models.mata_kuliah import MataKuliah as MataKuliahModel
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


def _make_kurikulum(prodi_id: uuid.UUID = None) -> MagicMock:
    k = MagicMock(spec=KurikulumModel)
    k.id = uuid.uuid4()
    k.kode = "21S1MATH"
    k.tahun = "2021"
    k.prodi_id = prodi_id or uuid.uuid4()
    k.is_active = True
    k.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return k


def _make_mk(
    kode: str = "MAT101",
    kurikulum_id: uuid.UUID = None,
    semester: int = 1,
    is_active: bool = True,
    kurikulum: MagicMock = None,
) -> MagicMock:
    mk = MagicMock(spec=MataKuliahModel)
    mk.id = uuid.uuid4()
    mk.kode = kode
    mk.kurikulum_id = kurikulum_id or uuid.uuid4()
    mk.nama = f"Mata Kuliah {kode}"
    mk.sks = 3
    mk.semester = semester
    mk.jenis = "Wajib"
    mk.prasyarat = None
    mk.is_active = is_active
    mk.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    mk.kurikulum = kurikulum
    return mk


def _token(user: MagicMock) -> str:
    return create_token({"sub": str(user.id), "role": user.role})


def _auth_header(user: MagicMock) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


def _simple_db_override(user: MagicMock, query_result=None, get_result=None):
    """Simple DB override: query returns list, get returns get_result or user."""
    def _override():
        mock_filter = MagicMock()
        mock_filter.first.return_value = get_result
        mock_filter.all.return_value = query_result if query_result is not None else []

        mock_order = MagicMock()
        mock_order.all.return_value = query_result if query_result is not None else []

        mock_join = MagicMock()
        mock_join.filter.return_value = mock_filter
        mock_join.order_by.return_value = mock_order

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_query.join.return_value = mock_join
        mock_query.order_by.return_value = mock_order

        db = MagicMock()
        db.query.return_value = mock_query
        db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else get_result
        yield db

    return _override


# ---------------------------------------------------------------------------
# GET /mata-kuliah
# ---------------------------------------------------------------------------

class TestListMataKuliah:
    def test_returns_list_no_filter(self):
        user = _make_user("dosen")
        mk1 = _make_mk("MAT101")
        mk2 = _make_mk("MAT102")

        def _override():
            mock_filter = MagicMock()
            mock_filter.filter.return_value = mock_filter
            mock_filter.join.return_value = mock_filter
            mock_filter.order_by.return_value = mock_filter
            mock_filter.all.return_value = [mk1, mk2]

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get("/mata-kuliah", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_filter_by_kurikulum_id(self):
        user = _make_user("koordinator_prodi")
        kurikulum_id = uuid.uuid4()
        mk = _make_mk("MAT201", kurikulum_id=kurikulum_id)

        def _override():
            mock_filter = MagicMock()
            mock_filter.filter.return_value = mock_filter
            mock_filter.join.return_value = mock_filter
            mock_filter.order_by.return_value = mock_filter
            mock_filter.all.return_value = [mk]

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/mata-kuliah?kurikulum_id={kurikulum_id}", headers=_auth_header(user))
            assert resp.status_code == 200
            assert len(resp.json()) == 1
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_filter_by_semester(self):
        user = _make_user("dosen")
        mk = _make_mk("MAT301", semester=3)

        def _override():
            mock_filter = MagicMock()
            mock_filter.filter.return_value = mock_filter
            mock_filter.join.return_value = mock_filter
            mock_filter.order_by.return_value = mock_filter
            mock_filter.all.return_value = [mk]

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get("/mata-kuliah?semester=3", headers=_auth_header(user))
            assert resp.status_code == 200
            assert len(resp.json()) == 1
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_filter_by_prodi_id(self):
        user = _make_user("dosen")
        prodi_id = uuid.uuid4()
        mk = _make_mk("MAT401")

        def _override():
            mock_filter = MagicMock()
            mock_filter.filter.return_value = mock_filter
            mock_filter.join.return_value = mock_filter
            mock_filter.order_by.return_value = mock_filter
            mock_filter.all.return_value = [mk]

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter
            mock_query.join.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/mata-kuliah?prodi_id={prodi_id}", headers=_auth_header(user))
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/mata-kuliah")
        assert resp.status_code in (401, 403)

    def test_response_contains_expected_fields(self):
        user = _make_user("admin")
        kurikulum = _make_kurikulum()
        mk = _make_mk(kurikulum_id=kurikulum.id, kurikulum=kurikulum)

        def _override():
            mock_filter = MagicMock()
            mock_filter.filter.return_value = mock_filter
            mock_filter.join.return_value = mock_filter
            mock_filter.order_by.return_value = mock_filter
            mock_filter.all.return_value = [mk]

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get("/mata-kuliah", headers=_auth_header(user))
            assert resp.status_code == 200
            item = resp.json()[0]
            for field in ("id", "kode", "kurikulum_id", "nama", "sks", "semester", "jenis", "is_active", "created_at"):
                assert field in item
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /mata-kuliah
# ---------------------------------------------------------------------------

class TestCreateMataKuliah:
    _kurikulum_id = str(uuid.uuid4())
    _payload = {
        "kode": "MAT101",
        "kurikulum_id": _kurikulum_id,
        "nama": "Kalkulus I",
        "sks": 3,
        "semester": 1,
        "jenis": "Wajib",
    }

    def test_admin_can_create(self):
        user = _make_user("admin")
        new_mk = _make_mk(kode="MAT101")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None  # no duplicate

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_mk.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/mata-kuliah", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_sekretaris_jurusan_can_create(self):
        user = _make_user("sekretaris_jurusan")
        new_mk = _make_mk(kode="MAT101")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_mk.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/mata-kuliah", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_gets_403(self):
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _simple_db_override(user)
            try:
                client = TestClient(app)
                resp = client.post("/mata-kuliah", json=self._payload, headers=_auth_header(user))
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_duplicate_kode_kurikulum_returns_409(self):
        user = _make_user("admin")
        existing = _make_mk(kode="MAT101")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = existing  # duplicate

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/mata-kuliah", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_missing_required_field_returns_422(self):
        user = _make_user("admin")
        app.dependency_overrides[get_db] = _simple_db_override(user)
        try:
            client = TestClient(app)
            # Missing 'nama'
            payload = {k: v for k, v in self._payload.items() if k != "nama"}
            resp = client.post("/mata-kuliah", json=payload, headers=_auth_header(user))
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/mata-kuliah", json=self._payload)
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PUT /mata-kuliah/{id}
# ---------------------------------------------------------------------------

class TestUpdateMataKuliah:
    def test_admin_can_update(self):
        user = _make_user("admin")
        mk_id = uuid.uuid4()
        existing = _make_mk(kode="MAT101")
        existing.id = mk_id

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None  # no conflict

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
                f"/mata-kuliah/{mk_id}",
                json={"nama": "Kalkulus I (Updated)"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        user = _make_user("admin")
        mk_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/mata-kuliah/{mk_id}",
                json={"nama": "Updated"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_gets_403(self):
        mk_id = uuid.uuid4()
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _simple_db_override(user)
            try:
                client = TestClient(app)
                resp = client.put(
                    f"/mata-kuliah/{mk_id}",
                    json={"nama": "Updated"},
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_duplicate_kode_on_update_returns_409(self):
        user = _make_user("admin")
        mk_id = uuid.uuid4()
        existing = _make_mk(kode="MAT101")
        existing.id = mk_id
        other = _make_mk(kode="MAT102")
        other.kurikulum_id = existing.kurikulum_id

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = other  # conflict

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
                f"/mata-kuliah/{mk_id}",
                json={"kode": "MAT102"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# DELETE /mata-kuliah/{id}
# ---------------------------------------------------------------------------

class TestDeleteMataKuliah:
    def test_admin_can_soft_delete(self):
        user = _make_user("admin")
        mk_id = uuid.uuid4()
        existing = _make_mk(kode="MAT101", is_active=True)
        existing.id = mk_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.delete(f"/mata-kuliah/{mk_id}", headers=_auth_header(user))
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_soft_delete_sets_is_active_false(self):
        user = _make_user("admin")
        mk_id = uuid.uuid4()
        existing = _make_mk(kode="MAT101", is_active=True)
        existing.id = mk_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            client.delete(f"/mata-kuliah/{mk_id}", headers=_auth_header(user))
            # Record still exists but is_active is False
            assert existing.is_active is False
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_delete_not_found_returns_404(self):
        user = _make_user("admin")
        mk_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.delete(f"/mata-kuliah/{mk_id}", headers=_auth_header(user))
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_gets_403(self):
        mk_id = uuid.uuid4()
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _simple_db_override(user)
            try:
                client = TestClient(app)
                resp = client.delete(f"/mata-kuliah/{mk_id}", headers=_auth_header(user))
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Helpers for MataKuliahKelas tests
# ---------------------------------------------------------------------------

from app.models.mata_kuliah import MataKuliahKelas as MataKuliahKelasModel


def _make_kelas(
    mata_kuliah_id: uuid.UUID = None,
    kelas: str = "A",
    label: str = "Fisika Dasar - A",
) -> MagicMock:
    k = MagicMock(spec=MataKuliahKelasModel)
    k.id = uuid.uuid4()
    k.mata_kuliah_id = mata_kuliah_id or uuid.uuid4()
    k.kelas = kelas
    k.label = label
    k.ket = None
    k.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return k


# ---------------------------------------------------------------------------
# GET /mata-kuliah/{id}/kelas
# ---------------------------------------------------------------------------

class TestListKelas:
    def test_returns_kelas_list(self):
        user = _make_user("dosen")
        mk = _make_mk()
        kelas_a = _make_kelas(mata_kuliah_id=mk.id, kelas="A")
        kelas_b = _make_kelas(mata_kuliah_id=mk.id, kelas="B")

        def _override():
            mock_filter = MagicMock()
            mock_filter.order_by.return_value = mock_filter
            mock_filter.all.return_value = [kelas_a, kelas_b]

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else mk
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/mata-kuliah/{mk.id}/kelas", headers=_auth_header(user))
            assert resp.status_code == 200
            assert len(resp.json()) == 2
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_mk_not_found_returns_404(self):
        user = _make_user("dosen")
        mk_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/mata-kuliah/{mk_id}/kelas", headers=_auth_header(user))
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_response_contains_expected_fields(self):
        user = _make_user("admin")
        mk = _make_mk()
        kelas = _make_kelas(mata_kuliah_id=mk.id)

        def _override():
            mock_filter = MagicMock()
            mock_filter.order_by.return_value = mock_filter
            mock_filter.all.return_value = [kelas]

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else mk
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/mata-kuliah/{mk.id}/kelas", headers=_auth_header(user))
            assert resp.status_code == 200
            item = resp.json()[0]
            for field in ("id", "mata_kuliah_id", "kelas", "label", "ket", "created_at"):
                assert field in item
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        mk_id = uuid.uuid4()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(f"/mata-kuliah/{mk_id}/kelas")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /mata-kuliah/{id}/kelas
# ---------------------------------------------------------------------------

class TestCreateKelas:
    _payload = {"kelas": "A", "label": "Kalkulus I - A"}

    def test_admin_can_create(self):
        user = _make_user("admin")
        mk = _make_mk()
        new_kelas = _make_kelas(mata_kuliah_id=mk.id)

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None  # no duplicate

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else mk
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_kelas.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post(
                f"/mata-kuliah/{mk.id}/kelas",
                json=self._payload,
                headers=_auth_header(user),
            )
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_mk_not_found_returns_404(self):
        user = _make_user("admin")
        mk_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post(
                f"/mata-kuliah/{mk_id}/kelas",
                json=self._payload,
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_duplicate_kelas_returns_409(self):
        user = _make_user("admin")
        mk = _make_mk()
        existing_kelas = _make_kelas(mata_kuliah_id=mk.id, kelas="A")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = existing_kelas  # duplicate

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else mk
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post(
                f"/mata-kuliah/{mk.id}/kelas",
                json=self._payload,
                headers=_auth_header(user),
            )
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_gets_403(self):
        mk_id = uuid.uuid4()
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _simple_db_override(user)
            try:
                client = TestClient(app)
                resp = client.post(
                    f"/mata-kuliah/{mk_id}/kelas",
                    json=self._payload,
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_missing_label_returns_422(self):
        user = _make_user("admin")
        mk = _make_mk()
        app.dependency_overrides[get_db] = _simple_db_override(user, get_result=mk)
        try:
            client = TestClient(app)
            resp = client.post(
                f"/mata-kuliah/{mk.id}/kelas",
                json={"kelas": "A"},  # missing label
                headers=_auth_header(user),
            )
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# PUT /mata-kuliah/{id}/kelas/{kelas_id}
# ---------------------------------------------------------------------------

class TestUpdateKelas:
    def test_admin_can_update(self):
        user = _make_user("admin")
        mk = _make_mk()
        kelas = _make_kelas(mata_kuliah_id=mk.id, kelas="A")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None  # no conflict

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else kelas
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/mata-kuliah/{mk.id}/kelas/{kelas.id}",
                json={"label": "Kalkulus I - A (Updated)"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        user = _make_user("admin")
        mk_id = uuid.uuid4()
        kelas_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/mata-kuliah/{mk_id}/kelas/{kelas_id}",
                json={"label": "Updated"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_kelas_belongs_to_different_mk_returns_404(self):
        user = _make_user("admin")
        mk_id = uuid.uuid4()
        kelas = _make_kelas(mata_kuliah_id=uuid.uuid4())  # different mk

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else kelas
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/mata-kuliah/{mk_id}/kelas/{kelas.id}",
                json={"label": "Updated"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_duplicate_kelas_on_update_returns_409(self):
        user = _make_user("admin")
        mk = _make_mk()
        kelas = _make_kelas(mata_kuliah_id=mk.id, kelas="A")
        other = _make_kelas(mata_kuliah_id=mk.id, kelas="B")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = other  # conflict

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else kelas
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/mata-kuliah/{mk.id}/kelas/{kelas.id}",
                json={"kelas": "B"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_gets_403(self):
        mk_id = uuid.uuid4()
        kelas_id = uuid.uuid4()
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _simple_db_override(user)
            try:
                client = TestClient(app)
                resp = client.put(
                    f"/mata-kuliah/{mk_id}/kelas/{kelas_id}",
                    json={"label": "Updated"},
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# DELETE /mata-kuliah/{id}/kelas/{kelas_id}
# ---------------------------------------------------------------------------

class TestDeleteKelas:
    def test_admin_can_delete(self):
        user = _make_user("admin")
        mk = _make_mk()
        kelas = _make_kelas(mata_kuliah_id=mk.id)

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else kelas
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/mata-kuliah/{mk.id}/kelas/{kelas.id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_delete_calls_db_delete(self):
        user = _make_user("admin")
        mk = _make_mk()
        kelas = _make_kelas(mata_kuliah_id=mk.id)

        captured_db = {}

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else kelas
            captured_db["db"] = db
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            client.delete(
                f"/mata-kuliah/{mk.id}/kelas/{kelas.id}",
                headers=_auth_header(user),
            )
            captured_db["db"].delete.assert_called_once_with(kelas)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        user = _make_user("admin")
        mk_id = uuid.uuid4()
        kelas_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/mata-kuliah/{mk_id}/kelas/{kelas_id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_kelas_belongs_to_different_mk_returns_404(self):
        user = _make_user("admin")
        mk_id = uuid.uuid4()
        kelas = _make_kelas(mata_kuliah_id=uuid.uuid4())  # different mk

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else kelas
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/mata-kuliah/{mk_id}/kelas/{kelas.id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_gets_403(self):
        mk_id = uuid.uuid4()
        kelas_id = uuid.uuid4()
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _simple_db_override(user)
            try:
                client = TestClient(app)
                resp = client.delete(
                    f"/mata-kuliah/{mk_id}/kelas/{kelas_id}",
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)
