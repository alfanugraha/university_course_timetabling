"""
backend/tests/test_conflict_engine_hc02.py
Unit tests for ConflictEngine.check_room_double() — HC-02.

Validates: Requirements HC-02 — Ruang tidak boleh dipakai dua kelas
di timeslot yang sama dalam satu sesi. Hanya diperiksa jika ruang_id tidak NULL.
"""

import uuid
from unittest.mock import MagicMock

from app.services.conflict_engine import ConflictEngine, ConflictJenis, ConflictSeverity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_timeslot(label: str = "Senin 07:30–10:00") -> MagicMock:
    ts = MagicMock()
    ts.id = uuid.uuid4()
    ts.label = label
    return ts


def _make_ruang(nama: str = "G.1.01") -> MagicMock:
    r = MagicMock()
    r.id = uuid.uuid4()
    r.nama = nama
    return r


def _make_dosen(nama: str = "Dr. Budi") -> MagicMock:
    d = MagicMock()
    d.id = uuid.uuid4()
    d.nama = nama
    return d


def _make_mk_kelas(label: str = "MAT101-A") -> MagicMock:
    mk = MagicMock()
    mk.id = uuid.uuid4()
    mk.label = label
    return mk


def _make_assignment(
    timeslot: MagicMock,
    mk_kelas: MagicMock,
    ruang: MagicMock | None = None,
    sesi_id: uuid.UUID | None = None,
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.sesi_id = sesi_id or uuid.uuid4()
    a.timeslot = timeslot
    a.timeslot_id = timeslot.id
    a.ruang = ruang
    a.ruang_id = ruang.id if ruang else None
    a.mk_kelas = mk_kelas
    a.mk_kelas_id = mk_kelas.id
    a.dosen1 = _make_dosen()
    a.dosen1_id = a.dosen1.id
    a.dosen2 = None
    a.dosen2_id = None
    return a


def _engine() -> ConflictEngine:
    db = MagicMock()
    return ConflictEngine(db)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckRoomDouble:

    def test_no_conflict_single_assignment(self):
        """Satu assignment saja — tidak ada konflik."""
        ts = _make_timeslot()
        ruang = _make_ruang()
        mk = _make_mk_kelas()
        assignments = [_make_assignment(ts, mk, ruang)]

        results = _engine().check_room_double(assignments)

        assert results == []

    def test_no_conflict_different_timeslots(self):
        """Ruang yang sama di timeslot berbeda — tidak ada konflik."""
        ruang = _make_ruang("G.1.01")
        ts1 = _make_timeslot("Senin 07:30")
        ts2 = _make_timeslot("Senin 10:00")
        mk1 = _make_mk_kelas("MAT101-A")
        mk2 = _make_mk_kelas("MAT102-A")
        assignments = [
            _make_assignment(ts1, mk1, ruang),
            _make_assignment(ts2, mk2, ruang),
        ]

        results = _engine().check_room_double(assignments)

        assert results == []

    def test_no_conflict_different_rooms(self):
        """Timeslot yang sama tapi ruang berbeda — tidak ada konflik."""
        ts = _make_timeslot("Senin 07:30")
        ruang1 = _make_ruang("G.1.01")
        ruang2 = _make_ruang("G.1.02")
        mk1 = _make_mk_kelas("MAT101-A")
        mk2 = _make_mk_kelas("MAT102-A")
        assignments = [
            _make_assignment(ts, mk1, ruang1),
            _make_assignment(ts, mk2, ruang2),
        ]

        results = _engine().check_room_double(assignments)

        assert results == []

    def test_conflict_same_room_same_timeslot(self):
        """Dua assignment di ruang dan timeslot yang sama → ERROR ROOM_DOUBLE."""
        ts = _make_timeslot("Senin 07:30–10:00")
        ruang = _make_ruang("G.1.01")
        mk1 = _make_mk_kelas("MAT101-A")
        mk2 = _make_mk_kelas("MAT102-A")
        a1 = _make_assignment(ts, mk1, ruang)
        a2 = _make_assignment(ts, mk2, ruang)

        results = _engine().check_room_double([a1, a2])

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.ROOM_DOUBLE
        assert r.severity == ConflictSeverity.ERROR
        assert set(r.assignment_ids) == {a1.id, a2.id}

    def test_conflict_pesan_contains_room_and_timeslot(self):
        """Pesan konflik harus menyebut nama ruang dan label timeslot."""
        ts = _make_timeslot("Selasa 10:00–12:30")
        ruang = _make_ruang("G.2.05")
        mk1 = _make_mk_kelas("MAT201-A")
        mk2 = _make_mk_kelas("MAT201-B")
        a1 = _make_assignment(ts, mk1, ruang)
        a2 = _make_assignment(ts, mk2, ruang)

        results = _engine().check_room_double([a1, a2])

        assert len(results) == 1
        assert "G.2.05" in results[0].pesan
        assert "Selasa 10:00–12:30" in results[0].pesan

    def test_conflict_detail_structure(self):
        """detail JSONB harus memuat ruang_id, ruang_nama, timeslot_id, timeslot_label, mk_kelas_labels."""
        ts = _make_timeslot("Rabu 13:00–15:30")
        ruang = _make_ruang("G.3.01")
        mk1 = _make_mk_kelas("MAT301-A")
        mk2 = _make_mk_kelas("MAT301-B")
        a1 = _make_assignment(ts, mk1, ruang)
        a2 = _make_assignment(ts, mk2, ruang)

        results = _engine().check_room_double([a1, a2])

        assert len(results) == 1
        detail = results[0].detail
        assert detail["ruang_id"] == str(ruang.id)
        assert detail["ruang_nama"] == "G.3.01"
        assert detail["timeslot_id"] == str(ts.id)
        assert detail["timeslot_label"] == "Rabu 13:00–15:30"
        assert "MAT301-A" in detail["mk_kelas_labels"]
        assert "MAT301-B" in detail["mk_kelas_labels"]

    def test_no_conflict_when_ruang_id_is_null(self):
        """Assignment dengan ruang_id NULL dilewati — tidak ada konflik HC-02."""
        ts = _make_timeslot("Kamis 07:30")
        mk1 = _make_mk_kelas("MAT401-A")
        mk2 = _make_mk_kelas("MAT401-B")
        # Both assignments have no room assigned
        a1 = _make_assignment(ts, mk1, ruang=None)
        a2 = _make_assignment(ts, mk2, ruang=None)

        results = _engine().check_room_double([a1, a2])

        assert results == []

    def test_no_conflict_mixed_null_and_non_null_different_rooms(self):
        """Satu assignment tanpa ruang, satu dengan ruang — tidak ada konflik."""
        ts = _make_timeslot("Jumat 10:00")
        ruang = _make_ruang("G.1.03")
        mk1 = _make_mk_kelas("MAT501-A")
        mk2 = _make_mk_kelas("MAT501-B")
        a1 = _make_assignment(ts, mk1, ruang=None)
        a2 = _make_assignment(ts, mk2, ruang)

        results = _engine().check_room_double([a1, a2])

        assert results == []

    def test_empty_assignments(self):
        """Tidak ada assignment → tidak ada konflik."""
        results = _engine().check_room_double([])
        assert results == []

    def test_multiple_conflicts_different_rooms(self):
        """Dua ruang berbeda masing-masing double-booked → dua ConflictResult."""
        ts = _make_timeslot("Senin 07:30")
        ruang1 = _make_ruang("G.1.01")
        ruang2 = _make_ruang("G.1.02")
        mk1 = _make_mk_kelas("MK1-A")
        mk2 = _make_mk_kelas("MK1-B")
        mk3 = _make_mk_kelas("MK2-A")
        mk4 = _make_mk_kelas("MK2-B")
        a1 = _make_assignment(ts, mk1, ruang1)
        a2 = _make_assignment(ts, mk2, ruang1)
        a3 = _make_assignment(ts, mk3, ruang2)
        a4 = _make_assignment(ts, mk4, ruang2)

        results = _engine().check_room_double([a1, a2, a3, a4])

        assert len(results) == 2
        conflict_room_ids = {r.detail["ruang_id"] for r in results}
        assert str(ruang1.id) in conflict_room_ids
        assert str(ruang2.id) in conflict_room_ids

    def test_three_assignments_same_room_timeslot(self):
        """Tiga assignment di ruang dan timeslot yang sama → satu ERROR dengan 3 assignment_ids."""
        ts = _make_timeslot("Selasa 07:30")
        ruang = _make_ruang("G.2.01")
        mk1 = _make_mk_kelas("MK-A")
        mk2 = _make_mk_kelas("MK-B")
        mk3 = _make_mk_kelas("MK-C")
        a1 = _make_assignment(ts, mk1, ruang)
        a2 = _make_assignment(ts, mk2, ruang)
        a3 = _make_assignment(ts, mk3, ruang)

        results = _engine().check_room_double([a1, a2, a3])

        assert len(results) == 1
        assert set(results[0].assignment_ids) == {a1.id, a2.id, a3.id}
