"""
backend/tests/test_dosen.py
Unit tests for Dosen CRUD endpoints.

Covers:
  GET  /dosen              — list dosen (semua role kecuali dosen)
  GET  /dosen?homebase_prodi_id=... — filter by homebase
  GET  /dosen?status=...   — filter by status
  POST /dosen              — create dosen (EDITOR_ROLES_JURUSAN)
  PUT  /dosen/{id}         — update dosen (EDITOR_ROLES_JURUSAN)
"""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
from app.models.dosen import Dosen as DosenModel
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


def _make_dosen(
    kode: str = "DSN001",
    nama: str = "Dr. Budi Santoso",
    nidn: str = "1234567890",
    nip: str = None,
    jabfung: str = "Lektor",
    kjfd: str = "Analisis",
    homebase_prodi_id: uuid.UUID = None,
    bkd_limit_sks: int = None,
    tgl_lahir: date = None,
    status: str = "Aktif",
    user_id: uuid.UUID = None,
) -> MagicMock:
    dosen = MagicMock(spec=DosenModel)
    dosen.id = uuid.uuid4()
    dosen.kode = kode
    dosen.nama = nama
    dosen.nidn = nidn
    dosen.nip = nip
    dosen.jabfung = jabfung
    dosen.kjfd = kjfd
    dosen.homebase_prodi_id = homebase_prodi_id
    dosen.bkd_limit_sks = bkd_limit_sks
    dosen.tgl_lahir = tgl_lahir
    dosen.status = status
    dosen.user_id = user_id
    dosen.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return dosen


def _db_override(user: MagicMock, query_result=None, get_result=None):
    def _override():
        mock_order = MagicMock()
        mock_order.all.return_value = query_result if query_result is not None else []

        mock_filter = MagicMock()
        mock_filter.first.return_value = get_result
        mock_filter.order_by.return_value = mock_order
        mock_filter.filter.return_value = mock_filter

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
# GET /dosen
# ---------------------------------------------------------------------------

