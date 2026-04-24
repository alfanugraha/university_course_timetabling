"""
backend/tests/test_conflict_engine_sc05.py
Unit tests for ConflictEngine.check_floor_priority() — SC-05.

Validates: SC-05 — Dosen senior diprioritaskan di lantai lebih rendah;
WARNING FLOOR_PRIORITY_VIOLATED jika dosen senior di lantai lebih tinggi.
"""

import uuid
from datetime import date
from unittest.mock import MagicMock

from app.services.conflict_engine import ConflictEngine, ConflictJenis, ConflictSeverity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dosen(nama: str, kode: str, tgl_lahir: date | None) -> MagicMock:
    d = MagicMock()
    d.id = uuid.uuid4()
    d.nama = nama
    d.kode = kode
    d.tgl_lahir = tgl_lahir
    return d


def _make_ruang(nama: str, lantai: int | None) -> MagicMock:
    r = MagicMock()
    r.id = uuid.uuid4()
    r.nama = nama
    r.lantai = lantai
    return r


def _make_timeslot(label: str = "Senin 07:30–10:00") -> MagicMock:
    ts = MagicMock()
    ts.id = uuid.uuid4()
    ts.label = label
    return ts


def _make_assignment(
    dosen1: MagicMock,
    ruang: MagicMock | None,
    timeslot: MagicMock,
    override_floor_priority: bool = False,
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.dosen1 = dosen1
    a.dosen1_id = dosen1.id if dosen1 else None
    a.ruang = ruang
    a.ruang_id = ruang.id if ruang else None
    a.timeslot = timeslot
    a.timeslot_id = timeslot.id
    a.override_floor_priority = override_floor_priority
    return a


def _engine() -> ConflictEngine:
    return ConflictEngine(MagicMock())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckFloorPriority:

    def test_empty_assignments_returns_empty(self):
        assert _engine().check_floor_priority([]) == []

    def test_single_assignment_no_conflict(self):
        """Hanya satu assignment → tidak ada pasangan untuk dibandingkan."""
        d = _make_dosen("Dr. Senior", "SEN", date(1965, 1, 1))
        r = _make_ruang("R101", lantai=1)
        ts = _make_timeslot()
        a = _make_assignment(d, r, ts)

        assert _engine().check_floor_priority([a]) == []

    def test_senior_lower_floor_no_conflict(self):
        """Dosen senior di lantai lebih rendah dari junior → tidak ada konflik."""
        ts = _make_timeslot("Senin 07:30–10:00")
        d_senior = _make_dosen("Dr. Senior", "SEN", date(1965, 1, 1))
        d_junior = _make_dosen("Dr. Junior", "JUN", date(1985, 1, 1))
        r_low = _make_ruang("R101", lantai=1)
        r_high = _make_ruang("R301", lantai=3)
        a_senior = _make_assignment(d_senior, r_low, ts)
        a_junior = _make_assignment(d_junior, r_high, ts)

        assert _engine().check_floor_priority([a_senior, a_junior]) == []

    def test_senior_higher_floor_warns(self):
        """Dosen senior di lantai lebih tinggi dari junior → WARNING FLOOR_PRIORITY_VIOLATED."""
        ts = _make_timeslot("Senin 07:30–10:00")
        d_senior = _make_dosen("Dr. Senior", "SEN", date(1965, 1, 1))
        d_junior = _make_dosen("Dr. Junior", "JUN", date(1985, 1, 1))
        r_high = _make_ruang("R301", lantai=3)
        r_low = _make_ruang("R101", lantai=1)
        a_senior = _make_assignment(d_senior, r_high, ts)   # senior di lantai 3 ← salah
        a_junior = _make_assignment(d_junior, r_low, ts)    # junior di lantai 1

        results = _engine().check_floor_priority([a_senior, a_junior])

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.FLOOR_PRIORITY_VIOLATED
        assert r.severity == ConflictSeverity.WARNING
        assert set(r.assignment_ids) == {a_senior.id, a_junior.id}

    def test_override_flag_skips_check(self):
        """override_floor_priority=TRUE → assignment dilewati, tidak ada WARNING."""
        ts = _make_timeslot()
        d_senior = _make_dosen("Dr. Senior", "SEN", date(1965, 1, 1))
        d_junior = _make_dosen("Dr. Junior", "JUN", date(1985, 1, 1))
        r_high = _make_ruang("R301", lantai=3)
        r_low = _make_ruang("R101", lantai=1)
        # Senior di lantai tinggi tapi override aktif
        a_senior = _make_assignment(d_senior, r_high, ts, override_floor_priority=True)
        a_junior = _make_assignment(d_junior, r_low, ts)

        assert _engine().check_floor_priority([a_senior, a_junior]) == []

    def test_no_ruang_skipped(self):
        """Assignment tanpa ruang_id dilewati."""
        ts = _make_timeslot()
        d_senior = _make_dosen("Dr. Senior", "SEN", date(1965, 1, 1))
        d_junior = _make_dosen("Dr. Junior", "JUN", date(1985, 1, 1))
        r_low = _make_ruang("R101", lantai=1)
        a_senior = _make_assignment(d_senior, None, ts)   # tanpa ruang
        a_junior = _make_assignment(d_junior, r_low, ts)

        assert _engine().check_floor_priority([a_senior, a_junior]) == []

    def test_ruang_lantai_null_skipped(self):
        """Ruang dengan lantai=NULL dilewati."""
        ts = _make_timeslot()
        d_senior = _make_dosen("Dr. Senior", "SEN", date(1965, 1, 1))
        d_junior = _make_dosen("Dr. Junior", "JUN", date(1985, 1, 1))
        r_null = _make_ruang("R-Unknown", lantai=None)
        r_low = _make_ruang("R101", lantai=1)
        a_senior = _make_assignment(d_senior, r_null, ts)
        a_junior = _make_assignment(d_junior, r_low, ts)

        assert _engine().check_floor_priority([a_senior, a_junior]) == []

    def test_dosen_no_tgl_lahir_skipped(self):
        """Dosen tanpa tgl_lahir dilewati."""
        ts = _make_timeslot()
        d_no_dob = _make_dosen("Dr. Unknown", "UNK", tgl_lahir=None)
        d_junior = _make_dosen("Dr. Junior", "JUN", date(1985, 1, 1))
        r_high = _make_ruang("R301", lantai=3)
        r_low = _make_ruang("R101", lantai=1)
        a_no_dob = _make_assignment(d_no_dob, r_high, ts)
        a_junior = _make_assignment(d_junior, r_low, ts)

        assert _engine().check_floor_priority([a_no_dob, a_junior]) == []

    def test_same_age_no_conflict(self):
        """Dosen dengan tgl_lahir sama → tidak ada pelanggaran."""
        ts = _make_timeslot()
        d1 = _make_dosen("Dr. A", "AAA", date(1975, 6, 15))
        d2 = _make_dosen("Dr. B", "BBB", date(1975, 6, 15))
        r_high = _make_ruang("R301", lantai=3)
        r_low = _make_ruang("R101", lantai=1)
        a1 = _make_assignment(d1, r_high, ts)
        a2 = _make_assignment(d2, r_low, ts)

        assert _engine().check_floor_priority([a1, a2]) == []

    def test_different_timeslot_no_comparison(self):
        """Assignment di timeslot berbeda tidak dibandingkan satu sama lain."""
        ts1 = _make_timeslot("Senin 07:30–10:00")
        ts2 = _make_timeslot("Senin 10:00–12:30")
        d_senior = _make_dosen("Dr. Senior", "SEN", date(1965, 1, 1))
        d_junior = _make_dosen("Dr. Junior", "JUN", date(1985, 1, 1))
        r_high = _make_ruang("R301", lantai=3)
        r_low = _make_ruang("R101", lantai=1)
        a_senior = _make_assignment(d_senior, r_high, ts1)
        a_junior = _make_assignment(d_junior, r_low, ts2)

        assert _engine().check_floor_priority([a_senior, a_junior]) == []

    def test_detail_contains_expected_fields(self):
        """detail harus memuat info senior dan junior dosen beserta lantai."""
        ts = _make_timeslot("Selasa 07:30–10:00")
        d_senior = _make_dosen("Dr. Senior", "SEN", date(1965, 3, 20))
        d_junior = _make_dosen("Dr. Junior", "JUN", date(1985, 7, 10))
        r_high = _make_ruang("R301", lantai=3)
        r_low = _make_ruang("R101", lantai=1)
        a_senior = _make_assignment(d_senior, r_high, ts)
        a_junior = _make_assignment(d_junior, r_low, ts)

        results = _engine().check_floor_priority([a_senior, a_junior])

        assert len(results) == 1
        d = results[0].detail
        assert d["senior_dosen_nama"] == "Dr. Senior"
        assert d["senior_lantai"] == 3
        assert d["junior_dosen_nama"] == "Dr. Junior"
        assert d["junior_lantai"] == 1
        assert "timeslot_label" in d

    def test_pesan_mentions_senior_junior_and_floors(self):
        """Pesan harus menyebut nama dosen senior, junior, dan lantai masing-masing."""
        ts = _make_timeslot("Rabu 07:30–10:00")
        d_senior = _make_dosen("Dr. Senior", "SEN", date(1960, 1, 1))
        d_junior = _make_dosen("Dr. Junior", "JUN", date(1990, 1, 1))
        r_high = _make_ruang("R401", lantai=4)
        r_low = _make_ruang("R101", lantai=1)
        a_senior = _make_assignment(d_senior, r_high, ts)
        a_junior = _make_assignment(d_junior, r_low, ts)

        results = _engine().check_floor_priority([a_senior, a_junior])

        assert len(results) == 1
        pesan = results[0].pesan
        assert "Senior" in pesan
        assert "Junior" in pesan
        assert "4" in pesan
        assert "1" in pesan
