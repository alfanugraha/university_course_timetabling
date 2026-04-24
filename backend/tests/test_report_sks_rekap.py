"""
backend/tests/test_report_sks_rekap.py
Unit tests for GET /sesi/{id}/reports/sks-rekap endpoint.

Covers:
  - Admin mendapat rekap SKS semua dosen
  - Breakdown per prodi key (singkat prodi atau "Layanan" untuk kategori Layanan)
  - BKD flag: no_limit, ok, near_limit, over_limit
  - Dosen2 mendapat kredit penuh SKS (tidak dibagi)
  - 404 jika sesi tidak ditemukan
  - 403 jika role tidak diizinkan (dosen)
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


def _make_sesi(sesi_id=None) -> MagicMock:
    sesi = MagicMock(spec=SesiJadwalModel)
    sesi.id = sesi_id or uuid.uuid4()
    sesi.nama = "Genap 2025-2026"
    sesi.semester = "Genap"
    sesi.tahun_akademik = "2025-2026"
    sesi.status = "Aktif"
    sesi.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return sesi


def _make_prodi(singkat: str = "S1 MTK", kategori: str = "Internal") -> MagicMock:
    prodi = MagicMock(spec=ProdiModel)
    prodi.id = uuid.uuid4()
    prodi.kode = "MTK1"
    prodi.nama = "S1 Matematika"
    prodi.singkat = singkat
    prodi.kategori = kategori
    return prodi


def _make_timeslot(sks: int = 3) -> MagicMock:
    ts = MagicMock(spec=TimeslotModel)
    ts.id = uuid.uuid4()
    ts.kode = "mon_s1"
    ts.hari = "Senin"
    ts.sesi = 1
    ts.jam_mulai = time(7, 30)
    ts.jam_selesai = time(10, 0)
    ts.label = "Senin 07:30-10:00"
    ts.sks = sks
    return ts


def _make_mk_kelas(prodi: MagicMock) -> MagicMock:
    kurikulum = MagicMock(spec=KurikulumModel)
    kurikulum.id = uuid.uuid4()
    kurikulum.prodi = prodi

    mk = MagicMock(spec=MataKuliahModel)
    mk.id = uuid.uuid4()
    mk.kode = "MAT101"
    mk.nama = "Kalkulus I"
    mk.semester = 1
    mk.sks = 3
    mk.kurikulum = kurikulum

    mk_kelas = MagicMock(spec=MkKelasModel)
    mk_kelas.id = uuid.uuid4()
    mk_kelas.label = "Kalkulus I - A"
    mk_kelas.kelas = "A"
    mk_kelas.mata_kuliah = mk
    return mk_kelas


def _make_dosen(nama: str = "Dr. Andi", kode: str = "AND", bkd_limit_sks=None) -> MagicMock:
    dosen = MagicMock(spec=DosenModel)
    dosen.id = uuid.uuid4()
    dosen.nama = nama
    dosen.kode = kode
    dosen.bkd_limit_sks = bkd_limit_sks
    return dosen


def _make_assignment(sesi_id, dosen1, dosen2=None, prodi=None, sks=3) -> MagicMock:
    if prodi is None:
        prodi = _make_prodi()
    mk_kelas = _make_mk_kelas(prodi)
    timeslot = _make_timeslot(sks=sks)

    assignment = MagicMock(spec=AssignmentModel)
    assignment.id = uuid.uuid4()
    assignment.sesi_id = sesi_id
    assignment.dosen1 = dosen1
    assignment.dosen2 = dosen2
    assignment.mk_kelas = mk_kelas
    assignment.timeslot = timeslot
    return assignment


# ---------------------------------------------------------------------------
# DB override factory
# ---------------------------------------------------------------------------

def _db_override(user: MagicMock, sesi: MagicMock, assignments: list):
    """Build a DB dependency override that returns the given sesi and assignments."""
    def _override():
        db = MagicMock()

        # db.get(SesiJadwal, sesi_id) → sesi; db.get(User, user_id) → user
        def _get(model, pk):
            if model.__name__ == "User":
                return user
            if model.__name__ == "SesiJadwal":
                return sesi
            return None

        db.get.side_effect = _get

        # db.query(...).filter(...).options(...).all() → assignments
        mock_options = MagicMock()
        mock_options.all.return_value = assignments
        mock_filter = MagicMock()
        mock_filter.options.return_value = mock_options
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_filter
        db.query.return_value = mock_query

        yield db

    return _override


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSksRekapEndpoint:

    def test_admin_gets_rekap(self):
        """Admin mendapat rekap SKS semua dosen dalam sesi."""
        user = _make_user("admin")
        sesi = _make_sesi()
        dosen = _make_dosen("Dr. Andi", "AND")
        prodi = _make_prodi("S1 MTK", "Internal")
        assignment = _make_assignment(sesi.id, dosen, prodi=prodi)

        app.dependency_overrides[get_db] = _db_override(user, sesi, [assignment])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/sks-rekap",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["sesi_id"] == str(sesi.id)
        assert data["total_dosen"] == 1
        item = data["items"][0]
        assert item["dosen_kode"] == "AND"
        assert item["total_sks"] == 3
        assert item["breakdown"] == {"S1 MTK": 3}

    def test_layanan_prodi_uses_layanan_key(self):
        """MK dengan kategori prodi 'Layanan' menggunakan key 'Layanan' di breakdown."""
        user = _make_user("admin")
        sesi = _make_sesi()
        dosen = _make_dosen("Dr. Budi", "BUD")
        prodi_layanan = _make_prodi("S1 FIS", "Layanan")
        assignment = _make_assignment(sesi.id, dosen, prodi=prodi_layanan)

        app.dependency_overrides[get_db] = _db_override(user, sesi, [assignment])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/sks-rekap",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "Layanan" in item["breakdown"]
        assert "S1 FIS" not in item["breakdown"]

    def test_dosen2_gets_full_sks_credit(self):
        """Dosen2 mendapat kredit penuh SKS (tidak dibagi dengan dosen1)."""
        user = _make_user("admin")
        sesi = _make_sesi()
        dosen1 = _make_dosen("Dr. Andi", "AND")
        dosen2 = _make_dosen("Dr. Budi", "BUD")
        prodi = _make_prodi("S1 MTK", "Internal")
        assignment = _make_assignment(sesi.id, dosen1, dosen2=dosen2, prodi=prodi, sks=3)

        app.dependency_overrides[get_db] = _db_override(user, sesi, [assignment])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/sks-rekap",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_dosen"] == 2
        # Kedua dosen masing-masing mendapat 3 SKS penuh
        sks_by_kode = {item["dosen_kode"]: item["total_sks"] for item in data["items"]}
        assert sks_by_kode["AND"] == 3
        assert sks_by_kode["BUD"] == 3

    def test_bkd_flag_no_limit(self):
        """bkd_limit_sks NULL → flag 'no_limit'."""
        user = _make_user("admin")
        sesi = _make_sesi()
        dosen = _make_dosen("Dr. Andi", "AND", bkd_limit_sks=None)
        assignment = _make_assignment(sesi.id, dosen)

        app.dependency_overrides[get_db] = _db_override(user, sesi, [assignment])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/sks-rekap",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["items"][0]["bkd_flag"] == "no_limit"

    def test_bkd_flag_ok(self):
        """total_sks < 80% bkd_limit → flag 'ok'."""
        user = _make_user("admin")
        sesi = _make_sesi()
        dosen = _make_dosen("Dr. Andi", "AND", bkd_limit_sks=12)
        # 3 SKS < 80% of 12 (9.6)
        assignment = _make_assignment(sesi.id, dosen, sks=3)

        app.dependency_overrides[get_db] = _db_override(user, sesi, [assignment])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/sks-rekap",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["items"][0]["bkd_flag"] == "ok"

    def test_bkd_flag_near_limit(self):
        """total_sks >= 80% bkd_limit tapi < limit → flag 'near_limit'."""
        user = _make_user("admin")
        sesi = _make_sesi()
        dosen = _make_dosen("Dr. Andi", "AND", bkd_limit_sks=12)
        # 10 SKS >= 80% of 12 (9.6) but < 12
        prodi = _make_prodi("S1 MTK", "Internal")
        a1 = _make_assignment(sesi.id, dosen, prodi=prodi, sks=3)
        a2 = _make_assignment(sesi.id, dosen, prodi=prodi, sks=3)
        a3 = _make_assignment(sesi.id, dosen, prodi=prodi, sks=3)
        a4 = _make_assignment(sesi.id, dosen, prodi=prodi, sks=1)
        # total = 10 SKS

        # Override timeslot sks for a4
        a4.timeslot.sks = 1

        app.dependency_overrides[get_db] = _db_override(user, sesi, [a1, a2, a3, a4])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/sks-rekap",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["items"][0]["bkd_flag"] == "near_limit"

    def test_bkd_flag_over_limit(self):
        """total_sks >= bkd_limit → flag 'over_limit'."""
        user = _make_user("admin")
        sesi = _make_sesi()
        dosen = _make_dosen("Dr. Andi", "AND", bkd_limit_sks=6)
        prodi = _make_prodi("S1 MTK", "Internal")
        # 3 + 3 + 3 = 9 SKS >= 6
        a1 = _make_assignment(sesi.id, dosen, prodi=prodi, sks=3)
        a2 = _make_assignment(sesi.id, dosen, prodi=prodi, sks=3)
        a3 = _make_assignment(sesi.id, dosen, prodi=prodi, sks=3)

        app.dependency_overrides[get_db] = _db_override(user, sesi, [a1, a2, a3])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/sks-rekap",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["items"][0]["bkd_flag"] == "over_limit"

    def test_sesi_not_found_returns_404(self):
        """Sesi tidak ditemukan → 404."""
        user = _make_user("admin")

        def _db_no_sesi():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _db_no_sesi
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{uuid.uuid4()}/reports/sks-rekap",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 404

    def test_dosen_role_forbidden(self):
        """Role 'dosen' tidak diizinkan → 403."""
        user = _make_user("dosen")
        sesi = _make_sesi()

        app.dependency_overrides[get_db] = _db_override(user, sesi, [])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/sks-rekap",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 403

    def test_koordinator_prodi_allowed(self):
        """Role 'koordinator_prodi' diizinkan mengakses endpoint."""
        user = _make_user("koordinator_prodi")
        sesi = _make_sesi()

        app.dependency_overrides[get_db] = _db_override(user, sesi, [])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/sks-rekap",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["total_dosen"] == 0

    def test_empty_sesi_returns_empty_list(self):
        """Sesi tanpa assignment → items kosong, total_dosen = 0."""
        user = _make_user("admin")
        sesi = _make_sesi()

        app.dependency_overrides[get_db] = _db_override(user, sesi, [])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/sks-rekap",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total_dosen"] == 0

    def test_multiple_prodi_breakdown(self):
        """Dosen mengajar di beberapa prodi → breakdown mencakup semua prodi."""
        user = _make_user("admin")
        sesi = _make_sesi()
        dosen = _make_dosen("Dr. Andi", "AND")
        prodi_s1 = _make_prodi("S1 MTK", "Internal")
        prodi_s2 = _make_prodi("S2 MTK", "Internal")
        prodi_layanan = _make_prodi("S1 FIS", "Layanan")

        a1 = _make_assignment(sesi.id, dosen, prodi=prodi_s1, sks=3)
        a2 = _make_assignment(sesi.id, dosen, prodi=prodi_s2, sks=3)
        a3 = _make_assignment(sesi.id, dosen, prodi=prodi_layanan, sks=3)

        app.dependency_overrides[get_db] = _db_override(user, sesi, [a1, a2, a3])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/sks-rekap",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["total_sks"] == 9
        assert item["breakdown"]["S1 MTK"] == 3
        assert item["breakdown"]["S2 MTK"] == 3
        assert item["breakdown"]["Layanan"] == 3


# ===========================================================================
# Tests for GET /sesi/{id}/reports/room-map
# ===========================================================================

from app.models.ruang import Ruang as RuangModel


def _make_ruang(nama: str, is_active: bool = True) -> MagicMock:
    ruang = MagicMock(spec=RuangModel)
    ruang.id = uuid.uuid4()
    ruang.nama = nama
    ruang.is_active = is_active
    ruang.kapasitas = 45
    return ruang


def _make_timeslot_full(kode: str, hari: str, sesi: int, label: str) -> MagicMock:
    ts = MagicMock(spec=TimeslotModel)
    ts.id = uuid.uuid4()
    ts.kode = kode
    ts.hari = hari
    ts.sesi = sesi
    ts.label = label
    ts.sks = 3
    return ts


def _make_assignment_with_ruang(sesi_id, dosen1, mk_kelas, timeslot, ruang=None) -> MagicMock:
    assignment = MagicMock(spec=AssignmentModel)
    assignment.id = uuid.uuid4()
    assignment.sesi_id = sesi_id
    assignment.dosen1 = dosen1
    assignment.dosen2 = None
    assignment.mk_kelas = mk_kelas
    assignment.timeslot = timeslot
    assignment.timeslot_id = timeslot.id
    assignment.ruang = ruang
    assignment.ruang_id = ruang.id if ruang else None
    return assignment


def _db_override_room_map(user, sesi, rooms, timeslots, assignments):
    """DB override untuk room-map: mock query untuk Ruang, Timeslot, dan JadwalAssignment."""
    def _override():
        db = MagicMock()

        def _get(model, pk):
            if model.__name__ == "User":
                return user
            if model.__name__ == "SesiJadwal":
                return sesi
            return None

        db.get.side_effect = _get

        # Kita perlu mock db.query() untuk tiga model berbeda
        # Gunakan side_effect berdasarkan argumen
        def _query(model):
            mock_q = MagicMock()
            if model is RuangModel or (hasattr(model, '__name__') and model.__name__ == 'Ruang'):
                # .filter().order_by().all() → rooms
                mock_filter = MagicMock()
                mock_order = MagicMock()
                mock_order.all.return_value = rooms
                mock_filter.order_by.return_value = mock_order
                mock_q.filter.return_value = mock_filter
            elif model is TimeslotModel or (hasattr(model, '__name__') and model.__name__ == 'Timeslot'):
                # .order_by().all() → timeslots
                mock_order = MagicMock()
                mock_order.all.return_value = timeslots
                mock_q.order_by.return_value = mock_order
            elif model is AssignmentModel or (hasattr(model, '__name__') and model.__name__ == 'JadwalAssignment'):
                # .filter(sesi_id, ruang_id.isnot(None)).options().all() → assignments
                mock_filter1 = MagicMock()
                mock_options = MagicMock()
                mock_options.all.return_value = assignments
                mock_filter1.options.return_value = mock_options
                mock_q.filter.return_value = mock_filter1
            return mock_q

        db.query.side_effect = _query
        yield db

    return _override


class TestRoomMapEndpoint:

    def _make_standard_timeslots(self):
        """Buat 15 timeslot tetap (3 sesi × 5 hari)."""
        days = [
            ("Senin", "mon"),
            ("Selasa", "tue"),
            ("Rabu", "wed"),
            ("Kamis", "thu"),
            ("Jumat", "fri"),
        ]
        slots = []
        for hari, prefix in days:
            for sesi_num in range(1, 4):
                kode = f"{prefix}_s{sesi_num}"
                label = f"{hari} Sesi {sesi_num}"
                slots.append(_make_timeslot_full(kode, hari, sesi_num, label))
        return slots

    def test_admin_gets_room_map(self):
        """Admin mendapat room-map dengan struktur yang benar."""
        user = _make_user("admin")
        sesi = _make_sesi()
        rooms = [_make_ruang("R.101"), _make_ruang("R.102")]
        timeslots = self._make_standard_timeslots()

        app.dependency_overrides[get_db] = _db_override_room_map(user, sesi, rooms, timeslots, [])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/room-map",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["sesi_id"] == str(sesi.id)
        assert "R.101" in data["rooms"]
        assert "R.102" in data["rooms"]
        assert len(data["slots"]) == 15
        assert len(data["days"]) == 5

    def test_empty_sesi_all_cells_null(self):
        """Sesi tanpa assignment → semua sel null."""
        user = _make_user("admin")
        sesi = _make_sesi()
        rooms = [_make_ruang("R.101")]
        timeslots = self._make_standard_timeslots()

        app.dependency_overrides[get_db] = _db_override_room_map(user, sesi, rooms, timeslots, [])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/room-map",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        for slot in resp.json()["slots"]:
            assert slot["rooms"]["R.101"] is None

    def test_assigned_cell_contains_mk_info(self):
        """Sel yang terisi memuat kode MK, nama MK, kelas, dan dosen."""
        user = _make_user("admin")
        sesi = _make_sesi()
        ruang = _make_ruang("R.101")
        rooms = [ruang]
        timeslots = self._make_standard_timeslots()
        ts = timeslots[0]  # Senin Sesi 1

        dosen = _make_dosen("Dr. Andi", "AND")
        prodi = _make_prodi("S1 MTK", "Internal")
        mk_kelas = _make_mk_kelas(prodi)
        mk_kelas.kelas = "A"
        mk_kelas.mata_kuliah.kode = "MAT101"
        mk_kelas.mata_kuliah.nama = "Kalkulus I"

        assignment = _make_assignment_with_ruang(sesi.id, dosen, mk_kelas, ts, ruang)

        app.dependency_overrides[get_db] = _db_override_room_map(user, sesi, rooms, timeslots, [assignment])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/room-map",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        slots = resp.json()["slots"]
        # Slot pertama (Senin Sesi 1) harus terisi
        first_slot = slots[0]
        cell = first_slot["rooms"]["R.101"]
        assert cell is not None
        assert cell["kode_mk"] == "MAT101"
        assert cell["nama_mk"] == "Kalkulus I"
        assert cell["kelas"] == "A"
        assert cell["dosen"] == "Dr. Andi"

    def test_team_teaching_dosen_label(self):
        """Assignment dengan dosen2 → label dosen = 'dosen1 / dosen2'."""
        user = _make_user("admin")
        sesi = _make_sesi()
        ruang = _make_ruang("R.101")
        rooms = [ruang]
        timeslots = self._make_standard_timeslots()
        ts = timeslots[0]

        dosen1 = _make_dosen("Dr. Andi", "AND")
        dosen2 = _make_dosen("Dr. Budi", "BUD")
        prodi = _make_prodi("S1 MTK", "Internal")
        mk_kelas = _make_mk_kelas(prodi)

        assignment = _make_assignment_with_ruang(sesi.id, dosen1, mk_kelas, ts, ruang)
        assignment.dosen2 = dosen2

        app.dependency_overrides[get_db] = _db_override_room_map(user, sesi, rooms, timeslots, [assignment])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/room-map",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        cell = resp.json()["slots"][0]["rooms"]["R.101"]
        assert cell is not None
        assert "Dr. Andi" in cell["dosen"]
        assert "Dr. Budi" in cell["dosen"]

    def test_only_active_rooms_included(self):
        """Hanya ruang aktif yang muncul di room-map."""
        user = _make_user("admin")
        sesi = _make_sesi()
        # Satu aktif, satu tidak aktif — tapi DB override sudah filter is_active=True
        # Simulasikan DB hanya mengembalikan ruang aktif
        rooms = [_make_ruang("R.101", is_active=True)]
        timeslots = self._make_standard_timeslots()

        app.dependency_overrides[get_db] = _db_override_room_map(user, sesi, rooms, timeslots, [])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/room-map",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["rooms"] == ["R.101"]

    def test_sesi_not_found_returns_404(self):
        """Sesi tidak ditemukan → 404."""
        user = _make_user("admin")

        def _db_no_sesi():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else None
            yield db

        app.dependency_overrides[get_db] = _db_no_sesi
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{uuid.uuid4()}/reports/room-map",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 404

    def test_dosen_role_forbidden(self):
        """Role 'dosen' tidak diizinkan → 403."""
        user = _make_user("dosen")
        sesi = _make_sesi()

        def _db_dosen():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else sesi
            yield db

        app.dependency_overrides[get_db] = _db_dosen
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/room-map",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 403

    def test_koordinator_prodi_forbidden(self):
        """Role 'koordinator_prodi' tidak diizinkan untuk room-map → 403."""
        user = _make_user("koordinator_prodi")
        sesi = _make_sesi()

        def _db_kp():
            db = MagicMock()
            db.get.side_effect = lambda model, pk: user if model.__name__ == "User" else sesi
            yield db

        app.dependency_overrides[get_db] = _db_kp
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/room-map",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 403

    def test_days_order_is_canonical(self):
        """Hari dalam response mengikuti urutan Senin–Jumat."""
        user = _make_user("admin")
        sesi = _make_sesi()
        rooms = [_make_ruang("R.101")]
        timeslots = self._make_standard_timeslots()

        app.dependency_overrides[get_db] = _db_override_room_map(user, sesi, rooms, timeslots, [])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/room-map",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        days = resp.json()["days"]
        assert days == ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]

    def test_multiple_rooms_correct_cell_assignment(self):
        """Assignment di R.101 tidak mengisi sel R.102."""
        user = _make_user("admin")
        sesi = _make_sesi()
        ruang1 = _make_ruang("R.101")
        ruang2 = _make_ruang("R.102")
        rooms = [ruang1, ruang2]
        timeslots = self._make_standard_timeslots()
        ts = timeslots[0]

        dosen = _make_dosen("Dr. Andi", "AND")
        prodi = _make_prodi("S1 MTK", "Internal")
        mk_kelas = _make_mk_kelas(prodi)
        assignment = _make_assignment_with_ruang(sesi.id, dosen, mk_kelas, ts, ruang1)

        app.dependency_overrides[get_db] = _db_override_room_map(user, sesi, rooms, timeslots, [assignment])
        client = TestClient(app)
        resp = client.get(
            f"/sesi/{sesi.id}/reports/room-map",
            headers=_auth_header(user),
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        first_slot = resp.json()["slots"][0]
        assert first_slot["rooms"]["R.101"] is not None
        assert first_slot["rooms"]["R.102"] is None
