"""
backend/tests/test_conflict_engine_hc08.py
Unit tests for ConflictEngine.check_student_daily_load() — HC-08.

Validates: Requirements HC-08 — Mahasiswa satu prodi+semester
maks 2 MK atau 6 SKS per hari.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from app.services.conflict_engine import ConflictEngine, ConflictJenis, ConflictSeverity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_prodi(nama: str = "S1 Matematika") -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.nama = nama
    return p


def _make_kurikulum(prodi: MagicMock) -> MagicMock:
    k = MagicMock()
    k.id = uuid.uuid4()
    k.prodi_id = prodi.id
    k.prodi = prodi
    return k


def _make_mata_kuliah(
    nama: str,
    semester: int,
    sks: int,
    kurikulum: MagicMock,
    mk_id: uuid.UUID | None = None,
) -> MagicMock:
    mk = MagicMock()
    mk.id = mk_id or uuid.uuid4()
    mk.nama = nama
    mk.semester = semester
    mk.sks = sks
    mk.kurikulum_id = kurikulum.id
    mk.kurikulum = kurikulum
    return mk


def _make_mk_kelas(
    mata_kuliah: MagicMock,
    kelas: str = "A",
) -> MagicMock:
    mkk = MagicMock()
    mkk.id = uuid.uuid4()
    mkk.kelas = kelas
    mkk.mata_kuliah_id = mata_kuliah.id
    mkk.mata_kuliah = mata_kuliah
    mkk.label = f"{mata_kuliah.nama}-{kelas}"
    return mkk


def _make_timeslot(hari: str = "Senin", sks: int = 3) -> MagicMock:
    ts = MagicMock()
    ts.id = uuid.uuid4()
    ts.hari = hari
    ts.sks = sks
    ts.label = f"{hari} 07:30–10:00"
    return ts


def _make_assignment(
    mk_kelas: MagicMock,
    timeslot: MagicMock,
    sesi_id: uuid.UUID | None = None,
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.sesi_id = sesi_id or uuid.uuid4()
    a.mk_kelas = mk_kelas
    a.mk_kelas_id = mk_kelas.id
    a.timeslot = timeslot
    a.timeslot_id = timeslot.id
    return a


def _engine() -> ConflictEngine:
    db = MagicMock()
    return ConflictEngine(db)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckStudentDailyLoad:

    def test_empty_assignments_returns_empty(self):
        """Tidak ada assignment → tidak ada konflik."""
        results = _engine().check_student_daily_load([])
        assert results == []

    def test_one_mk_no_conflict(self):
        """Satu MK dalam satu hari → tidak ada konflik."""
        prodi = _make_prodi()
        kur = _make_kurikulum(prodi)
        mk = _make_mata_kuliah("Kalkulus I", semester=1, sks=3, kurikulum=kur)
        mkk = _make_mk_kelas(mk)
        ts = _make_timeslot("Senin", sks=3)
        a = _make_assignment(mkk, ts)

        results = _engine().check_student_daily_load([a])

        assert results == []

    def test_two_mk_six_sks_no_conflict(self):
        """2 MK (6 SKS) dalam satu hari — tepat di batas, tidak ada konflik."""
        prodi = _make_prodi()
        kur = _make_kurikulum(prodi)
        mk1 = _make_mata_kuliah("Kalkulus I", semester=1, sks=3, kurikulum=kur)
        mk2 = _make_mata_kuliah("Aljabar Linear", semester=1, sks=3, kurikulum=kur)
        mkk1 = _make_mk_kelas(mk1)
        mkk2 = _make_mk_kelas(mk2)
        ts = _make_timeslot("Senin", sks=3)
        ts2 = _make_timeslot("Senin", sks=3)
        ts2.hari = "Senin"
        a1 = _make_assignment(mkk1, ts)
        a2 = _make_assignment(mkk2, ts2)

        results = _engine().check_student_daily_load([a1, a2])

        assert results == []

    def test_three_mk_same_day_raises_error(self):
        """3 MK di hari yang sama → ERROR STUDENT_DAILY_OVERLOAD (jumlah_mk > 2)."""
        prodi = _make_prodi("S1 Matematika")
        kur = _make_kurikulum(prodi)
        mk1 = _make_mata_kuliah("Kalkulus I", semester=1, sks=3, kurikulum=kur)
        mk2 = _make_mata_kuliah("Aljabar Linear", semester=1, sks=3, kurikulum=kur)
        mk3 = _make_mata_kuliah("Statistika", semester=1, sks=3, kurikulum=kur)
        mkk1 = _make_mk_kelas(mk1)
        mkk2 = _make_mk_kelas(mk2)
        mkk3 = _make_mk_kelas(mk3)
        ts1 = _make_timeslot("Senin", sks=3)
        ts2 = _make_timeslot("Senin", sks=3)
        ts3 = _make_timeslot("Senin", sks=3)
        a1 = _make_assignment(mkk1, ts1)
        a2 = _make_assignment(mkk2, ts2)
        a3 = _make_assignment(mkk3, ts3)

        results = _engine().check_student_daily_load([a1, a2, a3])

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.STUDENT_DAILY_OVERLOAD
        assert r.severity == ConflictSeverity.ERROR
        assert set(r.assignment_ids) == {a1.id, a2.id, a3.id}

    def test_two_mk_nine_sks_raises_error(self):
        """2 MK tapi total 9 SKS → ERROR STUDENT_DAILY_OVERLOAD (total_sks > 6)."""
        prodi = _make_prodi()
        kur = _make_kurikulum(prodi)
        mk1 = _make_mata_kuliah("Kalkulus I", semester=1, sks=3, kurikulum=kur)
        mk2 = _make_mata_kuliah("Aljabar Linear", semester=1, sks=6, kurikulum=kur)
        mkk1 = _make_mk_kelas(mk1)
        mkk2 = _make_mk_kelas(mk2)
        ts1 = _make_timeslot("Selasa", sks=3)
        ts2 = _make_timeslot("Selasa", sks=6)
        a1 = _make_assignment(mkk1, ts1)
        a2 = _make_assignment(mkk2, ts2)

        results = _engine().check_student_daily_load([a1, a2])

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.STUDENT_DAILY_OVERLOAD
        assert r.severity == ConflictSeverity.ERROR
        assert r.detail["total_sks"] == 9

    def test_parallel_classes_counted_as_one_mk(self):
        """Kelas paralel A dan B dari MK yang sama dihitung sebagai 1 MK."""
        prodi = _make_prodi()
        kur = _make_kurikulum(prodi)
        mk_id = uuid.uuid4()
        mk = _make_mata_kuliah("Kalkulus I", semester=1, sks=3, kurikulum=kur, mk_id=mk_id)
        mkk_a = _make_mk_kelas(mk, kelas="A")
        mkk_b = _make_mk_kelas(mk, kelas="B")
        ts = _make_timeslot("Rabu", sks=3)
        a1 = _make_assignment(mkk_a, ts)
        a2 = _make_assignment(mkk_b, ts)

        results = _engine().check_student_daily_load([a1, a2])

        # Kelas A dan B adalah MK yang sama → jumlah_mk = 1, total_sks = 3 → tidak konflik
        assert results == []

    def test_parallel_classes_plus_two_other_mk_raises_error(self):
        """Kelas paralel (1 MK) + 2 MK lain = 3 MK unik → ERROR."""
        prodi = _make_prodi()
        kur = _make_kurikulum(prodi)
        mk_id = uuid.uuid4()
        mk1 = _make_mata_kuliah("Kalkulus I", semester=1, sks=3, kurikulum=kur, mk_id=mk_id)
        mk2 = _make_mata_kuliah("Aljabar Linear", semester=1, sks=3, kurikulum=kur)
        mk3 = _make_mata_kuliah("Statistika", semester=1, sks=3, kurikulum=kur)
        mkk1a = _make_mk_kelas(mk1, kelas="A")
        mkk1b = _make_mk_kelas(mk1, kelas="B")
        mkk2 = _make_mk_kelas(mk2)
        mkk3 = _make_mk_kelas(mk3)
        ts = _make_timeslot("Kamis", sks=3)
        a1 = _make_assignment(mkk1a, ts)
        a2 = _make_assignment(mkk1b, ts)
        a3 = _make_assignment(mkk2, ts)
        a4 = _make_assignment(mkk3, ts)

        results = _engine().check_student_daily_load([a1, a2, a3, a4])

        assert len(results) == 1
        r = results[0]
        assert r.detail["jumlah_mk"] == 3

    def test_different_prodi_same_day_no_cross_conflict(self):
        """Dua prodi berbeda dengan 3 MK masing-masing di hari yang sama → 2 konflik terpisah."""
        prodi1 = _make_prodi("S1 Matematika")
        prodi2 = _make_prodi("S1 Statistika")
        kur1 = _make_kurikulum(prodi1)
        kur2 = _make_kurikulum(prodi2)

        # Prodi 1: 3 MK di Senin
        mk1a = _make_mata_kuliah("MK-A", semester=1, sks=3, kurikulum=kur1)
        mk1b = _make_mata_kuliah("MK-B", semester=1, sks=3, kurikulum=kur1)
        mk1c = _make_mata_kuliah("MK-C", semester=1, sks=3, kurikulum=kur1)
        # Prodi 2: 3 MK di Senin
        mk2a = _make_mata_kuliah("MK-X", semester=1, sks=3, kurikulum=kur2)
        mk2b = _make_mata_kuliah("MK-Y", semester=1, sks=3, kurikulum=kur2)
        mk2c = _make_mata_kuliah("MK-Z", semester=1, sks=3, kurikulum=kur2)

        ts = _make_timeslot("Senin", sks=3)
        assignments = [
            _make_assignment(_make_mk_kelas(mk1a), ts),
            _make_assignment(_make_mk_kelas(mk1b), ts),
            _make_assignment(_make_mk_kelas(mk1c), ts),
            _make_assignment(_make_mk_kelas(mk2a), ts),
            _make_assignment(_make_mk_kelas(mk2b), ts),
            _make_assignment(_make_mk_kelas(mk2c), ts),
        ]

        results = _engine().check_student_daily_load(assignments)

        assert len(results) == 2
        prodi_ids = {r.detail["prodi_id"] for r in results}
        assert str(prodi1.id) in prodi_ids
        assert str(prodi2.id) in prodi_ids

    def test_different_semester_same_prodi_no_cross_conflict(self):
        """Semester berbeda dalam prodi yang sama tidak saling mempengaruhi."""
        prodi = _make_prodi()
        kur = _make_kurikulum(prodi)
        # Semester 1: 3 MK
        mk1 = _make_mata_kuliah("MK-1", semester=1, sks=3, kurikulum=kur)
        mk2 = _make_mata_kuliah("MK-2", semester=1, sks=3, kurikulum=kur)
        mk3 = _make_mata_kuliah("MK-3", semester=1, sks=3, kurikulum=kur)
        # Semester 3: 1 MK (tidak konflik)
        mk4 = _make_mata_kuliah("MK-4", semester=3, sks=3, kurikulum=kur)

        ts = _make_timeslot("Senin", sks=3)
        assignments = [
            _make_assignment(_make_mk_kelas(mk1), ts),
            _make_assignment(_make_mk_kelas(mk2), ts),
            _make_assignment(_make_mk_kelas(mk3), ts),
            _make_assignment(_make_mk_kelas(mk4), ts),
        ]

        results = _engine().check_student_daily_load(assignments)

        # Hanya semester 1 yang konflik
        assert len(results) == 1
        assert results[0].detail["semester"] == 1

    def test_different_day_no_conflict(self):
        """3 MK di hari berbeda (masing-masing 1 MK per hari) → tidak ada konflik."""
        prodi = _make_prodi()
        kur = _make_kurikulum(prodi)
        mk1 = _make_mata_kuliah("MK-1", semester=1, sks=3, kurikulum=kur)
        mk2 = _make_mata_kuliah("MK-2", semester=1, sks=3, kurikulum=kur)
        mk3 = _make_mata_kuliah("MK-3", semester=1, sks=3, kurikulum=kur)
        ts_sen = _make_timeslot("Senin", sks=3)
        ts_sel = _make_timeslot("Selasa", sks=3)
        ts_rab = _make_timeslot("Rabu", sks=3)
        assignments = [
            _make_assignment(_make_mk_kelas(mk1), ts_sen),
            _make_assignment(_make_mk_kelas(mk2), ts_sel),
            _make_assignment(_make_mk_kelas(mk3), ts_rab),
        ]

        results = _engine().check_student_daily_load(assignments)

        assert results == []

    def test_conflict_detail_contains_expected_fields(self):
        """detail ConflictResult harus memuat semua field yang diharapkan."""
        prodi = _make_prodi("S1 Matematika")
        kur = _make_kurikulum(prodi)
        mk1 = _make_mata_kuliah("Kalkulus I", semester=2, sks=3, kurikulum=kur)
        mk2 = _make_mata_kuliah("Aljabar Linear", semester=2, sks=3, kurikulum=kur)
        mk3 = _make_mata_kuliah("Statistika", semester=2, sks=3, kurikulum=kur)
        ts = _make_timeslot("Jumat", sks=3)
        assignments = [
            _make_assignment(_make_mk_kelas(mk1), ts),
            _make_assignment(_make_mk_kelas(mk2), ts),
            _make_assignment(_make_mk_kelas(mk3), ts),
        ]

        results = _engine().check_student_daily_load(assignments)

        assert len(results) == 1
        detail = results[0].detail
        assert "prodi_id" in detail
        assert "prodi_nama" in detail
        assert "semester" in detail
        assert "hari" in detail
        assert "jumlah_mk" in detail
        assert "total_sks" in detail
        assert "mk_names" in detail
        assert detail["prodi_id"] == str(prodi.id)
        assert detail["prodi_nama"] == "S1 Matematika"
        assert detail["semester"] == 2
        assert detail["hari"] == "Jumat"
        assert detail["jumlah_mk"] == 3
        assert detail["total_sks"] == 9

    def test_conflict_pesan_mentions_prodi_semester_hari(self):
        """Pesan konflik harus menyebut nama prodi, semester, dan hari."""
        prodi = _make_prodi("S1 Matematika")
        kur = _make_kurikulum(prodi)
        mk1 = _make_mata_kuliah("MK-1", semester=3, sks=3, kurikulum=kur)
        mk2 = _make_mata_kuliah("MK-2", semester=3, sks=3, kurikulum=kur)
        mk3 = _make_mata_kuliah("MK-3", semester=3, sks=3, kurikulum=kur)
        ts = _make_timeslot("Kamis", sks=3)
        assignments = [
            _make_assignment(_make_mk_kelas(mk1), ts),
            _make_assignment(_make_mk_kelas(mk2), ts),
            _make_assignment(_make_mk_kelas(mk3), ts),
        ]

        results = _engine().check_student_daily_load(assignments)

        assert len(results) == 1
        pesan = results[0].pesan
        assert "S1 Matematika" in pesan
        assert "3" in pesan   # semester
        assert "Kamis" in pesan

    def test_assignment_missing_relations_skipped(self):
        """Assignment dengan relasi tidak lengkap dilewati tanpa error."""
        # Assignment dengan mk_kelas = None
        a_bad1 = MagicMock()
        a_bad1.id = uuid.uuid4()
        a_bad1.mk_kelas = None

        # Assignment dengan timeslot = None
        prodi = _make_prodi()
        kur = _make_kurikulum(prodi)
        mk = _make_mata_kuliah("MK-1", semester=1, sks=3, kurikulum=kur)
        mkk = _make_mk_kelas(mk)
        a_bad2 = MagicMock()
        a_bad2.id = uuid.uuid4()
        a_bad2.mk_kelas = mkk
        a_bad2.timeslot = None

        results = _engine().check_student_daily_load([a_bad1, a_bad2])

        assert results == []
