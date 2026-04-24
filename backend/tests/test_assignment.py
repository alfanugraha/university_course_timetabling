"""
backend/tests/test_assignment.py
Unit tests for GET /sesi/{id}/assignments endpoint.

Covers:
  - Admin sees all assignments
  - koordinator_prodi sees only own prodi
  - dosen sees only own assignments
  - filter by hari
  - filter by semester
  - pagination
"""

import uuid
from datetime import datetime, time, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_token
from app.database import get_db
from app.main import app
from app.models.dosen import Dosen as DosenModel
from app.models.jadwal_assignment import JadwalAssignment as AssignmentModel
from app.models.kurikulum import Kurikulum as KurikulumModel
from app.models.mata_kuliah import MataKuliah as MataKuliahModel, MataKuliahKelas as MkKelasModel
from app.models.prodi import Prodi as ProdiModel
from app.models.ruang import Ruang as RuangModel
from app.models.sesi_jadwal import SesiJadwal as SesiJadwalModel
from app.models.timeslot import Timeslot as TimeslotModel
from app.models.user import User as UserModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(role: str = "admin", prodi_id=None) -> MagicMock:
    user = MagicMock(spec=UserModel)
    user.id = uuid.uuid4()
    user.username = f"user_{role}"
    user.role = role
    user.is_active = True
    user.prodi_id = prodi_id
    return user


def _token(user: MagicMock) -> str:
    return create_token({"sub": str(user.id), "role": user.role})


def _auth_header(user: MagicMock) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


def _make_prodi(prodi_id=None) -> MagicMock:
    prodi = MagicMock(spec=ProdiModel)
    prodi.id = prodi_id or uuid.uuid4()
    prodi.kode = "MTK"
    prodi.nama = "S1 Matematika"
    prodi.singkat = "MTK"
    return prodi


def _make_timeslot(hari: str = "Senin", sesi: int = 1) -> MagicMock:
    ts = MagicMock(spec=TimeslotModel)
    ts.id = uuid.uuid4()
    ts.kode = f"mon_s{sesi}"
    ts.hari = hari
    ts.sesi = sesi
    ts.jam_mulai = time(7, 30)
    ts.jam_selesai = time(10, 0)
    ts.label = f"{hari} Sesi {sesi}"
    return ts


def _make_mk_kelas(prodi: MagicMock, semester: int = 1, sks: int = 3) -> MagicMock:
    kurikulum = MagicMock(spec=KurikulumModel)
    kurikulum.id = uuid.uuid4()
    kurikulum.prodi_id = prodi.id
    kurikulum.prodi = prodi

    mk = MagicMock(spec=MataKuliahModel)
    mk.id = uuid.uuid4()
    mk.kode = "MAT101"
    mk.nama = "Kalkulus I"
    mk.semester = semester
    mk.sks = sks
    mk.kurikulum = kurikulum

    mk_kelas = MagicMock(spec=MkKelasModel)
    mk_kelas.id = uuid.uuid4()
    mk_kelas.label = "Kalkulus I - A"
    mk_kelas.kelas = "A"
    mk_kelas.mata_kuliah = mk
    return mk_kelas


def _make_dosen(user_id=None) -> MagicMock:
    dosen = MagicMock(spec=DosenModel)
    dosen.id = uuid.uuid4()
    dosen.kode = "D001"
    dosen.nama = "Dr. Budi"
    dosen.user_id = user_id
    return dosen


def _make_assignment(
    sesi_id: uuid.UUID,
    mk_kelas: MagicMock,
    dosen1: MagicMock,
    timeslot: MagicMock,
    dosen2: MagicMock = None,
    ruang: MagicMock = None,
) -> MagicMock:
    a = MagicMock(spec=AssignmentModel)
    a.id = uuid.uuid4()
    a.sesi_id = sesi_id
    a.mk_kelas_id = mk_kelas.id
    a.mk_kelas = mk_kelas
    a.dosen1_id = dosen1.id
    a.dosen1 = dosen1
    a.dosen2_id = dosen2.id if dosen2 else None
    a.dosen2 = dosen2
    a.timeslot_id = timeslot.id
    a.timeslot = timeslot
    a.ruang_id = ruang.id if ruang else None
    a.ruang = ruang
    a.override_floor_priority = False
    a.catatan = None
    a.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return a


def _make_sesi() -> MagicMock:
    sesi = MagicMock(spec=SesiJadwalModel)
    sesi.id = uuid.uuid4()
    sesi.nama = "Genap 2025-2026"
    sesi.semester = "Genap"
    sesi.tahun_akademik = "2025-2026"
    sesi.status = "Draft"
    sesi.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return sesi


# ---------------------------------------------------------------------------
# DB mock builder
# ---------------------------------------------------------------------------

def _make_db(user: MagicMock, sesi: MagicMock, assignments: list, dosen_for_user=None):
    """
    Build a DB mock that:
    - db.get(User, id) → user
    - db.get(SesiJadwal, id) → sesi
    - db.query(...) chain → returns assignments (with count and pagination)
    """
    def _override():
        db = MagicMock()

        def _get(model, pk):
            if model.__name__ == "User":
                return user
            if model.__name__ == "SesiJadwal":
                return sesi
            return None

        db.get.side_effect = _get

        # Build a chainable query mock
        mock_q = _build_query_chain(assignments, dosen_for_user=dosen_for_user, db=db)
        db.query.return_value = mock_q

        yield db

    return _override


def _build_query_chain(assignments: list, dosen_for_user=None, db=None):
    """Build a mock query chain that supports join/filter/count/offset/limit/all/order_by."""

    # We track the filtered assignments through the chain
    state = {"items": list(assignments)}

    mock_q = MagicMock()

    def _join(*args, **kwargs):
        return mock_q

    def _filter(*args, **kwargs):
        # We don't actually filter in the mock — tests control the list directly
        return mock_q

    def _order_by(*args, **kwargs):
        return mock_q

    def _count():
        return len(state["items"])

    def _offset(n):
        state["_offset"] = n
        return mock_q

    def _limit(n):
        state["_limit"] = n
        return mock_q

    def _all():
        offset = state.get("_offset", 0)
        limit = state.get("_limit", len(state["items"]))
        return state["items"][offset: offset + limit]

    # For dosen query (db.query(Dosen).filter(...).first())
    dosen_q = MagicMock()
    dosen_q.filter.return_value = dosen_q
    dosen_q.first.return_value = dosen_for_user

    mock_q.join.side_effect = _join
    mock_q.filter.side_effect = _filter
    mock_q.order_by.side_effect = _order_by
    mock_q.count.side_effect = _count
    mock_q.offset.side_effect = _offset
    mock_q.limit.side_effect = _limit
    mock_q.all.side_effect = _all

    # db.query dispatch: Dosen → dosen_q, else → mock_q
    if db is not None:
        original_query = db.query.side_effect

        def _query(model, *args, **kwargs):
            if hasattr(model, "__name__") and model.__name__ == "Dosen":
                return dosen_q
            return mock_q

        db.query.side_effect = _query

    return mock_q


