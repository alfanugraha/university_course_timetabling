"""
backend/tests/test_conflict_engine_hc09.py
Unit tests for ConflictEngine.check_lecturer_daily_load() — HC-09.

Validates: Requirements HC-09 — Dosen maks 2 MK atau 6 SKS per hari,
dihitung dari semua assignment di mana dosen muncul sebagai dosen1 atau dosen2.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from app.services.conflict_engine import ConflictEngine, ConflictJenis, ConflictSeverity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dosen(nama: str = "Dr. Budi", kode: str = "BUD") -> MagicMock:
    d = MagicMock()
    d.id = uuid.uuid4()
    d.nama = nama
    d.kode = kode
    return d


def _make_mata_kuliah(nama: str = "Kalkulus I", sks: int = 3) -> MagicMock:
    mk = MagicMock()
    mk.id = uuid.uuid4()
    mk.nama = nama
    mk.sks = sks
    return mk


def _make_mk_kelas(mata_kuliah: MagicMock, kelas: str = "A") -> MagicMock:
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
    dosen1: MagicMock | None = None,
    dosen2: MagicMock | None = None,
    sesi_id: uuid.UUID | None = None,
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.sesi_id = sesi_id or uuid.uuid4()
    a.mk_kelas = mk_kelas
    a.mk_kelas_id = mk_kelas.id
    a.timeslot = timeslot
    a.timeslot_id = timeslot.id
    a.dosen1 = dosen1
    a.dosen1_id = dosen1.id if dosen1 else None
    a.dosen2 = dosen2
    a.dosen2_id = dosen2.id if dosen2 else None
    return a


def _engine() -> ConflictEngine:
    db = MagicMock()
    return ConflictEngine(db)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckLecturerDailyLoad:

    def test_empty_assignments_returns_empty(self):
        """Tidak ada assignment → tidak ada konflik."""
        results = _engine().check_lecturer_daily_load([])
        assert results == []

    def test_one_mk_no_conflict(self):
        """Dosen mengajar 1 MK dalam satu hari → tidak ada konflik."""
        d = _make_dosen()
        mk = _make_mata_kuliah("Kalkulus I", sks=3)
        mkk = _make_mk_kelas(mk)
        ts = _make_timeslot("Senin", sks=3)
        a = _make_assignment(mkk, ts, dosen1=d)

        results = _engine().check_lecturer_daily_load([a])

        assert results == []

    def test_two_mk_six_sks_no_conflict(self):
        """Dosen mengajar 2 MK (6 SKS) dalam satu hari — tepat di batas, tidak konflik."""
        d = _make_dosen()
        mk1 = _make_mata_kuliah("Kalkulus I", sks=3)
        mk2 = _make_mata_kuliah("Aljabar Linear", sks=3)
        ts = _make_timeslot("Senin", sks=3)
        a1 = _make_assignment(_make_mk_kelas(mk1), ts, dosen1=d)
        a2 = _make_assignment(_make_mk_kelas(mk2), ts, dosen1=d)

        results = _engine().check_lecturer_daily_load([a1, a2])

        assert results == []

    def test_three_mk_same_day_raises_error(self):
        """Dosen mengajar 3 MK di hari yang sama → ERROR LECTURER_DAILY_OVERLOAD."""
        d = _make_dosen("Dr. Ani", "ANI")
        mk1 = _make_mata_kuliah("Kalkulus I", sks=3)
        mk2 = _make_mata_kuliah("Aljabar Linear", sks=3)
        mk3 = _make_mata_kuliah("Statistika", sks=3)
        ts = _make_timeslot("Senin", sks=3)
        a1 = _make_assignment(_make_mk_kelas(mk1), ts, dosen1=d)
        a2 = _make_assignment(_make_mk_kelas(mk2), ts, dosen1=d)
        a3 = _make_assignment(_make_mk_kelas(mk3), ts, dosen1=d)

        results = _engine().check_lecturer_daily_load([a1, a2, a3])

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.LECTURER_DAILY_OVERLOAD
        assert r.severity == ConflictSeverity.ERROR
        assert set(r.assignment_ids) == {a1.id, a2.id, a3.id}
        assert r.detail["jumlah_mk"] == 3

    def test_dosen_as_dosen2_counted(self):
        """Dosen yang muncul sebagai dosen2 juga dihitung dalam beban hariannya."""
        d = _make_dosen("Dr. Budi", "BUD")
        d_other = _make_dosen("Dr. Citra", "CTR")
        mk1 = _make_mata_kuliah("MK-1", sks=3)
        mk2 = _make_mata_kuliah("MK-2", sks=3)
        mk3 = _make_mata_kuliah("MK-3", sks=3)
        ts = _make_timeslot("Selasa", sks=3)
        # d sebagai dosen1 di mk1 dan mk2, sebagai dosen2 di mk3
        a1 = _make_assignment(_make_mk_kelas(mk1), ts, dosen1=d)
        a2 = _make_assignment(_make_mk_kelas(mk2), ts, dosen1=d)
        a3 = _make_assignment(_make_mk_kelas(mk3), ts, dosen1=d_other, dosen2=d)

        results = _engine().check_lecturer_daily_load([a1, a2, a3])

        # d mengajar 3 MK → ERROR
        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.LECTURER_DAILY_OVERLOAD
        assert r.detail["dosen_id"] == str(d.id)
        assert r.detail["jumlah_mk"] == 3

    def test_dosen1_as_dosen2_in_another_total_two_mk_no_conflict(self):
        """Dosen sebagai dosen1 di 1 MK + dosen2 di 1 MK berbeda = 2 MK → tidak konflik."""
        d = _make_dosen()
        d_other = _make_dosen("Dr. Eko", "EKO")
        mk1 = _make_mata_kuliah("MK-1", sks=3)
        mk2 = _make_mata_kuliah("MK-2", sks=3)
        ts = _make_timeslot("Rabu", sks=3)
        a1 = _make_assignment(_make_mk_kelas(mk1), ts, dosen1=d)
        a2 = _make_assignment(_make_mk_kelas(mk2), ts, dosen1=d_other, dosen2=d)

        results = _engine().check_lecturer_daily_load([a1, a2])

        assert results == []

    def test_different_dosen_independent(self):
        """Dua dosen berbeda dengan 3 MK masing-masing → 2 konflik terpisah."""
        d1 = _make_dosen("Dr. Fani", "FAN")
        d2 = _make_dosen("Dr. Gita", "GIT")
        ts = _make_timeslot("Kamis", sks=3)

        assignments = []
        for i in range(3):
            mk = _make_mata_kuliah(f"MK-D1-{i}", sks=3)
            assignments.append(_make_assignment(_make_mk_kelas(mk), ts, dosen1=d1))
        for i in range(3):
            mk = _make_mata_kuliah(f"MK-D2-{i}", sks=3)
            assignments.append(_make_assignment(_make_mk_kelas(mk), ts, dosen1=d2))

        results = _engine().check_lecturer_daily_load(assignments)

        assert len(results) == 2
        dosen_ids = {r.detail["dosen_id"] for r in results}
        assert str(d1.id) in dosen_ids
        assert str(d2.id) in dosen_ids

    def test_different_day_no_conflict(self):
        """Dosen mengajar 3 MK di hari berbeda (1 per hari) → tidak ada konflik."""
        d = _make_dosen()
        ts_sen = _make_timeslot("Senin", sks=3)
        ts_sel = _make_timeslot("Selasa", sks=3)
        ts_rab = _make_timeslot("Rabu", sks=3)
        assignments = [
            _make_assignment(_make_mk_kelas(_make_mata_kuliah("MK-1")), ts_sen, dosen1=d),
            _make_assignment(_make_mk_kelas(_make_mata_kuliah("MK-2")), ts_sel, dosen1=d),
            _make_assignment(_make_mk_kelas(_make_mata_kuliah("MK-3")), ts_rab, dosen1=d),
        ]

        results = _engine().check_lecturer_daily_load(assignments)

        assert results == []

    def test_sks_overload_two_mk_nine_sks(self):
        """2 MK tapi total 9 SKS → ERROR (total_sks > 6)."""
        d = _make_dosen()
        mk1 = _make_mata_kuliah("MK-1", sks=3)
        mk2 = _make_mata_kuliah("MK-2", sks=6)
        ts1 = _make_timeslot("Jumat", sks=3)
        ts2 = _make_timeslot("Jumat", sks=6)
        a1 = _make_assignment(_make_mk_kelas(mk1), ts1, dosen1=d)
        a2 = _make_assignment(_make_mk_kelas(mk2), ts2, dosen1=d)

        results = _engine().check_lecturer_daily_load([a1, a2])

        assert len(results) == 1
        assert results[0].detail["total_sks"] == 9

    def test_parallel_classes_same_mk_counted_once(self):
        """Dosen mengajar kelas A dan B dari MK yang sama → dihitung 1 MK, bukan 2."""
        d = _make_dosen()
        mk_id = uuid.uuid4()
        mk = _make_mata_kuliah("Kalkulus I", sks=3)
        mk.id = mk_id
        mkk_a = _make_mk_kelas(mk, kelas="A")
        mkk_b = _make_mk_kelas(mk, kelas="B")
        ts = _make_timeslot("Senin", sks=3)
        a1 = _make_assignment(mkk_a, ts, dosen1=d)
        a2 = _make_assignment(mkk_b, ts, dosen1=d)

        results = _engine().check_lecturer_daily_load([a1, a2])

        # 1 MK unik, 3 SKS → tidak konflik
        assert results == []

    def test_conflict_detail_contains_expected_fields(self):
        """detail ConflictResult harus memuat semua field yang diharapkan."""
        d = _make_dosen("Dr. Hadi", "HAD")
        ts = _make_timeslot("Senin", sks=3)
        assignments = [
            _make_assignment(_make_mk_kelas(_make_mata_kuliah(f"MK-{i}")), ts, dosen1=d)
            for i in range(3)
        ]

        results = _engine().check_lecturer_daily_load(assignments)

        assert len(results) == 1
        detail = results[0].detail
        assert "dosen_id" in detail
        assert "dosen_nama" in detail
        assert "dosen_kode" in detail
        assert "hari" in detail
        assert "jumlah_mk" in detail
        assert "total_sks" in detail
        assert "mk_names" in detail
        assert detail["dosen_id"] == str(d.id)
        assert detail["dosen_nama"] == "Dr. Hadi"
        assert detail["dosen_kode"] == "HAD"
        assert detail["hari"] == "Senin"

    def test_conflict_pesan_mentions_dosen_and_hari(self):
        """Pesan konflik harus menyebut nama dosen dan hari."""
        d = _make_dosen("Dr. Irma", "IRM")
        ts = _make_timeslot("Rabu", sks=3)
        assignments = [
            _make_assignment(_make_mk_kelas(_make_mata_kuliah(f"MK-{i}")), ts, dosen1=d)
            for i in range(3)
        ]

        results = _engine().check_lecturer_daily_load(assignments)

        assert len(results) == 1
        pesan = results[0].pesan
        assert "Irma" in pesan or "IRM" in pesan
        assert "Rabu" in pesan

    def test_assignment_missing_timeslot_skipped(self):
        """Assignment dengan timeslot=None dilewati tanpa error."""
        d = _make_dosen()
        mk = _make_mata_kuliah("MK-1")
        a_bad = MagicMock()
        a_bad.id = uuid.uuid4()
        a_bad.timeslot = None
        a_bad.dosen1_id = d.id
        a_bad.dosen2_id = None

        results = _engine().check_lecturer_daily_load([a_bad])

        assert results == []

    def test_dosen1_none_not_counted(self):
        """dosen1_id=None tidak menyebabkan error."""
        d2 = _make_dosen("Dr. Joko", "JOK")
        mk = _make_mata_kuliah("MK-1")
        ts = _make_timeslot("Senin", sks=3)
        a = _make_assignment(_make_mk_kelas(mk), ts, dosen1=None, dosen2=d2)

        results = _engine().check_lecturer_daily_load([a])

        assert results == []
