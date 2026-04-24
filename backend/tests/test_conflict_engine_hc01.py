"""
backend/tests/test_conflict_engine_hc01.py
Unit tests for ConflictEngine.check_lecturer_double() — HC-01.

Validates: Requirements HC-01 — Dosen tidak boleh mengajar dua kelas
di timeslot yang sama dalam satu sesi.
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


def _make_dosen(nama: str = "Dr. Budi", kode: str = "BUD") -> MagicMock:
    d = MagicMock()
    d.id = uuid.uuid4()
    d.nama = nama
    d.kode = kode
    return d


def _make_mk_kelas(label: str = "MAT101-A") -> MagicMock:
    mk = MagicMock()
    mk.id = uuid.uuid4()
    mk.label = label
    return mk


def _make_assignment(
    dosen1: MagicMock,
    timeslot: MagicMock,
    mk_kelas: MagicMock,
    dosen2: MagicMock | None = None,
    sesi_id: uuid.UUID | None = None,
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.sesi_id = sesi_id or uuid.uuid4()
    a.dosen1 = dosen1
    a.dosen1_id = dosen1.id
    a.dosen2 = dosen2
    a.dosen2_id = dosen2.id if dosen2 else None
    a.timeslot = timeslot
    a.timeslot_id = timeslot.id
    a.mk_kelas = mk_kelas
    a.mk_kelas_id = mk_kelas.id
    return a


def _engine() -> ConflictEngine:
    db = MagicMock()
    return ConflictEngine(db)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckLecturerDouble:

    def test_no_conflict_single_assignment(self):
        """Satu assignment saja — tidak ada konflik."""
        ts = _make_timeslot()
        d1 = _make_dosen()
        mk = _make_mk_kelas()
        assignments = [_make_assignment(d1, ts, mk)]

        results = _engine().check_lecturer_double(assignments)

        assert results == []

    def test_no_conflict_different_timeslots(self):
        """Dosen yang sama di timeslot berbeda — tidak ada konflik."""
        d1 = _make_dosen()
        ts1 = _make_timeslot("Senin 07:30")
        ts2 = _make_timeslot("Senin 10:00")
        mk1 = _make_mk_kelas("MAT101-A")
        mk2 = _make_mk_kelas("MAT102-A")
        assignments = [
            _make_assignment(d1, ts1, mk1),
            _make_assignment(d1, ts2, mk2),
        ]

        results = _engine().check_lecturer_double(assignments)

        assert results == []

    def test_conflict_dosen1_same_timeslot(self):
        """Dosen1 muncul di dua assignment pada timeslot yang sama → ERROR."""
        d1 = _make_dosen("Dr. Budi", "BUD")
        d_other = _make_dosen("Dr. Ani", "ANI")
        ts = _make_timeslot("Senin 07:30")
        mk1 = _make_mk_kelas("MAT101-A")
        mk2 = _make_mk_kelas("MAT102-A")
        a1 = _make_assignment(d1, ts, mk1)
        a2 = _make_assignment(d1, ts, mk2)
        # second assignment has a different dosen1 to avoid trivial duplicate
        a2.dosen1 = d_other
        a2.dosen1_id = d_other.id
        a2.dosen2 = d1
        a2.dosen2_id = d1.id

        assignments = [a1, a2]
        results = _engine().check_lecturer_double(assignments)

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.LECTURER_DOUBLE
        assert r.severity == ConflictSeverity.ERROR
        assert set(r.assignment_ids) == {a1.id, a2.id}
        assert "Budi" in r.pesan or "BUD" in r.pesan
        assert r.detail["dosen_id"] == str(d1.id)
        assert r.detail["timeslot_label"] == "Senin 07:30"

    def test_conflict_dosen1_in_two_assignments(self):
        """Dosen sebagai dosen1 di dua kelas berbeda pada slot yang sama."""
        d1 = _make_dosen("Dr. Citra", "CTR")
        ts = _make_timeslot("Selasa 10:00")
        mk1 = _make_mk_kelas("MAT201-A")
        mk2 = _make_mk_kelas("MAT201-B")
        a1 = _make_assignment(d1, ts, mk1)
        a2 = _make_assignment(d1, ts, mk2)

        results = _engine().check_lecturer_double([a1, a2])

        assert len(results) == 1
        assert results[0].severity == ConflictSeverity.ERROR
        assert set(results[0].assignment_ids) == {a1.id, a2.id}

    def test_conflict_dosen2_same_timeslot(self):
        """Dosen sebagai dosen2 di dua assignment pada slot yang sama → ERROR."""
        d_main1 = _make_dosen("Dr. X", "X")
        d_main2 = _make_dosen("Dr. Y", "Y")
        d_shared = _make_dosen("Dr. Shared", "SHR")
        ts = _make_timeslot("Rabu 13:00")
        mk1 = _make_mk_kelas("MAT301-A")
        mk2 = _make_mk_kelas("MAT302-A")
        a1 = _make_assignment(d_main1, ts, mk1, dosen2=d_shared)
        a2 = _make_assignment(d_main2, ts, mk2, dosen2=d_shared)

        results = _engine().check_lecturer_double([a1, a2])

        # d_shared appears as dosen2 in both → conflict
        conflict_dosen_ids = {r.detail["dosen_id"] for r in results}
        assert str(d_shared.id) in conflict_dosen_ids

    def test_conflict_dosen1_and_dosen2_cross(self):
        """Dosen sebagai dosen1 di satu assignment dan dosen2 di assignment lain → ERROR."""
        d1 = _make_dosen("Dr. Dian", "DIN")
        d_other = _make_dosen("Dr. Eko", "EKO")
        ts = _make_timeslot("Kamis 07:30")
        mk1 = _make_mk_kelas("MAT401-A")
        mk2 = _make_mk_kelas("MAT402-A")
        a1 = _make_assignment(d1, ts, mk1)           # d1 as dosen1
        a2 = _make_assignment(d_other, ts, mk2, dosen2=d1)  # d1 as dosen2

        results = _engine().check_lecturer_double([a1, a2])

        conflict_dosen_ids = {r.detail["dosen_id"] for r in results}
        assert str(d1.id) in conflict_dosen_ids

    def test_no_conflict_dosen2_is_null(self):
        """dosen2_id NULL tidak menyebabkan false positive."""
        d1 = _make_dosen()
        ts = _make_timeslot()
        mk = _make_mk_kelas()
        a = _make_assignment(d1, ts, mk, dosen2=None)

        results = _engine().check_lecturer_double([a])

        assert results == []

    def test_empty_assignments(self):
        """Tidak ada assignment → tidak ada konflik."""
        results = _engine().check_lecturer_double([])
        assert results == []

    def test_multiple_conflicts_different_dosen(self):
        """Dua dosen berbeda masing-masing double-booked → dua ConflictResult."""
        d1 = _make_dosen("Dr. A", "A")
        d2 = _make_dosen("Dr. B", "B")
        ts = _make_timeslot("Jumat 10:00")
        mk1 = _make_mk_kelas("MK1-A")
        mk2 = _make_mk_kelas("MK1-B")
        mk3 = _make_mk_kelas("MK2-A")
        mk4 = _make_mk_kelas("MK2-B")
        a1 = _make_assignment(d1, ts, mk1)
        a2 = _make_assignment(d1, ts, mk2)
        a3 = _make_assignment(d2, ts, mk3)
        a4 = _make_assignment(d2, ts, mk4)

        results = _engine().check_lecturer_double([a1, a2, a3, a4])

        assert len(results) == 2
        conflict_dosen_ids = {r.detail["dosen_id"] for r in results}
        assert str(d1.id) in conflict_dosen_ids
        assert str(d2.id) in conflict_dosen_ids

    def test_conflict_result_contains_mk_labels(self):
        """detail harus menyertakan mk_kelas_labels dari semua assignment yang terlibat."""
        d1 = _make_dosen("Dr. Fani", "FAN")
        ts = _make_timeslot("Senin 13:00")
        mk1 = _make_mk_kelas("MAT501-A")
        mk2 = _make_mk_kelas("MAT501-B")
        a1 = _make_assignment(d1, ts, mk1)
        a2 = _make_assignment(d1, ts, mk2)

        results = _engine().check_lecturer_double([a1, a2])

        assert len(results) == 1
        labels = results[0].detail["mk_kelas_labels"]
        assert "MAT501-A" in labels
        assert "MAT501-B" in labels

    def test_no_duplicate_assignment_ids_in_result(self):
        """assignment_ids dalam ConflictResult tidak boleh duplikat."""
        d1 = _make_dosen("Dr. G", "G")
        ts = _make_timeslot()
        mk1 = _make_mk_kelas("MK-A")
        mk2 = _make_mk_kelas("MK-B")
        a1 = _make_assignment(d1, ts, mk1)
        a2 = _make_assignment(d1, ts, mk2)

        results = _engine().check_lecturer_double([a1, a2])

        assert len(results) == 1
        ids = results[0].assignment_ids
        assert len(ids) == len(set(ids))