# ---------------------------------------------------------------------------
# Tests: list_assignments
# ---------------------------------------------------------------------------

class TestListAssignmentsAdmin:
    def test_admin_sees_all_assignments(self):
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        a1 = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        a2 = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_db(user, sesi, [a1, a2])
        try:
            client = TestClient(app)
            resp = client.get(f"/sesi/{sesi.id}/assignments", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_response_has_pagination_fields(self):
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        a1 = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_db(user, sesi, [a1])
        try:
            client = TestClient(app)
            resp = client.get(f"/sesi/{sesi.id}/assignments?page=1&page_size=10", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert "total" in data
            assert "page" in data
            assert "page_size" in data
            assert "items" in data
            assert data["page"] == 1
            assert data["page_size"] == 10
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_401_or_403(self):
        sesi_id = uuid.uuid4()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(f"/sesi/{sesi_id}/assignments")
        assert resp.status_code in (401, 403)

    def test_sesi_not_found_returns_404(self):
        user = _make_user("admin")

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.get(f"/sesi/{uuid.uuid4()}/assignments", headers=_auth_header(user))
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestListAssignmentsKoordinatorProdi:
    def test_koordinator_prodi_sees_only_own_prodi(self):
        """koordinator_prodi with prodi_id set should only see assignments for that prodi."""
        prodi_id = uuid.uuid4()
        user = _make_user("koordinator_prodi", prodi_id=prodi_id)
        sesi = _make_sesi()
        prodi = _make_prodi(prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()

        # Only 1 assignment for own prodi
        a1 = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_db(user, sesi, [a1])
        try:
            client = TestClient(app)
            resp = client.get(f"/sesi/{sesi.id}/assignments", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_koordinator_prodi_without_prodi_id_returns_empty(self):
        """koordinator_prodi with no prodi_id should get empty list."""
        user = _make_user("koordinator_prodi", prodi_id=None)
        sesi = _make_sesi()

        app.dependency_overrides[get_db] = _make_db(user, sesi, [])
        try:
            client = TestClient(app)
            resp = client.get(f"/sesi/{sesi.id}/assignments", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 0
            assert data["items"] == []
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_prodi_sees_only_own_prodi(self):
        """tendik_prodi behaves same as koordinator_prodi."""
        prodi_id = uuid.uuid4()
        user = _make_user("tendik_prodi", prodi_id=prodi_id)
        sesi = _make_sesi()
        prodi = _make_prodi(prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        a1 = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_db(user, sesi, [a1])
        try:
            client = TestClient(app)
            resp = client.get(f"/sesi/{sesi.id}/assignments", headers=_auth_header(user))
            assert resp.status_code == 200
            assert resp.json()["total"] == 1
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestListAssignmentsDosen:
    def test_dosen_sees_only_own_assignments(self):
        """dosen role should only see assignments where they are dosen1 or dosen2."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)

        # Dosen linked to this user
        dosen = _make_dosen(user_id=user.id)
        a1 = _make_assignment(sesi.id, mk_kelas, dosen, ts)

        app.dependency_overrides[get_db] = _make_db(user, sesi, [a1], dosen_for_user=dosen)
        try:
            client = TestClient(app)
            resp = client.get(f"/sesi/{sesi.id}/assignments", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_without_linked_record_returns_empty(self):
        """dosen with no Dosen record linked should get empty list."""
        user = _make_user("dosen")
        sesi = _make_sesi()

        app.dependency_overrides[get_db] = _make_db(user, sesi, [], dosen_for_user=None)
        try:
            client = TestClient(app)
            resp = client.get(f"/sesi/{sesi.id}/assignments", headers=_auth_header(user))
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 0
            assert data["items"] == []
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestListAssignmentsFilters:
    def test_filter_by_hari(self):
        """Filter by hari should return only assignments on that day."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts_senin = _make_timeslot(hari="Senin")
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        a1 = _make_assignment(sesi.id, mk_kelas, dosen1, ts_senin)

        app.dependency_overrides[get_db] = _make_db(user, sesi, [a1])
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments?hari=Senin",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["items"][0]["timeslot"]["hari"] == "Senin"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_filter_by_semester(self):
        """Filter by semester should return only assignments for that semester."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas_sem1 = _make_mk_kelas(prodi, semester=1)
        dosen1 = _make_dosen()
        a1 = _make_assignment(sesi.id, mk_kelas_sem1, dosen1, ts)

        app.dependency_overrides[get_db] = _make_db(user, sesi, [a1])
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments?semester=1",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["items"][0]["mk_kelas"]["semester"] == 1
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_filter_by_prodi_id(self):
        """Filter by prodi_id should return only assignments for that prodi."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi_id = uuid.uuid4()
        prodi = _make_prodi(prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        a1 = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_db(user, sesi, [a1])
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments?prodi_id={prodi_id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestListAssignmentsPagination:
    def test_pagination_page_and_page_size(self):
        """Pagination: page=1, page_size=2 should return first 2 items."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()

        assignments = [_make_assignment(sesi.id, mk_kelas, dosen1, ts) for _ in range(5)]

        app.dependency_overrides[get_db] = _make_db(user, sesi, assignments)
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments?page=1&page_size=2",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 5
            assert len(data["items"]) == 2
            assert data["page"] == 1
            assert data["page_size"] == 2
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_pagination_second_page(self):
        """Pagination: page=2, page_size=2 should return items 3-4."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()

        assignments = [_make_assignment(sesi.id, mk_kelas, dosen1, ts) for _ in range(5)]

        app.dependency_overrides[get_db] = _make_db(user, sesi, assignments)
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments?page=2&page_size=2",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 5
            assert len(data["items"]) == 2
            assert data["page"] == 2
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_pagination_last_page_partial(self):
        """Pagination: last page may have fewer items than page_size."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()

        assignments = [_make_assignment(sesi.id, mk_kelas, dosen1, ts) for _ in range(5)]

        app.dependency_overrides[get_db] = _make_db(user, sesi, assignments)
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments?page=3&page_size=2",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 5
            assert len(data["items"]) == 1  # only 1 item on page 3
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestListAssignmentsRoleAccess:
    def test_ketua_jurusan_sees_all(self):
        """ketua_jurusan should see all assignments (no prodi filter)."""
        user = _make_user("ketua_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignments = [_make_assignment(sesi.id, mk_kelas, dosen1, ts) for _ in range(3)]

        app.dependency_overrides[get_db] = _make_db(user, sesi, assignments)
        try:
            client = TestClient(app)
            resp = client.get(f"/sesi/{sesi.id}/assignments", headers=_auth_header(user))
            assert resp.status_code == 200
            assert resp.json()["total"] == 3
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_sekretaris_jurusan_sees_all(self):
        user = _make_user("sekretaris_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignments = [_make_assignment(sesi.id, mk_kelas, dosen1, ts) for _ in range(2)]

        app.dependency_overrides[get_db] = _make_db(user, sesi, assignments)
        try:
            client = TestClient(app)
            resp = client.get(f"/sesi/{sesi.id}/assignments", headers=_auth_header(user))
            assert resp.status_code == 200
            assert resp.json()["total"] == 2
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_jurusan_sees_all(self):
        user = _make_user("tendik_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignments = [_make_assignment(sesi.id, mk_kelas, dosen1, ts) for _ in range(2)]

        app.dependency_overrides[get_db] = _make_db(user, sesi, assignments)
        try:
            client = TestClient(app)
            resp = client.get(f"/sesi/{sesi.id}/assignments", headers=_auth_header(user))
            assert resp.status_code == 200
            assert resp.json()["total"] == 2
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Tests: create_assignment  (POST /sesi/{id}/assignments)
# ---------------------------------------------------------------------------

def _make_ruang(is_active: bool = True) -> MagicMock:
    ruang = MagicMock(spec=RuangModel)
    ruang.id = uuid.uuid4()
    ruang.nama = "R.101"
    ruang.kapasitas = 40
    ruang.lantai = 1
    ruang.gedung = "FMIPA"
    ruang.is_active = is_active
    return ruang


def _make_post_db(
    user: MagicMock,
    sesi: MagicMock,
    mk_kelas: MagicMock,
    dosen1: MagicMock,
    timeslot: MagicMock,
    dosen2: MagicMock = None,
    ruang: MagicMock = None,
    existing_assignment: MagicMock = None,
):
    """Build a DB mock for POST /sesi/{id}/assignments tests."""

    def _override():
        db = MagicMock()

        def _get(model, pk):
            name = model.__name__ if hasattr(model, "__name__") else str(model)
            if name == "User":
                return user
            if name == "SesiJadwal":
                return sesi
            if name == "MataKuliahKelas":
                return mk_kelas
            if name == "Dosen":
                if pk == dosen1.id:
                    return dosen1
                if dosen2 and pk == dosen2.id:
                    return dosen2
                return None
            if name == "Timeslot":
                return timeslot
            if name == "Ruang":
                return ruang
            return None

        db.get.side_effect = _get

        # query chain for HC-05 duplicate check
        mock_q = MagicMock()
        mock_q.filter.return_value = mock_q
        mock_q.first.return_value = existing_assignment

        db.query.return_value = mock_q

        # db.add / db.commit / db.refresh
        def _refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
            obj.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
            obj.mk_kelas = mk_kelas
            obj.dosen1 = dosen1
            obj.dosen2 = dosen2
            obj.timeslot = timeslot
            obj.ruang = ruang

        db.add.return_value = None
        db.commit.return_value = None
        db.refresh.side_effect = _refresh

        yield db

    return _override


def _post_payload(
    mk_kelas: MagicMock,
    dosen1: MagicMock,
    timeslot: MagicMock,
    dosen2: MagicMock = None,
    ruang: MagicMock = None,
) -> dict:
    payload = {
        "mk_kelas_id": str(mk_kelas.id),
        "dosen1_id": str(dosen1.id),
        "timeslot_id": str(timeslot.id),
    }
    if dosen2:
        payload["dosen2_id"] = str(dosen2.id)
    if ruang:
        payload["ruang_id"] = str(ruang.id)
    return payload


class TestCreateAssignment:
    def test_happy_path_returns_201(self):
        """Admin can create a new assignment — returns 201 with assignment data."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        app.dependency_overrides[get_db] = _make_post_db(
            user, sesi, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["mk_kelas_id"] == str(mk_kelas.id)
            assert data["dosen1_id"] == str(dosen1.id)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_sesi_not_found_returns_404(self):
        user = _make_user("admin")

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{uuid.uuid4()}/assignments",
                json={
                    "mk_kelas_id": str(uuid.uuid4()),
                    "dosen1_id": str(uuid.uuid4()),
                    "timeslot_id": str(uuid.uuid4()),
                },
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_sesi_arsip_returns_422(self):
        """Cannot add assignment to an archived sesi."""
        user = _make_user("admin")
        sesi = _make_sesi()
        sesi.status = "Arsip"
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        app.dependency_overrides[get_db] = _make_post_db(
            user, sesi, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen1_not_found_returns_404(self):
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        def _override():
            db = MagicMock()

            def _get(model, pk):
                name = model.__name__
                if name == "User":
                    return user
                if name == "SesiJadwal":
                    return sesi
                if name == "MataKuliahKelas":
                    return mk_kelas
                if name == "Dosen":
                    return None  # dosen not found
                if name == "Timeslot":
                    return ts
                return None

            db.get.side_effect = _get
            mock_q = MagicMock()
            mock_q.filter.return_value = mock_q
            mock_q.first.return_value = None
            db.query.return_value = mock_q
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen1_inactive_returns_422(self):
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Nonaktif"

        app.dependency_overrides[get_db] = _make_post_db(
            user, sesi, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_timeslot_not_found_returns_404(self):
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        def _override():
            db = MagicMock()

            def _get(model, pk):
                name = model.__name__
                if name == "User":
                    return user
                if name == "SesiJadwal":
                    return sesi
                if name == "MataKuliahKelas":
                    return mk_kelas
                if name == "Dosen":
                    return dosen1
                if name == "Timeslot":
                    return None  # not found
                return None

            db.get.side_effect = _get
            mock_q = MagicMock()
            mock_q.filter.return_value = mock_q
            mock_q.first.return_value = None
            db.query.return_value = mock_q
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_ruang_inactive_returns_422(self):
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"
        ruang = _make_ruang(is_active=False)

        app.dependency_overrides[get_db] = _make_post_db(
            user, sesi, mk_kelas, dosen1, ts, ruang=ruang
        )
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts, ruang=ruang),
                headers=_auth_header(user),
            )
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_hc05_duplicate_returns_409(self):
        """HC-05: duplicate (sesi_id, mk_kelas_id) returns 409."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"
        existing = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_post_db(
            user, sesi, mk_kelas, dosen1, ts, existing_assignment=existing
        )
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_401_or_403(self):
        sesi_id = uuid.uuid4()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            f"/sesi/{sesi_id}/assignments",
            json={
                "mk_kelas_id": str(uuid.uuid4()),
                "dosen1_id": str(uuid.uuid4()),
                "timeslot_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code in (401, 403)

    def test_dosen_role_forbidden(self):
        """dosen role is not in EDITOR_ROLES_PRODI — should get 403."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        app.dependency_overrides[get_db] = _make_post_db(
            user, sesi, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_koordinator_prodi_own_prodi_allowed(self):
        """koordinator_prodi can create assignment for their own prodi."""
        prodi_id = uuid.uuid4()
        user = _make_user("koordinator_prodi", prodi_id=prodi_id)
        sesi = _make_sesi()
        prodi = _make_prodi(prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        app.dependency_overrides[get_db] = _make_post_db(
            user, sesi, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_koordinator_prodi_other_prodi_forbidden(self):
        """koordinator_prodi cannot create assignment for a different prodi."""
        prodi_id = uuid.uuid4()
        other_prodi_id = uuid.uuid4()
        user = _make_user("koordinator_prodi", prodi_id=prodi_id)
        sesi = _make_sesi()
        other_prodi = _make_prodi(other_prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(other_prodi)  # mk belongs to other prodi
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        app.dependency_overrides[get_db] = _make_post_db(
            user, sesi, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_with_dosen2_and_ruang(self):
        """Happy path with optional dosen2 and ruang provided."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"
        dosen2 = _make_dosen()
        dosen2.status = "Aktif"
        ruang = _make_ruang(is_active=True)

        app.dependency_overrides[get_db] = _make_post_db(
            user, sesi, mk_kelas, dosen1, ts, dosen2=dosen2, ruang=ruang
        )
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts, dosen2=dosen2, ruang=ruang),
                headers=_auth_header(user),
            )
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Tests: update_assignment  (PUT /sesi/{id}/assignments/{aid})
# ---------------------------------------------------------------------------

def _make_put_db(
    user: MagicMock,
    sesi: MagicMock,
    assignment: MagicMock,
    mk_kelas: MagicMock,
    dosen1: MagicMock,
    timeslot: MagicMock,
    dosen2: MagicMock = None,
    ruang: MagicMock = None,
    duplicate_assignment: MagicMock = None,
):
    """Build a DB mock for PUT /sesi/{id}/assignments/{aid} tests."""

    def _override():
        db = MagicMock()

        def _get(model, pk):
            name = model.__name__ if hasattr(model, "__name__") else str(model)
            if name == "User":
                return user
            if name == "SesiJadwal":
                return sesi
            if name == "JadwalAssignment":
                return assignment if pk == assignment.id else None
            if name == "MataKuliahKelas":
                return mk_kelas if pk == mk_kelas.id else None
            if name == "Dosen":
                if pk == dosen1.id:
                    return dosen1
                if dosen2 and pk == dosen2.id:
                    return dosen2
                return None
            if name == "Timeslot":
                return timeslot if pk == timeslot.id else None
            if name == "Ruang":
                return ruang if (ruang and pk == ruang.id) else None
            return None

        db.get.side_effect = _get

        # query chain for HC-05 duplicate check
        mock_q = MagicMock()
        mock_q.filter.return_value = mock_q
        mock_q.first.return_value = duplicate_assignment

        db.query.return_value = mock_q

        def _refresh(obj):
            obj.updated_at = datetime(2025, 6, 1, tzinfo=timezone.utc)
            obj.mk_kelas = mk_kelas
            obj.dosen1 = dosen1
            obj.dosen2 = dosen2
            obj.timeslot = timeslot
            obj.ruang = ruang

        db.add.return_value = None
        db.commit.return_value = None
        db.refresh.side_effect = _refresh

        yield db

    return _override


class TestUpdateAssignment:
    def test_happy_path_sekretaris_jurusan(self):
        """sekretaris_jurusan can update an assignment — returns 200 with updated data."""
        user = _make_user("sekretaris_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        assignment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        new_ts = _make_timeslot(hari="Selasa", sesi=2)

        app.dependency_overrides[get_db] = _make_put_db(
            user, sesi, assignment, mk_kelas, dosen1, new_ts
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                json={"timeslot_id": str(new_ts.id), "catatan": "updated"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == str(assignment.id)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_assignment_not_found_returns_404(self):
        """Assignment id not found → 404."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        # assignment with a different id — db.get returns None for unknown id
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        assignment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        def _override():
            db = MagicMock()

            def _get(model, pk):
                name = model.__name__ if hasattr(model, "__name__") else str(model)
                if name == "User":
                    return user
                if name == "SesiJadwal":
                    return sesi
                if name == "JadwalAssignment":
                    return None  # not found
                return None

            db.get.side_effect = _get
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{uuid.uuid4()}",
                json={"catatan": "x"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_sesi_arsip_returns_400(self):
        """Cannot update assignment on an archived sesi → 400."""
        user = _make_user("admin")
        sesi = _make_sesi()
        sesi.status = "Arsip"
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        assignment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        app.dependency_overrides[get_db] = _make_put_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                json={"catatan": "x"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_koordinator_prodi_other_prodi_forbidden(self):
        """koordinator_prodi cannot update assignment belonging to a different prodi → 403."""
        prodi_id = uuid.uuid4()
        other_prodi_id = uuid.uuid4()
        user = _make_user("koordinator_prodi", prodi_id=prodi_id)
        sesi = _make_sesi()
        other_prodi = _make_prodi(other_prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(other_prodi)  # belongs to other prodi
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        assignment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        def _override():
            db = MagicMock()

            def _get(model, pk):
                name = model.__name__ if hasattr(model, "__name__") else str(model)
                if name == "User":
                    return user
                if name == "SesiJadwal":
                    return sesi
                if name == "JadwalAssignment":
                    return assignment if pk == assignment.id else None
                if name == "MataKuliahKelas":
                    return mk_kelas if pk == mk_kelas.id else None
                return None

            db.get.side_effect = _get
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                json={"catatan": "x"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Tests: toggle_override_floor_priority  (PATCH /sesi/{id}/assignments/{aid}/override-floor)
# ---------------------------------------------------------------------------

def _make_patch_floor_db(
    user: MagicMock,
    sesi: MagicMock,
    assignment: MagicMock,
    mk_kelas: MagicMock,
    dosen1: MagicMock,
    timeslot: MagicMock,
    dosen2: MagicMock = None,
    ruang: MagicMock = None,
):
    """Build a DB mock for PATCH .../override-floor tests."""

    def _override():
        db = MagicMock()

        def _get(model, pk):
            name = model.__name__ if hasattr(model, "__name__") else str(model)
            if name == "User":
                return user
            if name == "SesiJadwal":
                return sesi
            if name == "JadwalAssignment":
                return assignment if pk == assignment.id else None
            return None

        db.get.side_effect = _get

        def _refresh(obj):
            obj.mk_kelas = mk_kelas
            obj.dosen1 = dosen1
            obj.dosen2 = dosen2
            obj.timeslot = timeslot
            obj.ruang = ruang

        db.commit.return_value = None
        db.refresh.side_effect = _refresh

        yield db

    return _override


class TestToggleOverrideFloorPriority:
    def test_happy_path_toggles_false_to_true(self):
        """Admin can toggle override_floor_priority from False to True — returns 200."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        assignment.override_floor_priority = False
        assignment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        app.dependency_overrides[get_db] = _make_patch_floor_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/override-floor",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            # The assignment mock's override_floor_priority should have been toggled
            assert assignment.override_floor_priority is True
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_happy_path_toggles_true_to_false(self):
        """Toggle from True to False."""
        user = _make_user("sekretaris_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        assignment.override_floor_priority = True
        assignment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        app.dependency_overrides[get_db] = _make_patch_floor_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/override-floor",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert assignment.override_floor_priority is False
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_sesi_not_found_returns_404(self):
        user = _make_user("admin")

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{uuid.uuid4()}/assignments/{uuid.uuid4()}/override-floor",
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_assignment_not_found_returns_404(self):
        user = _make_user("admin")
        sesi = _make_sesi()

        def _override():
            db = MagicMock()

            def _get(model, pk):
                name = model.__name__
                if name == "User":
                    return user
                if name == "SesiJadwal":
                    return sesi
                return None  # assignment not found

            db.get.side_effect = _get
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi.id}/assignments/{uuid.uuid4()}/override-floor",
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_assignment_belongs_to_different_sesi_returns_404(self):
        """Assignment exists but belongs to a different sesi → 404."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        assignment.sesi_id = uuid.uuid4()  # different sesi
        assignment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        app.dependency_overrides[get_db] = _make_patch_floor_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/override-floor",
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_koordinator_prodi_role_forbidden(self):
        """koordinator_prodi is not in EDITOR_ROLES_JURUSAN → 403."""
        user = _make_user("koordinator_prodi")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        assignment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        app.dependency_overrides[get_db] = _make_patch_floor_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/override-floor",
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_role_forbidden(self):
        """dosen role is not in EDITOR_ROLES_JURUSAN → 403."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        assignment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        app.dependency_overrides[get_db] = _make_patch_floor_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/override-floor",
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_401_or_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.patch(
            f"/sesi/{uuid.uuid4()}/assignments/{uuid.uuid4()}/override-floor"
        )
        assert resp.status_code in (401, 403)

    def test_tendik_jurusan_allowed(self):
        """tendik_jurusan is in EDITOR_ROLES_JURUSAN → allowed."""
        user = _make_user("tendik_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        assignment.override_floor_priority = False
        assignment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        app.dependency_overrides[get_db] = _make_patch_floor_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.patch(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/override-floor",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Tests: delete_assignment  (DELETE /sesi/{id}/assignments/{aid})
# ---------------------------------------------------------------------------

def _make_delete_db(
    user: MagicMock,
    sesi: MagicMock,
    assignment: MagicMock | None,
):
    """Build a DB mock for DELETE /sesi/{id}/assignments/{aid} tests."""

    def _override():
        db = MagicMock()

        def _get(model, pk):
            name = model.__name__ if hasattr(model, "__name__") else str(model)
            if name == "User":
                return user
            if name == "SesiJadwal":
                return sesi
            if name == "JadwalAssignment":
                return assignment if (assignment and pk == assignment.id) else None
            return None

        db.get.side_effect = _get
        db.delete.return_value = None
        db.commit.return_value = None

        yield db

    return _override


class TestDeleteAssignment:
    def test_happy_path_returns_204(self):
        """Admin can delete an existing assignment — returns 204 No Content."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_delete_db(user, sesi, assignment)
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 204
            assert resp.content == b""
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_assignment_not_found_returns_404(self):
        """Delete non-existent assignment → 404."""
        user = _make_user("admin")
        sesi = _make_sesi()

        app.dependency_overrides[get_db] = _make_delete_db(user, sesi, None)
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/sesi/{sesi.id}/assignments/{uuid.uuid4()}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_assignment_belongs_to_different_sesi_returns_404(self):
        """Assignment exists but belongs to a different sesi → 404."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        assignment.sesi_id = uuid.uuid4()  # different sesi

        app.dependency_overrides[get_db] = _make_delete_db(user, sesi, assignment)
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_sesi_not_found_returns_404(self):
        """Sesi not found → 404."""
        user = _make_user("admin")

        def _override():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/sesi/{uuid.uuid4()}/assignments/{uuid.uuid4()}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_koordinator_prodi_role_forbidden(self):
        """koordinator_prodi is not in EDITOR_ROLES_JURUSAN → 403."""
        user = _make_user("koordinator_prodi")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_delete_db(user, sesi, assignment)
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_401_or_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.delete(
            f"/sesi/{uuid.uuid4()}/assignments/{uuid.uuid4()}"
        )
        assert resp.status_code in (401, 403)

    def test_sekretaris_jurusan_allowed(self):
        """sekretaris_jurusan is in EDITOR_ROLES_JURUSAN → allowed."""
        user = _make_user("sekretaris_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_delete_db(user, sesi, assignment)
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Tests: team teaching endpoints
# ---------------------------------------------------------------------------

from app.models.jadwal_assignment import TeamTeachingOrder as TeamTeachingOrderModel


def _make_tt_order(assignment_id: uuid.UUID, dosen_id: uuid.UUID, urutan_pra_uts: int = 1, urutan_pasca_uts=None) -> MagicMock:
    order = MagicMock(spec=TeamTeachingOrderModel)
    order.id = uuid.uuid4()
    order.assignment_id = assignment_id
    order.dosen_id = dosen_id
    order.urutan_pra_uts = urutan_pra_uts
    order.urutan_pasca_uts = urutan_pasca_uts
    order.catatan = None
    return order


def _make_tt_db(
    user: MagicMock,
    sesi: MagicMock,
    assignment: MagicMock,
    dosen_for_user: MagicMock = None,
    tt_orders: list = None,
):
    """Build a DB mock for team teaching endpoint tests."""
    if tt_orders is None:
        tt_orders = []

    def _override():
        db = MagicMock()

        def _get(model, pk):
            name = model.__name__ if hasattr(model, "__name__") else str(model)
            if name == "User":
                return user
            if name == "SesiJadwal":
                return sesi
            if name == "JadwalAssignment":
                return assignment if (assignment and pk == assignment.id) else None
            return None

        db.get.side_effect = _get

        # Build query chain that handles both Dosen and TeamTeachingOrder queries
        dosen_q = MagicMock()
        dosen_q.filter.return_value = dosen_q
        dosen_q.first.return_value = dosen_for_user

        tt_q = MagicMock()
        tt_q.filter.return_value = tt_q
        tt_q.first.return_value = None  # no existing record by default
        tt_q.all.return_value = tt_orders

        def _query(model, *args, **kwargs):
            if hasattr(model, "__name__") and model.__name__ == "Dosen":
                return dosen_q
            if hasattr(model, "__name__") and model.__name__ == "TeamTeachingOrder":
                return tt_q
            return MagicMock()

        db.query.side_effect = _query
        db.add.return_value = None
        db.commit.return_value = None

        yield db

    return _override


class TestGetTeamTeaching:
    def test_admin_can_get_team_teaching(self):
        """Admin can GET team teaching orders — returns 200 with items list."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen2 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts, dosen2=dosen2)

        order1 = _make_tt_order(assignment.id, dosen1.id, urutan_pra_uts=1)
        order2 = _make_tt_order(assignment.id, dosen2.id, urutan_pra_uts=2)

        app.dependency_overrides[get_db] = _make_tt_db(user, sesi, assignment, tt_orders=[order1, order2])
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "items" in data
            assert len(data["items"]) == 2
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_can_get_team_teaching(self):
        """Dosen role can also GET team teaching (all roles allowed)."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen(user_id=user.id)
        dosen2 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts, dosen2=dosen2)

        app.dependency_overrides[get_db] = _make_tt_db(user, sesi, assignment, tt_orders=[])
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert resp.json()["items"] == []
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_no_dosen2_returns_400(self):
        """Assignment without dosen2_id → 400 with specific message."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)  # no dosen2

        app.dependency_overrides[get_db] = _make_tt_db(user, sesi, assignment)
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching",
                headers=_auth_header(user),
            )
            assert resp.status_code == 400
            assert "dosen2_id" in resp.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_assignment_not_found_returns_404(self):
        user = _make_user("admin")
        sesi = _make_sesi()

        app.dependency_overrides[get_db] = _make_tt_db(user, sesi, None)
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments/{uuid.uuid4()}/team-teaching",
                headers=_auth_header(user),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_401_or_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            f"/sesi/{uuid.uuid4()}/assignments/{uuid.uuid4()}/team-teaching"
        )
        assert resp.status_code in (401, 403)


class TestPutTeamTeaching:
    def test_dosen_own_can_set_order(self):
        """Dosen who is dosen1 can PUT team teaching order — returns 200."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen(user_id=user.id)
        dosen2 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts, dosen2=dosen2)

        app.dependency_overrides[get_db] = _make_tt_db(
            user, sesi, assignment, dosen_for_user=dosen1, tt_orders=[]
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching",
                json={"orders": [
                    {"dosen_id": str(dosen1.id), "urutan_pra_uts": 1},
                    {"dosen_id": str(dosen2.id), "urutan_pra_uts": 2},
                ]},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert "items" in resp.json()
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen2_own_can_set_order(self):
        """Dosen who is dosen2 can also PUT team teaching order."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen2 = _make_dosen(user_id=user.id)
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts, dosen2=dosen2)

        app.dependency_overrides[get_db] = _make_tt_db(
            user, sesi, assignment, dosen_for_user=dosen2, tt_orders=[]
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching",
                json={"orders": [
                    {"dosen_id": str(dosen1.id), "urutan_pra_uts": 2},
                    {"dosen_id": str(dosen2.id), "urutan_pra_uts": 1},
                ]},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_not_in_assignment_returns_403(self):
        """Dosen who is not dosen1 or dosen2 → 403."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen2 = _make_dosen()
        other_dosen = _make_dosen(user_id=user.id)  # not in assignment
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts, dosen2=dosen2)

        app.dependency_overrides[get_db] = _make_tt_db(
            user, sesi, assignment, dosen_for_user=other_dosen
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching",
                json={"orders": [{"dosen_id": str(dosen1.id), "urutan_pra_uts": 1}]},
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_no_dosen2_returns_400(self):
        """Assignment without dosen2_id → 400."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen(user_id=user.id)
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)  # no dosen2

        app.dependency_overrides[get_db] = _make_tt_db(
            user, sesi, assignment, dosen_for_user=dosen1
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching",
                json={"orders": [{"dosen_id": str(dosen1.id), "urutan_pra_uts": 1}]},
                headers=_auth_header(user),
            )
            assert resp.status_code == 400
            assert "dosen2_id" in resp.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_dosen_role_returns_403(self):
        """Admin role cannot PUT team teaching (only dosen role allowed)."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen2 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts, dosen2=dosen2)

        app.dependency_overrides[get_db] = _make_tt_db(user, sesi, assignment)
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching",
                json={"orders": [{"dosen_id": str(dosen1.id), "urutan_pra_uts": 1}]},
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_no_linked_record_returns_403(self):
        """Dosen user with no Dosen record linked → 403."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen2 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts, dosen2=dosen2)

        app.dependency_overrides[get_db] = _make_tt_db(
            user, sesi, assignment, dosen_for_user=None  # no linked dosen
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching",
                json={"orders": [{"dosen_id": str(dosen1.id), "urutan_pra_uts": 1}]},
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestPostTeamTeachingSwap:
    def test_dosen_own_can_swap(self):
        """Dosen who is dosen1 can POST swap — returns 200."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen(user_id=user.id)
        dosen2 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts, dosen2=dosen2)

        app.dependency_overrides[get_db] = _make_tt_db(
            user, sesi, assignment, dosen_for_user=dosen1, tt_orders=[]
        )
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching/swap",
                json={"orders": [
                    {"dosen_id": str(dosen1.id), "urutan_pasca_uts": 2},
                    {"dosen_id": str(dosen2.id), "urutan_pasca_uts": 1},
                ]},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert "items" in resp.json()
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_not_in_assignment_returns_403(self):
        """Dosen not in assignment → 403 on swap."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen2 = _make_dosen()
        other_dosen = _make_dosen(user_id=user.id)
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts, dosen2=dosen2)

        app.dependency_overrides[get_db] = _make_tt_db(
            user, sesi, assignment, dosen_for_user=other_dosen
        )
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching/swap",
                json={"orders": [{"dosen_id": str(dosen1.id), "urutan_pasca_uts": 1}]},
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_no_dosen2_returns_400(self):
        """Assignment without dosen2_id → 400 on swap."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen(user_id=user.id)
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)  # no dosen2

        app.dependency_overrides[get_db] = _make_tt_db(
            user, sesi, assignment, dosen_for_user=dosen1
        )
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching/swap",
                json={"orders": [{"dosen_id": str(dosen1.id), "urutan_pasca_uts": 1}]},
                headers=_auth_header(user),
            )
            assert resp.status_code == 400
            assert "dosen2_id" in resp.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_dosen_role_returns_403(self):
        """sekretaris_jurusan cannot POST swap (only dosen role allowed)."""
        user = _make_user("sekretaris_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen2 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts, dosen2=dosen2)

        app.dependency_overrides[get_db] = _make_tt_db(user, sesi, assignment)
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments/{assignment.id}/team-teaching/swap",
                json={"orders": [{"dosen_id": str(dosen1.id), "urutan_pasca_uts": 1}]},
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_unauthenticated_returns_401_or_403(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            f"/sesi/{uuid.uuid4()}/assignments/{uuid.uuid4()}/team-teaching/swap",
            json={"orders": []},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# T3.6 — Additional RBAC and coverage tests
# ---------------------------------------------------------------------------

class TestCreateAssignmentRoleAccess:
    """T3.6: Role access tests for POST /sesi/{id}/assignments."""

    def test_ketua_jurusan_cannot_create(self):
        """ketua_jurusan is read-only — POST returns 403."""
        user = _make_user("ketua_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        app.dependency_overrides[get_db] = _make_post_db(user, sesi, mk_kelas, dosen1, ts)
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_prodi_own_prodi_allowed(self):
        """tendik_prodi can create assignment for their own prodi."""
        prodi_id = uuid.uuid4()
        user = _make_user("tendik_prodi", prodi_id=prodi_id)
        sesi = _make_sesi()
        prodi = _make_prodi(prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        app.dependency_overrides[get_db] = _make_post_db(user, sesi, mk_kelas, dosen1, ts)
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_prodi_other_prodi_forbidden(self):
        """tendik_prodi cannot create assignment for a different prodi."""
        prodi_id = uuid.uuid4()
        other_prodi_id = uuid.uuid4()
        user = _make_user("tendik_prodi", prodi_id=prodi_id)
        sesi = _make_sesi()
        other_prodi = _make_prodi(other_prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(other_prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        app.dependency_overrides[get_db] = _make_post_db(user, sesi, mk_kelas, dosen1, ts)
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_sekretaris_jurusan_can_create_any_prodi(self):
        """sekretaris_jurusan can create assignment for any prodi."""
        user = _make_user("sekretaris_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()  # any prodi
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        app.dependency_overrides[get_db] = _make_post_db(user, sesi, mk_kelas, dosen1, ts)
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_jurusan_can_create_any_prodi(self):
        """tendik_jurusan can create assignment for any prodi."""
        user = _make_user("tendik_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"

        app.dependency_overrides[get_db] = _make_post_db(user, sesi, mk_kelas, dosen1, ts)
        try:
            client = TestClient(app)
            resp = client.post(
                f"/sesi/{sesi.id}/assignments",
                json=_post_payload(mk_kelas, dosen1, ts),
                headers=_auth_header(user),
            )
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestUpdateAssignmentRoleAccess:
    """T3.6: Role access tests for PUT /sesi/{id}/assignments/{aid}."""

    def _make_assignment_for_prodi(self, prodi_id=None):
        prodi = _make_prodi(prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        dosen1.status = "Aktif"
        sesi = _make_sesi()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)
        assignment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        return sesi, prodi, ts, mk_kelas, dosen1, assignment

    def test_ketua_jurusan_cannot_update(self):
        """ketua_jurusan is read-only — PUT returns 403."""
        user = _make_user("ketua_jurusan")
        sesi, prodi, ts, mk_kelas, dosen1, assignment = self._make_assignment_for_prodi()

        app.dependency_overrides[get_db] = _make_put_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                json={"catatan": "x"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_cannot_update(self):
        """dosen role is not in EDITOR_ROLES_PRODI — PUT returns 403."""
        user = _make_user("dosen")
        sesi, prodi, ts, mk_kelas, dosen1, assignment = self._make_assignment_for_prodi()

        app.dependency_overrides[get_db] = _make_put_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                json={"catatan": "x"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_sekretaris_jurusan_can_update_any_prodi(self):
        """sekretaris_jurusan can update assignment for any prodi."""
        user = _make_user("sekretaris_jurusan")
        sesi, prodi, ts, mk_kelas, dosen1, assignment = self._make_assignment_for_prodi()

        app.dependency_overrides[get_db] = _make_put_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                json={"catatan": "updated by sekretaris"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_jurusan_can_update_any_prodi(self):
        """tendik_jurusan can update assignment for any prodi."""
        user = _make_user("tendik_jurusan")
        sesi, prodi, ts, mk_kelas, dosen1, assignment = self._make_assignment_for_prodi()

        app.dependency_overrides[get_db] = _make_put_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                json={"catatan": "updated by tendik_jurusan"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_koordinator_prodi_own_prodi_allowed(self):
        """koordinator_prodi can update assignment for their own prodi."""
        prodi_id = uuid.uuid4()
        user = _make_user("koordinator_prodi", prodi_id=prodi_id)
        sesi, prodi, ts, mk_kelas, dosen1, assignment = self._make_assignment_for_prodi(prodi_id)

        app.dependency_overrides[get_db] = _make_put_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                json={"catatan": "updated by koordinator"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_prodi_own_prodi_allowed(self):
        """tendik_prodi can update assignment for their own prodi."""
        prodi_id = uuid.uuid4()
        user = _make_user("tendik_prodi", prodi_id=prodi_id)
        sesi, prodi, ts, mk_kelas, dosen1, assignment = self._make_assignment_for_prodi(prodi_id)

        app.dependency_overrides[get_db] = _make_put_db(
            user, sesi, assignment, mk_kelas, dosen1, ts
        )
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                json={"catatan": "updated by tendik_prodi"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_prodi_other_prodi_forbidden(self):
        """tendik_prodi cannot update assignment belonging to a different prodi."""
        prodi_id = uuid.uuid4()
        other_prodi_id = uuid.uuid4()
        user = _make_user("tendik_prodi", prodi_id=prodi_id)
        sesi, other_prodi, ts, mk_kelas, dosen1, assignment = self._make_assignment_for_prodi(other_prodi_id)

        def _override():
            db = MagicMock()

            def _get(model, pk):
                name = model.__name__ if hasattr(model, "__name__") else str(model)
                if name == "User":
                    return user
                if name == "SesiJadwal":
                    return sesi
                if name == "JadwalAssignment":
                    return assignment if pk == assignment.id else None
                if name == "MataKuliahKelas":
                    return mk_kelas if pk == mk_kelas.id else None
                return None

            db.get.side_effect = _get
            yield db

        app.dependency_overrides[get_db] = _override
        try:
            client = TestClient(app)
            resp = client.put(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                json={"catatan": "x"},
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestDeleteAssignmentRoleAccess:
    """T3.6: Role access tests for DELETE /sesi/{id}/assignments/{aid}."""

    def test_ketua_jurusan_cannot_delete(self):
        """ketua_jurusan is read-only — DELETE returns 403."""
        user = _make_user("ketua_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_delete_db(user, sesi, assignment)
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_dosen_cannot_delete(self):
        """dosen role is not in EDITOR_ROLES_JURUSAN — DELETE returns 403."""
        user = _make_user("dosen")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_delete_db(user, sesi, assignment)
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_jurusan_can_delete(self):
        """tendik_jurusan is in EDITOR_ROLES_JURUSAN — DELETE returns 204."""
        user = _make_user("tendik_jurusan")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_delete_db(user, sesi, assignment)
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_prodi_cannot_delete(self):
        """tendik_prodi is not in EDITOR_ROLES_JURUSAN — DELETE returns 403."""
        user = _make_user("tendik_prodi")
        sesi = _make_sesi()
        prodi = _make_prodi()
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        assignment = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_delete_db(user, sesi, assignment)
        try:
            client = TestClient(app)
            resp = client.delete(
                f"/sesi/{sesi.id}/assignments/{assignment.id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestFilterAssignmentsByProdi:
    """T3.6: Filter assignments by prodi — role-scoped behavior."""

    def test_admin_can_filter_by_prodi_id(self):
        """Admin can explicitly filter by prodi_id query param."""
        user = _make_user("admin")
        sesi = _make_sesi()
        prodi_id = uuid.uuid4()
        prodi = _make_prodi(prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        a1 = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_db(user, sesi, [a1])
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments?prodi_id={prodi_id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["items"][0]["mk_kelas"]["prodi"]["id"] == str(prodi_id)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_koordinator_prodi_implicitly_filtered_to_own_prodi(self):
        """koordinator_prodi always sees only their own prodi assignments."""
        prodi_id = uuid.uuid4()
        user = _make_user("koordinator_prodi", prodi_id=prodi_id)
        sesi = _make_sesi()
        prodi = _make_prodi(prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        a1 = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_db(user, sesi, [a1])
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["items"][0]["mk_kelas"]["prodi"]["id"] == str(prodi_id)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_tendik_prodi_implicitly_filtered_to_own_prodi(self):
        """tendik_prodi always sees only their own prodi assignments."""
        prodi_id = uuid.uuid4()
        user = _make_user("tendik_prodi", prodi_id=prodi_id)
        sesi = _make_sesi()
        prodi = _make_prodi(prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        a1 = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_db(user, sesi, [a1])
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["items"][0]["mk_kelas"]["prodi"]["id"] == str(prodi_id)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_ketua_jurusan_can_filter_by_prodi_id(self):
        """ketua_jurusan (read-only) can GET and filter by prodi_id."""
        user = _make_user("ketua_jurusan")
        sesi = _make_sesi()
        prodi_id = uuid.uuid4()
        prodi = _make_prodi(prodi_id)
        ts = _make_timeslot()
        mk_kelas = _make_mk_kelas(prodi)
        dosen1 = _make_dosen()
        a1 = _make_assignment(sesi.id, mk_kelas, dosen1, ts)

        app.dependency_overrides[get_db] = _make_db(user, sesi, [a1])
        try:
            client = TestClient(app)
            resp = client.get(
                f"/sesi/{sesi.id}/assignments?prodi_id={prodi_id}",
                headers=_auth_header(user),
            )
            assert resp.status_code == 200
            assert resp.json()["total"] == 1
        finally:
            app.dependency_overrides.pop(get_db, None)
