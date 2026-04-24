"""
backend/tests/test_conflict_engine_sc01.py
Unit tests for ConflictEngine.check_student_conflict() — SC-01.

Validates: SC-01 — MK satu semester satu prodi sebaiknya tidak dijadwalkan
bersamaan (WARNING; pelengkap informatif dari HC-08).
"""

import uuid
from unittest.mock import MagicMock

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


def _make_mata_kuliah(nama: str, semester: int, kurikulum: MagicMock) -> MagicMock:
    mk = MagicMock()
    mk.id = uuid.uuid4()
    mk.nama = nama
    mk.semester = semester
    mk.kurikulum_id = kurikulum.id
    mk.kurikulum = kurikulum
    return mk


def _make_mk_kelas(mata_kuliah: MagicMock, kelas: str = "A") -> MagicMock:
    mkk = MagicMock()
    mkk.id = uuid.uuid4()
    mkk.kelas = kelas
    mkk.mata_kuliah_id = mata_kuliah.id
    mkk.mata_kuliah = mata_kuliah
    return mkk


def _make_timeslot(hari: str = "Senin", sks: int = 3) -> MagicMock:
    ts = MagicMock()
    ts.id = uuid.uuid4()
    ts.hari = hari
    ts.sks = sks
    ts.label = f"{hari} 07:30–10:00"
    return ts


def _make_assignment(mk_kelas: MagicMock, timeslot: MagicMock) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.mk_kelas = mk_kelas
    a.mk_kelas_id = mk_kelas.id
    a.timeslot = timeslot
    a.timeslot_id = timeslot.id
    return a


