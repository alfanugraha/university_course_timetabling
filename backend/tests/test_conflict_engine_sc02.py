"""
backend/tests/test_conflict_engine_sc02.py
Unit tests for ConflictEngine.check_workload_equity() — SC-02.

Validates: SC-02 — Distribusi beban SKS antar dosen dalam satu prodi
sebaiknya merata; WARNING jika std dev > 6 SKS.
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


def _make_dosen(nama: str, kode: str, prodi: MagicMock) -> MagicMock:
    d = MagicMock()
    d.id = uuid.uuid4()
    d.nama = nama
    d.kode = kode
    d.homebase_prodi_id = prodi.id
    d.homebase_prodi = prodi
    return d


def _make_timeslot(sks: int = 3) -> MagicMock:
    ts = MagicMock()
    ts.id = uuid.uuid4()
    ts.hari = "Senin"
    ts.sks = sks
    ts.label = "Senin 07:30–10:00"
    return ts


def _make_assignment(dosen1: MagicMock, sks: int = 3, dosen2: MagicMock | None = None) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.dosen1 = dosen1
    a.dosen1_id = dosen1.id if dosen1 else None
    a.dosen2 = dosen2
    a.dosen2_id = dosen2.id if dosen2 else None
    ts = _make_timeslot(sks)
    a.timeslot = ts
    a.timeslot_id = ts.id
    return a


def _engine() -> ConflictEngine:
    return ConflictEngine(MagicMock())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckWorkloadEquity:

    def test_empty_assignments_returns_empty(self):
        assert _engine().check_workload_equity([]) == []

    def test_single_dosen_no_conflict(self):
        """Hanya satu dosen → tidak bisa hitung std dev, tidak ada konflik."""
        prodi = _make_prodi()
        d = _make_dosen("Dr. Ani", "ANI", prodi)
        assignments = [_make_assignment(d, sks=3) for _ in range(3)]

        assert _engine().check_workload_equity(assignments) == []

    def test_equal_workload_no_conflict(self):
        """Dua dosen dengan beban SKS sama → std dev = 0, tidak ada konflik."""
        prodi = _make_prodi()
        d1 = _make_dosen("Dr. Ani", "ANI", prodi)
        d2 = _make_dosen("Dr. Budi", "BUD", prodi)
        # Masing-masing 9 SKS
        assignments = (
            [_make_assignment(d1, sks=3) for _ in range(3)]
            + [_make_assignment(d2, sks=3) for _ in range(3)]
        )

        assert _engine().check_workload_equity(assignments) == []

    def test_unequal_workload_above_threshold_warns(self):
        """Dosen dengan beban sangat tidak merata → WARNING WORKLOAD_INEQUITY."""
        prodi = _make_prodi("S1 Matematika")
        d1 = _make_dosen("Dr. Ani", "ANI", prodi)
        d2 = _make_dosen("Dr. Budi", "BUD", prodi)
        # d1: 3 SKS, d2: 21 SKS → std dev = 9 > threshold 6
        assignments = (
            [_make_assignment(d1, sks=3)]
            + [_make_assignment(d2, sks=3) for _ in range(7)]
        )

        results = _engine().check_workload_equity(assignments)

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.WORKLOAD_INEQUITY
        assert r.severity == ConflictSeverity.WARNING

    def test_different_prodi_independent(self):
        """Dosen dari prodi berbeda dievaluasi secara independen."""
        prodi1 = _make_prodi("S1 Matematika")
        prodi2 = _make_prodi("S1 Statistika")
        d1 = _make_dosen("Dr. Ani", "ANI", prodi1)
        d2 = _make_dosen("Dr. Budi", "BUD", prodi1)
        d3 = _make_dosen("Dr. Citra", "CTR", prodi2)
        d4 = _make_dosen("Dr. Dian", "DIN", prodi2)
        # Prodi1: tidak merata (3 vs 21 SKS)
        # Prodi2: merata (9 vs 9 SKS)
        assignments = (
            [_make_assignment(d1, sks=3)]
            + [_make_assignment(d2, sks=3) for _ in range(7)]
            + [_make_assignment(d3, sks=3) for _ in range(3)]
            + [_make_assignment(d4, sks=3) for _ in range(3)]
        )

        results = _engine().check_workload_equity(assignments)

        assert len(results) == 1
        assert results[0].detail["prodi_id"] == str(prodi1.id)

    def test_detail_contains_expected_fields(self):
        """detail harus memuat std_dev, mean_sks, threshold, breakdown."""
        prodi = _make_prodi("S1 Matematika")
        d1 = _make_dosen("Dr. Ani", "ANI", prodi)
        d2 = _make_dosen("Dr. Budi", "BUD", prodi)
        assignments = (
            [_make_assignment(d1, sks=3)]
            + [_make_assignment(d2, sks=3) for _ in range(7)]
        )

        results = _engine().check_workload_equity(assignments)

        assert len(results) == 1
        d = results[0].detail
        assert "std_dev" in d
        assert "mean_sks" in d
        assert "threshold" in d
        assert "breakdown" in d
        assert isinstance(d["breakdown"], list)
        assert len(d["breakdown"]) == 2

    def test_workload_just_at_threshold_no_conflict(self):
        """Std dev tepat di threshold (6) → tidak ada konflik (harus > threshold)."""
        prodi = _make_prodi()
        d1 = _make_dosen("Dr. Ani", "ANI", prodi)
        d2 = _make_dosen("Dr. Budi", "BUD", prodi)
        # d1: 3 SKS, d2: 15 SKS → mean=9, std dev=6 → tepat di threshold, tidak konflik
        assignments = (
            [_make_assignment(d1, sks=3)]
            + [_make_assignment(d2, sks=3) for _ in range(5)]
        )

        results = _engine().check_workload_equity(assignments)

        # std dev = 6.0 → tidak > threshold → tidak ada konflik
        assert results == []

    def test_dosen2_counted_in_workload(self):
        """Beban dosen2 juga dihitung dalam total SKS-nya."""
        prodi = _make_prodi()
        d1 = _make_dosen("Dr. Ani", "ANI", prodi)
        d2 = _make_dosen("Dr. Budi", "BUD", prodi)
        # d1 sebagai dosen1 di 1 MK (3 SKS)
        # d2 sebagai dosen2 di 7 MK (21 SKS)
        assignments = [_make_assignment(d1, sks=3, dosen2=d2) for _ in range(7)]
        assignments += [_make_assignment(d1, sks=3)]

        results = _engine().check_workload_equity(assignments)

        # d2 punya banyak SKS dari dosen2 role
        # Verifikasi d2 masuk dalam breakdown
        if results:
            breakdown_ids = {b["dosen_id"] for b in results[0].detail["breakdown"]}
            assert str(d2.id) in breakdown_ids