class TestListDosen:
    def test_returns_list_for_admin(self):
        user = _make_user("admin")
        d1 = _make_dosen("DSN001", "Dr. Budi")
        d2 = _make_dosen("DSN002", "Dr. Sari")

        app.dependency_overrides[get_db] = _db_override(user, query_result=[d1, d2])
        try:
            client = TestClient(app)
            resp = client.get("/dosen", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_returns_list_for_sekretaris_jurusan(self):
        user = _make_user("sekretaris_jurusan")
        d1 = _make_dosen()

        app.dependency_overrides[get_db] = _db_override(user, query_result=[d1])
        try:
            client = TestClient(app)
            resp = client.get("/dosen", headers=_auth_header(user))
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_returns_list_for_koordinator_prodi(self):
        user = _make_user("koordinator_prodi")
        app.dependency_overrides[get_db] = _db_override(user, query_result=[])
        try:
            client = TestClient(app)
            resp = client.get("/dosen", headers=_auth_header(user))
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_role_gets_403(self):
        user = _make_user("dosen")
        app.dependency_overrides[get_db] = _db_override(user, query_result=[])
        try:
            client = TestClient(app)
            resp = client.get("/dosen", headers=_auth_header(user))
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/dosen")
        assert resp.status_code in (401, 403)

    def test_response_contains_expected_fields(self):
        user = _make_user("admin")
        dosen = _make_dosen()
        app.dependency_overrides[get_db] = _db_override(user, query_result=[dosen])
        try:
            client = TestClient(app)
            resp = client.get("/dosen", headers=_auth_header(user))
            assert resp.status_code == 200
            item = resp.json()[0]
            for field in ("id", "kode", "nama", "nidn", "status", "created_at"):
                assert field in item
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_filter_by_homebase_prodi_id(self):
        user = _make_user("admin")
        prodi_id = uuid.uuid4()
        d1 = _make_dosen("DSN001", homebase_prodi_id=prodi_id)

        app.dependency_overrides[get_db] = _db_override(user, query_result=[d1])
        try:
            client = TestClient(app)
            resp = client.get(f"/dosen?homebase_prodi_id={prodi_id}", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_filter_by_status_aktif(self):
        user = _make_user("admin")
        d1 = _make_dosen("DSN001", status="Aktif")

        app.dependency_overrides[get_db] = _db_override(user, query_result=[d1])
        try:
            client = TestClient(app)
            resp = client.get("/dosen?status=Aktif", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["status"] == "Aktif"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_filter_by_status_non_aktif(self):
        user = _make_user("admin")
        d1 = _make_dosen("DSN002", status="Non-Aktif")

        app.dependency_overrides[get_db] = _db_override(user, query_result=[d1])
        try:
            client = TestClient(app)
            resp = client.get("/dosen?status=Non-Aktif", headers=_auth_header(user))
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_returns_empty_list_when_no_dosen(self):
        user = _make_user("admin")
        app.dependency_overrides[get_db] = _db_override(user, query_result=[])
        try:
            client = TestClient(app)
            resp = client.get("/dosen", headers=_auth_header(user))
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /dosen
# ---------------------------------------------------------------------------

class TestCreateDosen:
    _payload = {
        "kode": "DSN001",
        "nama": "Dr. Budi Santoso",
        "nidn": "1234567890",
        "jabfung": "Lektor",
        "status": "Aktif",
    }

    def test_admin_can_create_dosen(self):
        user = _make_user("admin")
        new_dosen = _make_dosen(**{k: v for k, v in self._payload.items()})

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None  # no duplicate

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_dosen.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/dosen", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_gets_403(self):
        for role in ("dosen", "koordinator_prodi", "tendik_prodi", "ketua_jurusan"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.post("/dosen", json=self._payload, headers=_auth_header(user))
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_duplicate_kode_returns_409(self):
        user = _make_user("admin")
        existing = _make_dosen(kode="DSN001")

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
            resp = client.post("/dosen", json=self._payload, headers=_auth_header(user))
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/dosen", json=self._payload)
        assert resp.status_code in (401, 403)

    def test_optional_fields_nullable(self):
        """POST with only required fields (kode, nama) should succeed."""
        user = _make_user("admin")
        new_dosen = _make_dosen(kode="DSN099", nama="Dosen Baru")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = None

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", new_dosen.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post("/dosen", json={"kode": "DSN099", "nama": "Dosen Baru"}, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# PUT /dosen/{id}
# ---------------------------------------------------------------------------

class TestUpdateDosen:
    def test_admin_can_update_dosen(self):
        user = _make_user("admin")
        dosen_id = uuid.uuid4()
        existing = _make_dosen(kode="DSN001")
        existing.id = dosen_id

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
                f"/dosen/{dosen_id}",
                json={"jabfung": "Lektor Kepala"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_gets_403(self):
        dosen_id = uuid.uuid4()
        for role in ("dosen", "koordinator_prodi", "tendik_prodi"):
            user = _make_user(role)
            app.dependency_overrides[get_db] = _db_override(user)
            try:
                client = TestClient(app)
                resp = client.put(
                    f"/dosen/{dosen_id}",
                    json={"jabfung": "Lektor"},
                    headers=_auth_header(user),
                )
                assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
            finally:
                app.dependency_overrides.pop(get_db, None)

    def test_not_found_returns_404(self):
        user = _make_user("admin")
        dosen_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/dosen/{dosen_id}",
                json={"jabfung": "Lektor"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_update_status_to_pensiun(self):
        user = _make_user("admin")
        dosen_id = uuid.uuid4()
        existing = _make_dosen(status="Aktif")
        existing.id = dosen_id

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else existing
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/dosen/{dosen_id}",
                json={"status": "Pensiun"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert existing.status == "Pensiun"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_duplicate_kode_on_update_returns_409(self):
        user = _make_user("admin")
        dosen_id = uuid.uuid4()
        existing = _make_dosen(kode="DSN001")
        existing.id = dosen_id
        other_dosen = _make_dosen(kode="DSN002")

        def _override():
            mock_filter = MagicMock()
            mock_filter.first.return_value = other_dosen  # kode conflict

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
                f"/dosen/{dosen_id}",
                json={"kode": "DSN002"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Helpers for unavailability tests
# ---------------------------------------------------------------------------

from app.models.dosen import DosenUnavailability as DosenUnavailabilityModel
from app.models.timeslot import Timeslot as TimeslotModel
from app.models.sesi_jadwal import SesiJadwal as SesiJadwalModel


def _make_timeslot() -> MagicMock:
    ts = MagicMock(spec=TimeslotModel)
    ts.id = uuid.uuid4()
    ts.kode = "mon_s1"
    ts.hari = "Senin"
    ts.sesi = 1
    ts.jam_mulai = "07:30:00"
    ts.jam_selesai = "10:00:00"
    ts.label = "Senin Sesi 1"
    return ts


def _make_sesi() -> MagicMock:
    sesi = MagicMock(spec=SesiJadwalModel)
    sesi.id = uuid.uuid4()
    sesi.nama = "Ganjil 2024/2025"
    sesi.semester = "Ganjil"
    sesi.tahun_akademik = "2024/2025"
    return sesi


def _make_unavailability(dosen_id: uuid.UUID, timeslot_id: uuid.UUID, sesi_id=None) -> MagicMock:
    u = MagicMock(spec=DosenUnavailabilityModel)
    u.id = uuid.uuid4()
    u.dosen_id = dosen_id
    u.timeslot_id = timeslot_id
    u.sesi_id = sesi_id
    u.catatan = None
    u.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    u.timeslot = None
    u.sesi = None
    return u


# ---------------------------------------------------------------------------
# GET /dosen/{id}/unavailability
# ---------------------------------------------------------------------------

class TestGetDosenUnavailability:
    def test_admin_can_list_unavailability(self):
        user = _make_user("admin")
        dosen = _make_dosen()
        ts = _make_timeslot()
        unavail = _make_unavailability(dosen.id, ts.id)

        def _override():
            mock_filter = MagicMock()
            mock_filter.filter.return_value = mock_filter
            mock_filter.all.return_value = [unavail]

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/dosen/{dosen.id}/unavailability", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["dosen_id"] == str(dosen.id)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_can_access_own_unavailability(self):
        user = _make_user("dosen")
        dosen = _make_dosen()
        dosen.user_id = user.id  # same user
        ts = _make_timeslot()
        unavail = _make_unavailability(dosen.id, ts.id)

        def _override():
            mock_filter = MagicMock()
            mock_filter.filter.return_value = mock_filter
            mock_filter.all.return_value = [unavail]

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/dosen/{dosen.id}/unavailability", headers=_auth_header(user))
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_cannot_access_other_dosen_unavailability(self):
        user = _make_user("dosen")
        other_dosen = _make_dosen()
        other_dosen.user_id = uuid.uuid4()  # different user

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else other_dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/dosen/{other_dosen.id}/unavailability", headers=_auth_header(user))
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_returns_404_for_unknown_dosen(self):
        user = _make_user("admin")

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/dosen/{uuid.uuid4()}/unavailability", headers=_auth_header(user))
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /dosen/{id}/unavailability
# ---------------------------------------------------------------------------

class TestPostDosenUnavailability:
    def test_admin_can_add_unavailability(self):
        user = _make_user("admin")
        dosen = _make_dosen()
        ts = _make_timeslot()
        unavail = _make_unavailability(dosen.id, ts.id)

        def _override():
            db = MagicMock()

            def _get(model, pk):
                if model.__name__ == "User":
                    return user
                if model.__name__ == "Dosen":
                    return dosen
                if model.__name__ == "Timeslot":
                    return ts
                return None

            db.get.side_effect = _get
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", unavail.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            payload = {"timeslot_id": str(ts.id)}
            resp = client.post(f"/dosen/{dosen.id}/unavailability", json=payload, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_duplicate_returns_409(self):
        from sqlalchemy.exc import IntegrityError as SAIntegrityError

        user = _make_user("admin")
        dosen = _make_dosen()
        ts = _make_timeslot()

        def _override():
            db = MagicMock()

            def _get(model, pk):
                if model.__name__ == "User":
                    return user
                if model.__name__ == "Dosen":
                    return dosen
                if model.__name__ == "Timeslot":
                    return ts
                return None

            db.get.side_effect = _get
            db.commit.side_effect = SAIntegrityError("duplicate", {}, None)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            payload = {"timeslot_id": str(ts.id)}
            resp = client.post(f"/dosen/{dosen.id}/unavailability", json=payload, headers=_auth_header(user))
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_can_add_own_unavailability(self):
        user = _make_user("dosen")
        dosen = _make_dosen()
        dosen.user_id = user.id  # own
        ts = _make_timeslot()
        unavail = _make_unavailability(dosen.id, ts.id)

        def _override():
            db = MagicMock()

            def _get(model, pk):
                if model.__name__ == "User":
                    return user
                if model.__name__ == "Dosen":
                    return dosen
                if model.__name__ == "Timeslot":
                    return ts
                return None

            db.get.side_effect = _get
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", unavail.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            payload = {"timeslot_id": str(ts.id)}
            resp = client.post(f"/dosen/{dosen.id}/unavailability", json=payload, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_cannot_add_unavailability_for_other_dosen(self):
        user = _make_user("dosen")
        other_dosen = _make_dosen()
        other_dosen.user_id = uuid.uuid4()  # different user
        ts = _make_timeslot()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else other_dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            payload = {"timeslot_id": str(ts.id)}
            resp = client.post(f"/dosen/{other_dosen.id}/unavailability", json=payload, headers=_auth_header(user))
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unknown_timeslot_returns_404(self):
        user = _make_user("admin")
        dosen = _make_dosen()

        def _override():
            db = MagicMock()

            def _get(model, pk):
                if model.__name__ == "User":
                    return user
                if model.__name__ == "Dosen":
                    return dosen
                return None  # timeslot not found

            db.get.side_effect = _get
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            payload = {"timeslot_id": str(uuid.uuid4())}
            resp = client.post(f"/dosen/{dosen.id}/unavailability", json=payload, headers=_auth_header(user))
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Helpers for preference tests
# ---------------------------------------------------------------------------

from app.models.dosen import DosenPreference as DosenPreferenceModel


def _make_preference(
    dosen_id: uuid.UUID,
    sesi_id: uuid.UUID,
    timeslot_id: uuid.UUID,
    fase: str = "pre_schedule",
) -> MagicMock:
    pref = MagicMock(spec=DosenPreferenceModel)
    pref.id = uuid.uuid4()
    pref.dosen_id = dosen_id
    pref.sesi_id = sesi_id
    pref.timeslot_id = timeslot_id
    pref.fase = fase
    pref.catatan = None
    pref.is_violated = False
    pref.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return pref


# ---------------------------------------------------------------------------
# GET /dosen/{id}/preferences
# ---------------------------------------------------------------------------

class TestGetDosenPreferences:
    def test_admin_can_list_preferences(self):
        user = _make_user("admin")
        dosen = _make_dosen()
        sesi = _make_sesi()
        ts = _make_timeslot()
        pref = _make_preference(dosen.id, sesi.id, ts.id)

        def _override():
            mock_filter = MagicMock()
            mock_filter.filter.return_value = mock_filter
            mock_filter.all.return_value = [pref]

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/dosen/{dosen.id}/preferences", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["dosen_id"] == str(dosen.id)
            assert data[0]["fase"] == "pre_schedule"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_can_access_own_preferences(self):
        user = _make_user("dosen")
        dosen = _make_dosen()
        dosen.user_id = user.id
        sesi = _make_sesi()
        ts = _make_timeslot()
        pref = _make_preference(dosen.id, sesi.id, ts.id)

        def _override():
            mock_filter = MagicMock()
            mock_filter.filter.return_value = mock_filter
            mock_filter.all.return_value = [pref]

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/dosen/{dosen.id}/preferences", headers=_auth_header(user))
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_cannot_access_other_dosen_preferences(self):
        user = _make_user("dosen")
        other_dosen = _make_dosen()
        other_dosen.user_id = uuid.uuid4()  # different user

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else other_dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/dosen/{other_dosen.id}/preferences", headers=_auth_header(user))
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_returns_404_for_unknown_dosen(self):
        user = _make_user("admin")

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/dosen/{uuid.uuid4()}/preferences", headers=_auth_header(user))
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_filter_by_fase(self):
        user = _make_user("admin")
        dosen = _make_dosen()
        sesi = _make_sesi()
        ts = _make_timeslot()
        pref = _make_preference(dosen.id, sesi.id, ts.id, fase="post_draft")

        def _override():
            mock_filter = MagicMock()
            mock_filter.filter.return_value = mock_filter
            mock_filter.all.return_value = [pref]

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_filter

            db = MagicMock()
            db.query.return_value = mock_query
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/dosen/{dosen.id}/preferences?fase=post_draft", headers=_auth_header(user))
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /dosen/{id}/preferences
# ---------------------------------------------------------------------------

class TestPostDosenPreferences:
    def test_admin_can_create_preference(self):
        user = _make_user("admin")
        dosen = _make_dosen()
        sesi = _make_sesi()
        ts = _make_timeslot()
        pref = _make_preference(dosen.id, sesi.id, ts.id)

        def _override():
            db = MagicMock()

            def _get(model, pk):
                if model.__name__ == "User":
                    return user
                if model.__name__ == "Dosen":
                    return dosen
                if model.__name__ == "SesiJadwal":
                    return sesi
                if model.__name__ == "Timeslot":
                    return ts
                return None

            db.get.side_effect = _get
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", pref.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            payload = {
                "sesi_id": str(sesi.id),
                "timeslot_id": str(ts.id),
                "fase": "pre_schedule",
            }
            resp = client.post(f"/dosen/{dosen.id}/preferences", json=payload, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_can_create_own_preference(self):
        user = _make_user("dosen")
        dosen = _make_dosen()
        dosen.user_id = user.id
        sesi = _make_sesi()
        ts = _make_timeslot()
        pref = _make_preference(dosen.id, sesi.id, ts.id)

        def _override():
            db = MagicMock()

            def _get(model, pk):
                if model.__name__ == "User":
                    return user
                if model.__name__ == "Dosen":
                    return dosen
                if model.__name__ == "SesiJadwal":
                    return sesi
                if model.__name__ == "Timeslot":
                    return ts
                return None

            db.get.side_effect = _get
            db.refresh.side_effect = lambda obj: setattr(obj, "__dict__", pref.__dict__)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            payload = {
                "sesi_id": str(sesi.id),
                "timeslot_id": str(ts.id),
                "fase": "pre_schedule",
            }
            resp = client.post(f"/dosen/{dosen.id}/preferences", json=payload, headers=_auth_header(user))
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_cannot_create_preference_for_other_dosen(self):
        user = _make_user("dosen")
        other_dosen = _make_dosen()
        other_dosen.user_id = uuid.uuid4()
        sesi = _make_sesi()
        ts = _make_timeslot()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else other_dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            payload = {
                "sesi_id": str(sesi.id),
                "timeslot_id": str(ts.id),
                "fase": "pre_schedule",
            }
            resp = client.post(f"/dosen/{other_dosen.id}/preferences", json=payload, headers=_auth_header(user))
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_duplicate_returns_409(self):
        from sqlalchemy.exc import IntegrityError as SAIntegrityError

        user = _make_user("admin")
        dosen = _make_dosen()
        sesi = _make_sesi()
        ts = _make_timeslot()

        def _override():
            db = MagicMock()

            def _get(model, pk):
                if model.__name__ == "User":
                    return user
                if model.__name__ == "Dosen":
                    return dosen
                if model.__name__ == "SesiJadwal":
                    return sesi
                if model.__name__ == "Timeslot":
                    return ts
                return None

            db.get.side_effect = _get
            db.commit.side_effect = SAIntegrityError("duplicate", {}, None)
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            payload = {
                "sesi_id": str(sesi.id),
                "timeslot_id": str(ts.id),
                "fase": "pre_schedule",
            }
            resp = client.post(f"/dosen/{dosen.id}/preferences", json=payload, headers=_auth_header(user))
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_invalid_fase_returns_422(self):
        user = _make_user("admin")
        dosen = _make_dosen()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            payload = {
                "sesi_id": str(uuid.uuid4()),
                "timeslot_id": str(uuid.uuid4()),
                "fase": "invalid_fase",
            }
            resp = client.post(f"/dosen/{dosen.id}/preferences", json=payload, headers=_auth_header(user))
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# PUT /dosen/{id}/preferences/{pid}
# ---------------------------------------------------------------------------

class TestPutDosenPreferences:
    def test_admin_can_update_preference(self):
        user = _make_user("admin")
        dosen = _make_dosen()
        sesi = _make_sesi()
        ts = _make_timeslot()
        pref = _make_preference(dosen.id, sesi.id, ts.id)

        def _override():
            db = MagicMock()

            def _get(model, pk):
                if model.__name__ == "User":
                    return user
                if model.__name__ == "Dosen":
                    return dosen
                if model.__name__ == "DosenPreference":
                    return pref
                return None

            db.get.side_effect = _get
            db.refresh.side_effect = lambda obj: None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/dosen/{dosen.id}/preferences/{pref.id}",
                json={"catatan": "Lebih suka pagi"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_preference_not_found_returns_404(self):
        user = _make_user("admin")
        dosen = _make_dosen()

        def _override():
            db = MagicMock()

            def _get(model, pk):
                if model.__name__ == "User":
                    return user
                if model.__name__ == "Dosen":
                    return dosen
                return None  # preference not found

            db.get.side_effect = _get
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/dosen/{dosen.id}/preferences/{uuid.uuid4()}",
                json={"catatan": "test"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_cannot_update_other_dosen_preference(self):
        user = _make_user("dosen")
        other_dosen = _make_dosen()
        other_dosen.user_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else other_dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/dosen/{other_dosen.id}/preferences/{uuid.uuid4()}",
                json={"catatan": "test"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# DELETE /dosen/{id}/preferences/{pid}
# ---------------------------------------------------------------------------

class TestDeleteDosenPreferences:
    def test_admin_can_delete_preference(self):
        user = _make_user("admin")
        dosen = _make_dosen()
        sesi = _make_sesi()
        ts = _make_timeslot()
        pref = _make_preference(dosen.id, sesi.id, ts.id)

        def _override():
            db = MagicMock()

            def _get(model, pk):
                if model.__name__ == "User":
                    return user
                if model.__name__ == "Dosen":
                    return dosen
                if model.__name__ == "DosenPreference":
                    return pref
                return None

            db.get.side_effect = _get
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/dosen/{dosen.id}/preferences/{pref.id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_preference_not_found_returns_404(self):
        user = _make_user("admin")
        dosen = _make_dosen()

        def _override():
            db = MagicMock()

            def _get(model, pk):
                if model.__name__ == "User":
                    return user
                if model.__name__ == "Dosen":
                    return dosen
                return None

            db.get.side_effect = _get
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/dosen/{dosen.id}/preferences/{uuid.uuid4()}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_cannot_delete_other_dosen_preference(self):
        user = _make_user("dosen")
        other_dosen = _make_dosen()
        other_dosen.user_id = uuid.uuid4()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else other_dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/dosen/{other_dosen.id}/preferences/{uuid.uuid4()}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_editor_role_gets_403(self):
        user = _make_user("ketua_jurusan")
        dosen = _make_dosen()

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else dosen
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/dosen/{dosen.id}/preferences/{uuid.uuid4()}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)
