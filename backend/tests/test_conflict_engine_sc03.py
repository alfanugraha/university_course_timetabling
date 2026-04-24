"""
backend/tests/test_conflict_engine_sc03.py
Unit tests for ConflictEngine.check_lecturer_preference() — SC-03.

Validates: SC-03 — Preferensi hari mengajar dosen sebaiknya diprioritaskan;
WARNING LECTURER_PREFERENCE_VIOLATED jika preferensi tidak dipenuhi.
"""

import uuid
from unittest.mock import MagicMock, call

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


def _make_timeslot(label: str = "Senin 07:30–10:00") -> MagicMock:
    ts = MagicMock()
    ts.id = uuid.uuid4()
    ts.label = label
    ts.hari = label.split()[0]
    ts.sks = 3
    return ts


def _make_preference(
    dosen: MagicMock,
    sesi_id: uuid.UUID,
    timeslot: MagicMock,
    fase: str = "pre_schedule",
    is_violated: bool = False,
) -> MagicMock:
    pref = MagicMock()
    pref.id = uuid.uuid4()
    pref.dosen_id = dosen.id
    pref.sesi_id = sesi_id
    pref.timeslot_id = timeslot.id
    pref.fase = fase
    pref.is_violated = is_violated
    return pref


def _make_assignment(
    dosen1: MagicMock,
    timeslot: MagicMock,
    sesi_id: uuid.UUID,
    dosen2: MagicMock | None = None,
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.sesi_id = sesi_id
    a.dosen1 = dosen1
    a.dosen1_id = dosen1.id if dosen1 else None
    a.dosen2 = dosen2
    a.dosen2_id = dosen2.id if dosen2 else None
    a.timeslot = timeslot
    a.timeslot_id = timeslot.id
    return a


def _engine_with_prefs(prefs: list) -> ConflictEngine:
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = prefs
    db.add = MagicMock()
    db.commit = MagicMock()
    return ConflictEngine(db)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckLecturerPreference:

    def test_empty_assignments_returns_empty(self):
        engine = _engine_with_prefs([])
        assert engine.check_lecturer_preference([]) == []

    def test_no_preferences_no_conflict(self):
        """Tidak ada preferensi terdaftar → tidak ada konflik."""
        sesi_id = uuid.uuid4()
        d = _make_dosen()
        ts = _make_timeslot("Senin 07:30–10:00")
        a = _make_assignment(d, ts, sesi_id)

        engine = _engine_with_prefs([])
        assert engine.check_lecturer_preference([a]) == []

    def test_preference_fulfilled_no_conflict(self):
        """Dosen dijadwalkan di timeslot yang ia preferensikan → tidak ada konflik."""
        sesi_id = uuid.uuid4()
        d = _make_dosen("Dr. Ani", "ANI")
        ts = _make_timeslot("Senin 07:30–10:00")
        a = _make_assignment(d, ts, sesi_id)
        pref = _make_preference(d, sesi_id, ts)  # preferensi = timeslot yang sama

        engine = _engine_with_prefs([pref])
        results = engine.check_lecturer_preference([a])

        assert results == []
        # is_violated harus tetap False
        assert pref.is_violated == False

    def test_preference_violated_warns(self):
        """Dosen tidak dijadwalkan di timeslot yang ia preferensikan → WARNING."""
        sesi_id = uuid.uuid4()
        d = _make_dosen("Dr. Budi", "BUD")
        ts_actual = _make_timeslot("Rabu 07:30–10:00")
        ts_pref = _make_timeslot("Senin 07:30–10:00")  # timeslot berbeda
        a = _make_assignment(d, ts_actual, sesi_id)
        pref = _make_preference(d, sesi_id, ts_pref)

        engine = _engine_with_prefs([pref])
        results = engine.check_lecturer_preference([a])

        assert len(results) == 1
        r = results[0]
        assert r.jenis == ConflictJenis.LECTURER_PREFERENCE_VIOLATED
        assert r.severity == ConflictSeverity.WARNING
        assert pref.is_violated == True

    def test_is_violated_updated_in_db(self):
        """is_violated harus diupdate di DB saat preferensi dilanggar."""
        sesi_id = uuid.uuid4()
        d = _make_dosen()
        ts_actual = _make_timeslot("Rabu 07:30–10:00")
        ts_pref = _make_timeslot("Senin 07:30–10:00")
        a = _make_assignment(d, ts_actual, sesi_id)
        pref = _make_preference(d, sesi_id, ts_pref, is_violated=False)

        engine = _engine_with_prefs([pref])
        engine.check_lecturer_preference([a])

        assert pref.is_violated == True
        engine.db.add.assert_called()
        engine.db.commit.assert_called()

    def test_multiple_preferences_one_violated(self):
        """Dosen punya 2 preferensi, 1 dipenuhi dan 1 dilanggar → 1 WARNING."""
        sesi_id = uuid.uuid4()
        d = _make_dosen("Dr. Citra", "CTR")
        ts1 = _make_timeslot("Senin 07:30–10:00")
        ts2 = _make_timeslot("Selasa 07:30–10:00")
        ts_pref_violated = _make_timeslot("Rabu 07:30–10:00")

        a1 = _make_assignment(d, ts1, sesi_id)
        a2 = _make_assignment(d, ts2, sesi_id)

        pref_ok = _make_preference(d, sesi_id, ts1)          # dipenuhi
        pref_violated = _make_preference(d, sesi_id, ts_pref_violated)  # dilanggar

        engine = _engine_with_prefs([pref_ok, pref_violated])
        results = engine.check_lecturer_preference([a1, a2])

        assert len(results) == 1
        assert results[0].detail["timeslot_id"] == str(ts_pref_violated.id)

    def test_detail_contains_expected_fields(self):
        """detail harus memuat dosen_id, dosen_nama, preference_id, timeslot_id, fase."""
        sesi_id = uuid.uuid4()
        d = _make_dosen("Dr. Dian", "DIN")
        ts_actual = _make_timeslot("Kamis 07:30–10:00")
        ts_pref = _make_timeslot("Jumat 07:30–10:00")
        a = _make_assignment(d, ts_actual, sesi_id)
        pref = _make_preference(d, sesi_id, ts_pref, fase="post_draft")

        engine = _engine_with_prefs([pref])
        results = engine.check_lecturer_preference([a])

        assert len(results) == 1
        detail = results[0].detail
        assert detail["dosen_id"] == str(d.id)
        assert detail["dosen_nama"] == "Dr. Dian"
        assert detail["dosen_kode"] == "DIN"
        assert detail["preference_id"] == str(pref.id)
        assert detail["timeslot_id"] == str(ts_pref.id)
        assert detail["fase"] == "post_draft"

    def test_dosen2_preference_also_checked(self):
        """Preferensi dosen2 juga diperiksa."""
        sesi_id = uuid.uuid4()
        d1 = _make_dosen("Dr. Eko", "EKO")
        d2 = _make_dosen("Dr. Fani", "FAN")
        ts_actual = _make_timeslot("Senin 07:30–10:00")
        ts_pref = _make_timeslot("Jumat 07:30–10:00")
        a = _make_assignment(d1, ts_actual, sesi_id, dosen2=d2)
        pref = _make_preference(d2, sesi_id, ts_pref)

        engine = _engine_with_prefs([pref])
        results = engine.check_lecturer_preference([a])

        assert len(results) == 1
        assert results[0].detail["dosen_id"] == str(d2.id)

    def test_preference_already_violated_stays_violated(self):
        """Preferensi yang sudah is_violated=True dan masih dilanggar → tetap violated."""
        sesi_id = uuid.uuid4()
        d = _make_dosen()
        ts_actual = _make_timeslot("Rabu 07:30–10:00")
        ts_pref = _make_timeslot("Senin 07:30–10:00")
        a = _make_assignment(d, ts_actual, sesi_id)
        pref = _make_preference(d, sesi_id, ts_pref, is_violated=True)

        engine = _engine_with_prefs([pref])
        results = engine.check_lecturer_preference([a])

        assert len(results) == 1
        assert pref.is_violated == True