def _engine() -> ConflictEngine:
    return ConflictEngine(MagicMock())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckStudentConflict:

    def test_empty_assignments_returns_empty(self):
        assert _engine().check_student_conflict([]) == []

    def test_single_mk_no_conflict(self):
        """Satu MK di satu slot → tidak ada konflik."""
        prodi = _make_prodi()
        kur = _make_kurikulum(prodi)
        mk = _make_mata_kuliah("Kalkulus I", semester=1, kurikulum=kur)
        ts = _make_timeslot("Senin")
        a = _make_assignment(_make_mk_kelas(mk), ts)

        assert _engine().check_student_conflict([a]) == []

    def test_two_mk_same_prodi_semester_same_timeslot_warns(self):
        """2 MK berbeda, prodi+semester sama, timeslot sama → WARNING STUDENT_CONFLICT."""
        prodi = _make_prodi("S1 Matematika")
        kur = _make_kurikulum(prodi)
        mk1 = _make_mata_kuliah("Kalkulus I", semester=1, kurikulum=kur)
        mk2 = _make_mata_kuliah("Aljabar Linear", semester=1, kurikulum=kur)
        ts = _make_timeslot("Senin")
        a1 = _make_assignment(_make_mk_kelas(mk1), ts)
        a2 = _make_assignment(_make_mk_kelas(mk2), ts)

        results = _engine().check_student_conflict([a1, a2])

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.STUDENT_CONFLICT
        assert r.severity == ConflictSeverity.WARNING
        assert set(r.assignment_ids) == {a1.id, a2.id}

    def test_two_mk_different_timeslot_no_conflict(self):
        """2 MK prodi+semester sama tapi timeslot berbeda → tidak ada konflik."""
        prodi = _make_prodi()
        kur = _make_kurikulum(prodi)
        mk1 = _make_mata_kuliah("MK-1", semester=1, kurikulum=kur)
        mk2 = _make_mata_kuliah("MK-2", semester=1, kurikulum=kur)
        ts1 = _make_timeslot("Senin")
        ts2 = _make_timeslot("Selasa")
        a1 = _make_assignment(_make_mk_kelas(mk1), ts1)
        a2 = _make_assignment(_make_mk_kelas(mk2), ts2)

        assert _engine().check_student_conflict([a1, a2]) == []

    def test_two_mk_different_semester_same_timeslot_no_conflict(self):
        """2 MK prodi sama tapi semester berbeda di timeslot sama → tidak ada konflik."""
        prodi = _make_prodi()
        kur = _make_kurikulum(prodi)
        mk1 = _make_mata_kuliah("MK-1", semester=1, kurikulum=kur)
        mk2 = _make_mata_kuliah("MK-2", semester=3, kurikulum=kur)
        ts = _make_timeslot("Senin")
        a1 = _make_assignment(_make_mk_kelas(mk1), ts)
        a2 = _make_assignment(_make_mk_kelas(mk2), ts)

        assert _engine().check_student_conflict([a1, a2]) == []

    def test_two_mk_different_prodi_same_timeslot_no_conflict(self):
        """2 MK prodi berbeda di timeslot sama → tidak ada konflik."""
        prodi1 = _make_prodi("S1 Matematika")
        prodi2 = _make_prodi("S1 Statistika")
        kur1 = _make_kurikulum(prodi1)
        kur2 = _make_kurikulum(prodi2)
        mk1 = _make_mata_kuliah("MK-1", semester=1, kurikulum=kur1)
        mk2 = _make_mata_kuliah("MK-2", semester=1, kurikulum=kur2)
        ts = _make_timeslot("Senin")
        a1 = _make_assignment(_make_mk_kelas(mk1), ts)
        a2 = _make_assignment(_make_mk_kelas(mk2), ts)

        assert _engine().check_student_conflict([a1, a2]) == []

    def test_parallel_classes_same_mk_not_conflict(self):
        """Kelas paralel A dan B dari MK yang sama di timeslot sama → bukan konflik SC-01."""
        prodi = _make_prodi()
        kur = _make_kurikulum(prodi)
        mk = _make_mata_kuliah("Kalkulus I", semester=1, kurikulum=kur)
        ts = _make_timeslot("Senin")
        a1 = _make_assignment(_make_mk_kelas(mk, kelas="A"), ts)
        a2 = _make_assignment(_make_mk_kelas(mk, kelas="B"), ts)

        # Hanya 1 MK unik → tidak ada konflik
        assert _engine().check_student_conflict([a1, a2]) == []

    def test_detail_contains_expected_fields(self):
        """detail harus memuat prodi_id, semester, timeslot_id, jumlah_mk, mk_names."""
        prodi = _make_prodi("S1 Matematika")
        kur = _make_kurikulum(prodi)
        mk1 = _make_mata_kuliah("Kalkulus I", semester=2, kurikulum=kur)
        mk2 = _make_mata_kuliah("Aljabar Linear", semester=2, kurikulum=kur)
        ts = _make_timeslot("Rabu")
        a1 = _make_assignment(_make_mk_kelas(mk1), ts)
        a2 = _make_assignment(_make_mk_kelas(mk2), ts)

        results = _engine().check_student_conflict([a1, a2])

        assert len(results) == 1
        d = results[0].detail
        assert d["prodi_id"] == str(prodi.id)
        assert d["semester"] == 2
        assert d["jumlah_mk"] == 2
        assert isinstance(d["mk_names"], list)
        assert len(d["mk_names"]) == 2

    def test_pesan_mentions_prodi_and_semester(self):
        """Pesan harus menyebut nama prodi dan semester."""
        prodi = _make_prodi("S1 Matematika")
        kur = _make_kurikulum(prodi)
        mk1 = _make_mata_kuliah("MK-1", semester=3, kurikulum=kur)
        mk2 = _make_mata_kuliah("MK-2", semester=3, kurikulum=kur)
        ts = _make_timeslot("Kamis")
        a1 = _make_assignment(_make_mk_kelas(mk1), ts)
        a2 = _make_assignment(_make_mk_kelas(mk2), ts)

        results = _engine().check_student_conflict([a1, a2])

        assert len(results) == 1
        assert "S1 Matematika" in results[0].pesan
        assert "3" in results[0].pesan
