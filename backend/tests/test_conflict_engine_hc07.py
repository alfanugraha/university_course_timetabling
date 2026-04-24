"""
backend/tests/test_conflict_engine_hc07.py
Unit tests for ConflictEngine.check_parallel_mismatch() — HC-07.

Validates: Requirements HC-07 — Kelas paralel dari MK yang sama
wajib dijadwalkan di timeslot yang sama dalam satu sesi.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from app.services.conflict_engine import ConflictEngine, ConflictJenis, ConflictSeverity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_timeslot(label: str = "Senin 07:30–10:00") -> MagicMock:
    ts = MagicMock()
    ts.id = uuid.uuid4()
    ts.label = label
    return ts


def _make_mata_kuliah(nama: str = "Kalkulus I", mk_id: uuid.UUID | None = None) -> MagicMock:
    mk = MagicMock()
    mk.id = mk_id or uuid.uuid4()
    mk.nama = nama
    return mk


def _make_mk_kelas(
    kelas: str,
    mata_kuliah: MagicMock,
    label: str | None = None,
) -> MagicMock:
    mkk = MagicMock()
    mkk.id = uuid.uuid4()
    mkk.kelas = kelas
    mkk.mata_kuliah_id = mata_kuliah.id
    mkk.mata_kuliah = mata_kuliah
    mkk.label = label or f"{mata_kuliah.nama}-{kelas}"
    return mkk


def _make_assignment(
    mk_kelas: MagicMock,
    timeslot: MagicMock,
    sesi_id: uuid.UUID | None = None,
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.sesi_id = sesi_id or uuid.uuid4()
    a.mk_kelas = mk_kelas
    a.mk_kelas_id = mk_kelas.id if mk_kelas else None
    a.timeslot = timeslot
    a.timeslot_id = timeslot.id
    return a


def _engine() -> ConflictEngine:
    db = MagicMock()
    return ConflictEngine(db)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckParallelMismatch:

    def test_no_conflict_single_class(self):
        """Satu kelas saja (tidak ada paralel) — tidak ada konflik."""
        mk = _make_mata_kuliah("Aljabar Linear")
        mkk_a = _make_mk_kelas("A", mk)
        ts = _make_timeslot("Senin 07:30")
        assignments = [_make_assignment(mkk_a, ts)]

        results = _engine().check_parallel_mismatch(assignments)

        assert results == []

    def test_no_conflict_parallel_same_timeslot(self):
        """Dua kelas paralel di timeslot yang sama — tidak ada konflik."""
        mk = _make_mata_kuliah("Kalkulus I")
        mkk_a = _make_mk_kelas("A", mk)
        mkk_b = _make_mk_kelas("B", mk)
        ts = _make_timeslot("Selasa 10:00")
        assignments = [
            _make_assignment(mkk_a, ts),
            _make_assignment(mkk_b, ts),
        ]

        results = _engine().check_parallel_mismatch(assignments)

        assert results == []

    def test_conflict_two_parallel_different_timeslots(self):
        """Dua kelas paralel di timeslot berbeda → ERROR PARALLEL_MISMATCH."""
        mk = _make_mata_kuliah("Kalkulus II")
        mkk_a = _make_mk_kelas("A", mk)
        mkk_b = _make_mk_kelas("B", mk)
        ts1 = _make_timeslot("Senin 07:30")
        ts2 = _make_timeslot("Senin 10:00")
        a1 = _make_assignment(mkk_a, ts1)
        a2 = _make_assignment(mkk_b, ts2)

        results = _engine().check_parallel_mismatch([a1, a2])

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.PARALLEL_MISMATCH
        assert r.severity == ConflictSeverity.ERROR
        assert set(r.assignment_ids) == {a1.id, a2.id}
        # Pesan harus menyebut kedua kelas
        assert "A" in r.pesan
        assert "B" in r.pesan

    def test_conflict_detail_fields(self):
        """detail harus mengandung mata_kuliah_id, mata_kuliah_nama, kelas_slots."""
        mk_id = uuid.uuid4()
        mk = _make_mata_kuliah("Statistika", mk_id=mk_id)
        mkk_a = _make_mk_kelas("A", mk)
        mkk_b = _make_mk_kelas("B", mk)
        ts1 = _make_timeslot("Rabu 07:30")
        ts2 = _make_timeslot("Rabu 13:00")
        a1 = _make_assignment(mkk_a, ts1)
        a2 = _make_assignment(mkk_b, ts2)

        results = _engine().check_parallel_mismatch([a1, a2])

        assert len(results) == 1
        detail = results[0].detail
        assert detail["mata_kuliah_id"] == str(mk_id)
        assert detail["mata_kuliah_nama"] == "Statistika"
        assert isinstance(detail["kelas_slots"], list)
        assert len(detail["kelas_slots"]) == 2
        kelas_values = {ks["kelas"] for ks in detail["kelas_slots"]}
        assert kelas_values == {"A", "B"}

    def test_no_conflict_three_parallel_same_timeslot(self):
        """Tiga kelas paralel (A, B, C) semua di timeslot yang sama — tidak ada konflik PARALLEL_MISMATCH."""
        mk = _make_mata_kuliah("Kalkulus III")
        mkk_a = _make_mk_kelas("A", mk)
        mkk_b = _make_mk_kelas("B", mk)
        mkk_c = _make_mk_kelas("C", mk)
        ts = _make_timeslot("Kamis 07:30")
        a1 = _make_assignment(mkk_a, ts)
        a2 = _make_assignment(mkk_b, ts)
        a3 = _make_assignment(mkk_c, ts)

        results = _engine().check_parallel_mismatch([a1, a2, a3])

        parallel_errors = [r for r in results if r.jenis == ConflictJenis.PARALLEL_MISMATCH]
        assert parallel_errors == []

    def test_conflict_three_parallel_one_different(self):
        """Tiga kelas paralel (A, B, C) di mana C di slot berbeda → ERROR, semua 3 assignment_ids."""
        mk = _make_mata_kuliah("Geometri")
        mkk_a = _make_mk_kelas("A", mk)
        mkk_b = _make_mk_kelas("B", mk)
        mkk_c = _make_mk_kelas("C", mk)
        ts1 = _make_timeslot("Kamis 07:30")
        ts2 = _make_timeslot("Kamis 10:00")
        a1 = _make_assignment(mkk_a, ts1)
        a2 = _make_assignment(mkk_b, ts1)
        a3 = _make_assignment(mkk_c, ts2)

        results = _engine().check_parallel_mismatch([a1, a2, a3])

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.PARALLEL_MISMATCH
        assert r.severity == ConflictSeverity.ERROR
        assert set(r.assignment_ids) == {a1.id, a2.id, a3.id}

    def test_no_conflict_different_mk_different_timeslots(self):
        """Dua MK berbeda (bukan paralel) di timeslot berbeda — tidak ada konflik."""
        mk1 = _make_mata_kuliah("Kalkulus I")
        mk2 = _make_mata_kuliah("Aljabar Linear")
        mkk_a = _make_mk_kelas("A", mk1)
        mkk_b = _make_mk_kelas("A", mk2)
        ts1 = _make_timeslot("Senin 07:30")
        ts2 = _make_timeslot("Selasa 10:00")
        assignments = [
            _make_assignment(mkk_a, ts1),
            _make_assignment(mkk_b, ts2),
        ]

        results = _engine().check_parallel_mismatch(assignments)

        assert results == []

    def test_edge_case_mk_kelas_none_skipped(self):
        """Assignment dengan mk_kelas=None dilewati tanpa error."""
        a_bad = MagicMock()
        a_bad.id = uuid.uuid4()
        a_bad.mk_kelas = None

        mk = _make_mata_kuliah("Topologi")
        mkk_a = _make_mk_kelas("A", mk)
        ts = _make_timeslot("Jumat 07:30")
        a_good = _make_assignment(mkk_a, ts)

        results = _engine().check_parallel_mismatch([a_bad, a_good])

        assert results == []

    def test_edge_case_mata_kuliah_id_none_skipped(self):
        """Assignment dengan mk_kelas.mata_kuliah_id=None dilewati tanpa error."""
        mkk_bad = MagicMock()
        mkk_bad.id = uuid.uuid4()
        mkk_bad.mata_kuliah_id = None

        a_bad = MagicMock()
        a_bad.id = uuid.uuid4()
        a_bad.mk_kelas = mkk_bad

        results = _engine().check_parallel_mismatch([a_bad])

        assert results == []

    def test_empty_assignments(self):
        """Tidak ada assignment → tidak ada konflik."""
        results = _engine().check_parallel_mismatch([])
        assert results == []

    def test_conflict_pesan_mentions_mk_nama(self):
        """Pesan konflik harus menyebut nama mata kuliah."""
        mk = _make_mata_kuliah("Analisis Real")
        mkk_a = _make_mk_kelas("A", mk)
        mkk_b = _make_mk_kelas("B", mk)
        ts1 = _make_timeslot("Senin 07:30")
        ts2 = _make_timeslot("Senin 13:00")
        a1 = _make_assignment(mkk_a, ts1)
        a2 = _make_assignment(mkk_b, ts2)

        results = _engine().check_parallel_mismatch([a1, a2])

        assert len(results) == 1
        assert "Analisis Real" in results[0].pesan
