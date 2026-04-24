"""
backend/tests/test_conflict_engine_hc06.py
Unit tests for ConflictEngine.check_lecturer_unavail() — HC-06.

Validates: Requirements HC-06 — Dosen tidak boleh dijadwalkan di slot
yang ia tandai tidak tersedia (dosen_unavailability).
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


def _make_unavail_record(
    dosen_id: uuid.UUID,
    timeslot_id: uuid.UUID,
    sesi_id: uuid.UUID | None = None,
) -> MagicMock:
    rec = MagicMock()
    rec.dosen_id = dosen_id
    rec.timeslot_id = timeslot_id
    rec.sesi_id = sesi_id
    return rec


def _engine_with_unavail(unavail_records: list) -> ConflictEngine:
    """Buat ConflictEngine dengan DB mock yang mengembalikan unavail_records."""
    db = MagicMock()
    # Mock chained query: db.query(...).filter(...).all() → unavail_records
    db.query.return_value.filter.return_value.all.return_value = unavail_records
    return ConflictEngine(db)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckLecturerUnavail:

    def test_empty_assignments_returns_empty(self):
        """Tidak ada assignment → tidak ada konflik."""
        engine = _engine_with_unavail([])
        results = engine.check_lecturer_unavail([])
        assert results == []

    def test_no_unavailability_records_no_conflict(self):
        """Tidak ada rekaman unavailability → tidak ada konflik."""
        ts = _make_timeslot()
        d1 = _make_dosen()
        mk = _make_mk_kelas()
        sesi_id = uuid.uuid4()
        a = _make_assignment(d1, ts, mk, sesi_id=sesi_id)

        engine = _engine_with_unavail([])
        results = engine.check_lecturer_unavail([a])

        assert results == []

    def test_dosen1_unavailable_at_timeslot_raises_error(self):
        """dosen1 ditandai tidak tersedia di timeslot assignment → ERROR LECTURER_UNAVAILABLE."""
        ts = _make_timeslot("Senin 07:30–10:00")
        d1 = _make_dosen("Dr. Ani", "ANI")
        mk = _make_mk_kelas("MAT101-A")
        sesi_id = uuid.uuid4()
        a = _make_assignment(d1, ts, mk, sesi_id=sesi_id)

        unavail = _make_unavail_record(d1.id, ts.id, sesi_id=None)
        engine = _engine_with_unavail([unavail])
        results = engine.check_lecturer_unavail([a])

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.LECTURER_UNAVAILABLE
        assert r.severity == ConflictSeverity.ERROR
        assert a.id in r.assignment_ids
        assert "Ani" in r.pesan or "ANI" in r.pesan
        assert "Senin 07:30" in r.pesan
        assert r.detail["role"] == "dosen1"
        assert r.detail["dosen_id"] == str(d1.id)

    def test_dosen2_unavailable_at_timeslot_raises_error(self):
        """dosen2 ditandai tidak tersedia di timeslot assignment → ERROR LECTURER_UNAVAILABLE."""
        ts = _make_timeslot("Selasa 10:00–12:30")
        d1 = _make_dosen("Dr. Budi", "BUD")
        d2 = _make_dosen("Dr. Citra", "CTR")
        mk = _make_mk_kelas("MAT201-A")
        sesi_id = uuid.uuid4()
        a = _make_assignment(d1, ts, mk, dosen2=d2, sesi_id=sesi_id)

        unavail = _make_unavail_record(d2.id, ts.id, sesi_id=None)
        engine = _engine_with_unavail([unavail])
        results = engine.check_lecturer_unavail([a])

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.LECTURER_UNAVAILABLE
        assert r.severity == ConflictSeverity.ERROR
        assert r.detail["role"] == "dosen2"
        assert r.detail["dosen_id"] == str(d2.id)
        assert "Citra" in r.pesan or "CTR" in r.pesan

    def test_both_dosen1_and_dosen2_unavailable_returns_two_conflicts(self):
        """Baik dosen1 maupun dosen2 tidak tersedia → dua ConflictResult terpisah."""
        ts = _make_timeslot("Rabu 13:00–15:30")
        d1 = _make_dosen("Dr. Dian", "DIN")
        d2 = _make_dosen("Dr. Eko", "EKO")
        mk = _make_mk_kelas("MAT301-A")
        sesi_id = uuid.uuid4()
        a = _make_assignment(d1, ts, mk, dosen2=d2, sesi_id=sesi_id)

        unavail_d1 = _make_unavail_record(d1.id, ts.id, sesi_id=None)
        unavail_d2 = _make_unavail_record(d2.id, ts.id, sesi_id=None)
        engine = _engine_with_unavail([unavail_d1, unavail_d2])
        results = engine.check_lecturer_unavail([a])

        assert len(results) == 2
        roles = {r.detail["role"] for r in results}
        assert roles == {"dosen1", "dosen2"}

    def test_unavailability_null_sesi_applies_to_all_sessions(self):
        """sesi_id NULL pada unavailability berlaku untuk semua sesi."""
        ts = _make_timeslot("Kamis 07:30–10:00")
        d1 = _make_dosen("Dr. Fani", "FAN")
        mk = _make_mk_kelas("MAT401-A")
        sesi_id = uuid.uuid4()
        a = _make_assignment(d1, ts, mk, sesi_id=sesi_id)

        # sesi_id=None → berlaku semua sesi
        unavail = _make_unavail_record(d1.id, ts.id, sesi_id=None)
        engine = _engine_with_unavail([unavail])
        results = engine.check_lecturer_unavail([a])

        assert len(results) == 1
        assert results[0].jenis == ConflictJenis.LECTURER_UNAVAILABLE

    def test_unavailability_matching_sesi_applies(self):
        """sesi_id yang cocok pada unavailability juga memicu konflik."""
        ts = _make_timeslot("Jumat 10:00–12:30")
        d1 = _make_dosen("Dr. Gita", "GIT")
        mk = _make_mk_kelas("MAT501-A")
        sesi_id = uuid.uuid4()
        a = _make_assignment(d1, ts, mk, sesi_id=sesi_id)

        # sesi_id cocok dengan sesi assignment
        unavail = _make_unavail_record(d1.id, ts.id, sesi_id=sesi_id)
        engine = _engine_with_unavail([unavail])
        results = engine.check_lecturer_unavail([a])

        assert len(results) == 1

    def test_dosen_available_at_different_timeslot_no_conflict(self):
        """Unavailability di timeslot berbeda → tidak ada konflik."""
        ts_assigned = _make_timeslot("Senin 07:30–10:00")
        ts_unavail = _make_timeslot("Senin 10:00–12:30")
        d1 = _make_dosen("Dr. Hadi", "HAD")
        mk = _make_mk_kelas("MAT601-A")
        sesi_id = uuid.uuid4()
        a = _make_assignment(d1, ts_assigned, mk, sesi_id=sesi_id)

        # Unavailability di slot berbeda — tidak akan masuk unavail_set
        # karena (d1.id, ts_unavail.id) != (d1.id, ts_assigned.id)
        # Simulasikan: query mengembalikan record untuk ts_unavail
        unavail = _make_unavail_record(d1.id, ts_unavail.id, sesi_id=None)
        engine = _engine_with_unavail([unavail])
        results = engine.check_lecturer_unavail([a])

        assert results == []

    def test_dosen2_null_not_checked(self):
        """dosen2_id NULL tidak menyebabkan false positive."""
        ts = _make_timeslot()
        d1 = _make_dosen("Dr. Irma", "IRM")
        mk = _make_mk_kelas("MAT701-A")
        sesi_id = uuid.uuid4()
        a = _make_assignment(d1, ts, mk, dosen2=None, sesi_id=sesi_id)

        # Tidak ada unavailability untuk d1
        engine = _engine_with_unavail([])
        results = engine.check_lecturer_unavail([a])

        assert results == []

    def test_conflict_detail_contains_expected_fields(self):
        """detail ConflictResult harus memuat semua field yang diharapkan."""
        ts = _make_timeslot("Senin 07:30–10:00")
        d1 = _make_dosen("Dr. Joko", "JOK")
        mk = _make_mk_kelas("MAT801-A")
        sesi_id = uuid.uuid4()
        a = _make_assignment(d1, ts, mk, sesi_id=sesi_id)

        unavail = _make_unavail_record(d1.id, ts.id, sesi_id=None)
        engine = _engine_with_unavail([unavail])
        results = engine.check_lecturer_unavail([a])

        assert len(results) == 1
        detail = results[0].detail
        assert "dosen_id" in detail
        assert "dosen_nama" in detail
        assert "dosen_kode" in detail
        assert "role" in detail
        assert "timeslot_id" in detail
        assert "timeslot_label" in detail
        assert "mk_kelas_label" in detail
        assert detail["dosen_nama"] == "Dr. Joko"
        assert detail["dosen_kode"] == "JOK"
        assert detail["mk_kelas_label"] == "MAT801-A"

    def test_multiple_assignments_only_conflicting_ones_flagged(self):
        """Hanya assignment yang melanggar unavailability yang di-flag."""
        ts1 = _make_timeslot("Senin 07:30–10:00")
        ts2 = _make_timeslot("Senin 10:00–12:30")
        d1 = _make_dosen("Dr. Kiki", "KIK")
        d2 = _make_dosen("Dr. Lina", "LIN")
        mk1 = _make_mk_kelas("MAT901-A")
        mk2 = _make_mk_kelas("MAT902-A")
        sesi_id = uuid.uuid4()

        a1 = _make_assignment(d1, ts1, mk1, sesi_id=sesi_id)  # d1 unavail di ts1
        a2 = _make_assignment(d2, ts2, mk2, sesi_id=sesi_id)  # d2 tersedia di ts2

        # Hanya d1 tidak tersedia di ts1
        unavail = _make_unavail_record(d1.id, ts1.id, sesi_id=None)
        engine = _engine_with_unavail([unavail])
        results = engine.check_lecturer_unavail([a1, a2])

        assert len(results) == 1
        assert results[0].detail["dosen_id"] == str(d1.id)
