"""
backend/tests/test_conflict_engine_integration.py

Integration test for ConflictEngine using real Excel data.

Reads the actual schedule Excel file (Genap 2025-2026), parses it into
in-memory mock assignment objects (no DB required), runs ConflictEngine
rule methods directly, and asserts that known conflicts detected manually
from the Excel appear with the correct severity.

Known conflicts verified manually:
  HC-01 LECTURER_DOUBLE (ERROR): 4 dosen double-booked
  HC-07 PARALLEL_MISMATCH (ERROR): 3 MK with parallel classes at different slots
  HC-08 STUDENT_DAILY_OVERLOAD (ERROR): S1 Mat Smt II on Senin (3+ MK)
  SC-01 STUDENT_CONFLICT (WARNING): multiple MK same prodi+semester at same slot
"""

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Excel file path — relative to this test file's location
# ---------------------------------------------------------------------------
_EXCEL_PATH = (
    Path(__file__).parent.parent.parent
    / "data_dukung_aktualisasi"
    / "Jadwal Kuliah Semester Sebelumnya"
    / "ED-8_Jadwal Kuliah Jurusan Matematika_Genap 2025-2026 v3.xlsx"
)

pytestmark = pytest.mark.skipif(
    not _EXCEL_PATH.exists(),
    reason=f"Excel file not found: {_EXCEL_PATH}",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VALID_HARI = {"Senin", "Selasa", "Rabu", "Kamis", "Jumat"}
VALID_WAKTU = {"07:30-10:00", "10:00-12:30", "10:05-12:35", "13:00-15:30"}

HARI_TO_DAY = {
    "Senin": "mon",
    "Selasa": "tue",
    "Rabu": "wed",
    "Kamis": "thu",
    "Jumat": "fri",
}

WAKTU_TO_SESI = {
    "07:30-10:00": "s1",
    "10:00-12:30": "s2",
    "10:05-12:35": "s2",
    "13:00-15:30": "s3",
}

# ---------------------------------------------------------------------------
# Mock factory helpers (same pattern as other unit tests)
# ---------------------------------------------------------------------------

def _make_timeslot(kode: str, hari: str, sesi: str, label: str) -> MagicMock:
    ts = MagicMock()
    ts.id = uuid.uuid4()
    ts.kode = kode
    ts.hari = hari
    ts.sesi = sesi
    ts.label = label
    ts.sks = 3
    return ts


def _make_dosen(nama: str) -> MagicMock:
    d = MagicMock()
    d.id = uuid.uuid4()
    d.nama = nama
    d.kode = nama[:3].upper()
    d.tgl_lahir = None
    return d


def _make_prodi(nama: str) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.nama = nama
    return p


def _make_mk(nama: str, prodi: MagicMock, semester: str, sks: int = 3) -> MagicMock:
    mk = MagicMock()
    mk.id = uuid.uuid4()
    mk.nama = nama
    mk.semester = semester
    mk.sks = sks
    mk.kurikulum = MagicMock()
    mk.kurikulum.prodi_id = prodi.id
    mk.kurikulum.prodi = prodi
    return mk


def _make_mk_kelas(mk: MagicMock, kelas: str | None = None) -> MagicMock:
    mkk = MagicMock()
    mkk.id = uuid.uuid4()
    mkk.mata_kuliah_id = mk.id
    mkk.mata_kuliah = mk
    mkk.kelas = kelas
    mkk.label = f"{mk.nama} {kelas or ''}".strip()
    return mkk


def _make_assignment(
    sesi_id: uuid.UUID,
    mk_kelas: MagicMock,
    dosen1: MagicMock,
    timeslot: MagicMock,
    dosen2: MagicMock | None = None,
    ruang: MagicMock | None = None,
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.sesi_id = sesi_id
    a.mk_kelas = mk_kelas
    a.mk_kelas_id = mk_kelas.id
    a.dosen1 = dosen1
    a.dosen1_id = dosen1.id
    a.dosen2 = dosen2
    a.dosen2_id = dosen2.id if dosen2 else None
    a.timeslot = timeslot
    a.timeslot_id = timeslot.id
    a.ruang = ruang
    a.ruang_id = ruang.id if ruang else None
    a.override_floor_priority = False
    return a


# ---------------------------------------------------------------------------
# Excel parser — builds mock objects from the real file
# ---------------------------------------------------------------------------

def _parse_excel() -> list[MagicMock]:
    """
    Parse the real Excel schedule file into a list of mock JadwalAssignment objects.

    Shared objects (timeslots, dosen, prodi, mk, mk_kelas) are keyed by their
    natural identifiers so that parallel classes share the same mata_kuliah mock,
    enabling HC-07 parallel mismatch detection.
    """
    import openpyxl  # noqa: PLC0415

    wb = openpyxl.load_workbook(str(_EXCEL_PATH), data_only=True)
    ws = wb["Jadwal Genap 2025 2026"]

    sesi_id = uuid.uuid4()

    # Shared registries
    timeslots: dict[str, MagicMock] = {}   # kode → timeslot
    dosens: dict[str, MagicMock] = {}      # nama → dosen
    prodis: dict[str, MagicMock] = {}      # nama → prodi
    mks: dict[tuple, MagicMock] = {}       # (mk_base_name, prodi_nama, smt) → mk
    mk_kelas_map: dict[tuple, MagicMock] = {}  # (mk_id, kelas) → mk_kelas

    assignments: list[MagicMock] = []

    for row in ws.iter_rows(min_row=10, values_only=True):
        hari = row[1]
        waktu = row[4]
        mk_nama = row[10]

        # Skip invalid rows
        if hari is None or (isinstance(hari, str) and hari.startswith("=")):
            continue
        if mk_nama is None or (isinstance(mk_nama, str) and mk_nama.startswith("=")):
            continue
        if hari not in VALID_HARI:
            continue
        if waktu not in VALID_WAKTU:
            continue

        prodi_nama = str(row[6]) if row[6] else "Unknown"
        kelas = str(row[12]) if row[12] else None
        smt = str(row[13]) if row[13] else "?"
        sks = int(row[15]) if row[15] else 3
        dosen1_nama = str(row[17]).strip() if row[17] else None
        dosen2_nama = str(row[18]).strip() if row[18] else None

        if not dosen1_nama:
            continue

        # --- Timeslot ---
        day = HARI_TO_DAY[hari]
        sesi = WAKTU_TO_SESI[waktu]
        ts_kode = f"{day}_{sesi}"
        if ts_kode not in timeslots:
            label = f"{hari} {waktu}"
            timeslots[ts_kode] = _make_timeslot(ts_kode, hari, sesi, label)
        timeslot = timeslots[ts_kode]

        # --- Prodi ---
        if prodi_nama not in prodis:
            prodis[prodi_nama] = _make_prodi(prodi_nama)
        prodi = prodis[prodi_nama]

        # --- MataKuliah — strip kelas suffix to get base name for grouping ---
        # e.g. "Aljabar Linear A" → base "Aljabar Linear" for parallel grouping
        mk_base = mk_nama
        if kelas and mk_nama.endswith(f" {kelas}"):
            mk_base = mk_nama[: -len(f" {kelas}")].strip()

        mk_key = (mk_base, prodi_nama, smt)
        if mk_key not in mks:
            mks[mk_key] = _make_mk(mk_base, prodi, smt, sks)
        mk = mks[mk_key]

        # --- MataKuliahKelas ---
        mkk_key = (mk.id, kelas)
        if mkk_key not in mk_kelas_map:
            mk_kelas_map[mkk_key] = _make_mk_kelas(mk, kelas)
        mk_kelas = mk_kelas_map[mkk_key]

        # --- Dosen ---
        if dosen1_nama not in dosens:
            dosens[dosen1_nama] = _make_dosen(dosen1_nama)
        dosen1 = dosens[dosen1_nama]

        dosen2 = None
        if dosen2_nama and dosen2_nama != dosen1_nama:
            if dosen2_nama not in dosens:
                dosens[dosen2_nama] = _make_dosen(dosen2_nama)
            dosen2 = dosens[dosen2_nama]

        assignments.append(
            _make_assignment(sesi_id, mk_kelas, dosen1, timeslot, dosen2)
        )

    return assignments


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestConflictEngineIntegration:
    """
    Integration tests for ConflictEngine using real Excel schedule data.

    Parses the actual Genap 2025-2026 schedule Excel file into mock assignment
    objects and runs ConflictEngine rule methods directly (no DB calls).
    Asserts that known conflicts detected manually from the Excel appear with
    the correct severity and conflict type.
    """

    @pytest.fixture(scope="class")
    def assignments(self):
        return _parse_excel()

    @pytest.fixture(scope="class")
    def engine(self):
        from app.services.conflict_engine import ConflictEngine
        return ConflictEngine(MagicMock())

    # ------------------------------------------------------------------
    # HC-01: LECTURER_DOUBLE
    # ------------------------------------------------------------------

    def test_hc01_rizka_amalia_senin_sesi2(self, assignments, engine):
        """Rizka Amalia Putri teaches both Statistika Kependudukan A and
        Algoritma dan Pemrograman A on Senin sesi 2 (10:05-12:35)."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity

        results = engine.check_lecturer_double(assignments)
        errors = [r for r in results if r.jenis == ConflictJenis.LECTURER_DOUBLE]

        dosen_names = {r.detail["dosen_nama"] for r in errors}
        assert any("Rizka" in name for name in dosen_names), (
            f"Expected Rizka Amalia Putri in LECTURER_DOUBLE conflicts, got: {dosen_names}"
        )

        rizka_conflicts = [
            r for r in errors if "Rizka" in r.detail["dosen_nama"]
        ]
        assert all(r.severity == ConflictSeverity.ERROR for r in rizka_conflicts)

    def test_hc01_imran_selasa_sesi3(self, assignments, engine):
        """Imran M. teaches both Metode Numerik Stat and Metode Numerik I B
        on Selasa sesi 3 (13:00-15:30)."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity

        results = engine.check_lecturer_double(assignments)
        errors = [r for r in results if r.jenis == ConflictJenis.LECTURER_DOUBLE]

        dosen_names = {r.detail["dosen_nama"] for r in errors}
        assert any("Imran" in name for name in dosen_names), (
            f"Expected Imran M. in LECTURER_DOUBLE conflicts, got: {dosen_names}"
        )

        imran_conflicts = [r for r in errors if "Imran" in r.detail["dosen_nama"]]
        assert all(r.severity == ConflictSeverity.ERROR for r in imran_conflicts)

    def test_hc01_susilawati_rabu_sesi1(self, assignments, engine):
        """Susilawati teaches both Pengantar Matematika Diskrit B and
        Aljabar Linear Elementer C on Rabu sesi 1 (07:30-10:00)."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity

        results = engine.check_lecturer_double(assignments)
        errors = [r for r in results if r.jenis == ConflictJenis.LECTURER_DOUBLE]

        dosen_names = {r.detail["dosen_nama"] for r in errors}
        assert any("Susilawati" in name for name in dosen_names), (
            f"Expected Susilawati in LECTURER_DOUBLE conflicts, got: {dosen_names}"
        )

        susi_conflicts = [r for r in errors if "Susilawati" in r.detail["dosen_nama"]]
        assert all(r.severity == ConflictSeverity.ERROR for r in susi_conflicts)

    def test_hc01_mashadi_kamis_sesi2(self, assignments, engine):
        """Mashadi teaches both Pengantar Analisis Real I A and B
        on Kamis sesi 2 (10:05-12:35)."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity

        results = engine.check_lecturer_double(assignments)
        errors = [r for r in results if r.jenis == ConflictJenis.LECTURER_DOUBLE]

        dosen_names = {r.detail["dosen_nama"] for r in errors}
        assert any("Mashadi" in name for name in dosen_names), (
            f"Expected Mashadi in LECTURER_DOUBLE conflicts, got: {dosen_names}"
        )

        mashadi_conflicts = [r for r in errors if "Mashadi" in r.detail["dosen_nama"]]
        assert all(r.severity == ConflictSeverity.ERROR for r in mashadi_conflicts)

    def test_hc01_at_least_four_lecturer_doubles(self, assignments, engine):
        """At least 4 distinct dosen double-booking conflicts are detected."""
        from app.services.conflict_engine import ConflictJenis

        results = engine.check_lecturer_double(assignments)
        errors = [r for r in results if r.jenis == ConflictJenis.LECTURER_DOUBLE]

        assert len(errors) >= 4, (
            f"Expected at least 4 LECTURER_DOUBLE conflicts, got {len(errors)}"
        )

    # ------------------------------------------------------------------
    # HC-07: PARALLEL_MISMATCH
    # ------------------------------------------------------------------

    def test_hc07_aljabar_linear_parallel_mismatch(self, assignments, engine):
        """Aljabar Linear (S1 Mat, Smt IV) classes A, B, C are at different slots."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity

        results = engine.check_parallel_mismatch(assignments)
        errors = [r for r in results if r.jenis == ConflictJenis.PARALLEL_MISMATCH]

        mk_names = {r.detail["mata_kuliah_nama"] for r in errors}
        assert any("Aljabar Linear" in name for name in mk_names), (
            f"Expected 'Aljabar Linear' in PARALLEL_MISMATCH conflicts, got: {mk_names}"
        )

        al_conflicts = [r for r in errors if "Aljabar Linear" in r.detail["mata_kuliah_nama"]]
        assert all(r.severity == ConflictSeverity.ERROR for r in al_conflicts)

    def test_hc07_algoritma_pemrograman_stat_parallel_mismatch(self, assignments, engine):
        """Algoritma dan Pemrograman (S1 Stat, Smt II) classes A-E are at different slots."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity

        results = engine.check_parallel_mismatch(assignments)
        errors = [r for r in results if r.jenis == ConflictJenis.PARALLEL_MISMATCH]

        mk_names = {r.detail["mata_kuliah_nama"] for r in errors}
        assert any("Algoritma dan Pemrograman" in name for name in mk_names), (
            f"Expected 'Algoritma dan Pemrograman' in PARALLEL_MISMATCH conflicts, got: {mk_names}"
        )

    def test_hc07_pengantar_algoritma_mat_parallel_mismatch(self, assignments, engine):
        """Pengantar Algoritma dan Pemrograman (S1 Mat, Smt II) classes A-E at different slots."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity

        results = engine.check_parallel_mismatch(assignments)
        errors = [r for r in results if r.jenis == ConflictJenis.PARALLEL_MISMATCH]

        mk_names = {r.detail["mata_kuliah_nama"] for r in errors}
        assert any("Pengantar Algoritma" in name for name in mk_names), (
            f"Expected 'Pengantar Algoritma' in PARALLEL_MISMATCH conflicts, got: {mk_names}"
        )

    def test_hc07_at_least_three_parallel_mismatches(self, assignments, engine):
        """At least 3 distinct PARALLEL_MISMATCH conflicts are detected."""
        from app.services.conflict_engine import ConflictJenis

        results = engine.check_parallel_mismatch(assignments)
        errors = [r for r in results if r.jenis == ConflictJenis.PARALLEL_MISMATCH]

        assert len(errors) >= 3, (
            f"Expected at least 3 PARALLEL_MISMATCH conflicts, got {len(errors)}"
        )

    # ------------------------------------------------------------------
    # HC-08: STUDENT_DAILY_OVERLOAD
    # ------------------------------------------------------------------

    def test_hc08_s1_mat_smt2_senin_overload(self, assignments, engine):
        """S1 Mat Smt II on Senin has Kalkulus Integral A/B/C + Aljabar Linear Elementer B
        = 4 distinct MK → exceeds 2 MK/day limit."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity

        results = engine.check_student_daily_load(assignments)
        errors = [r for r in results if r.jenis == ConflictJenis.STUDENT_DAILY_OVERLOAD]

        # Find the S1 Mat Smt II Senin overload
        target = [
            r for r in errors
            if r.detail["semester"] == "II"
            and r.detail["hari"] == "Senin"
            and "Mat" in r.detail["prodi_nama"]
        ]
        assert len(target) >= 1, (
            f"Expected STUDENT_DAILY_OVERLOAD for S1 Mat Smt II on Senin. "
            f"All overloads: {[(r.detail['prodi_nama'], r.detail['semester'], r.detail['hari']) for r in errors]}"
        )
        assert all(r.severity == ConflictSeverity.ERROR for r in target)
        # Should have more than 2 MK
        assert any(r.detail["jumlah_mk"] > 2 for r in target)

    def test_hc08_at_least_one_overload(self, assignments, engine):
        """At least one STUDENT_DAILY_OVERLOAD is detected."""
        from app.services.conflict_engine import ConflictJenis

        results = engine.check_student_daily_load(assignments)
        errors = [r for r in results if r.jenis == ConflictJenis.STUDENT_DAILY_OVERLOAD]

        assert len(errors) >= 1, "Expected at least 1 STUDENT_DAILY_OVERLOAD conflict"

    # ------------------------------------------------------------------
    # SC-01: STUDENT_CONFLICT
    # ------------------------------------------------------------------

    def test_sc01_student_conflicts_detected(self, assignments, engine):
        """Multiple MK from same prodi+semester at same timeslot → WARNING STUDENT_CONFLICT."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity

        results = engine.check_student_conflict(assignments)
        warnings = [r for r in results if r.jenis == ConflictJenis.STUDENT_CONFLICT]

        assert len(warnings) >= 1, (
            "Expected at least 1 STUDENT_CONFLICT warning from the real schedule"
        )
        assert all(r.severity == ConflictSeverity.WARNING for r in warnings)

    def test_sc01_severity_is_warning_not_error(self, assignments, engine):
        """SC-01 must be WARNING, not ERROR."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity

        results = engine.check_student_conflict(assignments)
        for r in results:
            if r.jenis == ConflictJenis.STUDENT_CONFLICT:
                assert r.severity == ConflictSeverity.WARNING, (
                    f"STUDENT_CONFLICT should be WARNING, got {r.severity}"
                )

    # ------------------------------------------------------------------
    # Sanity checks
    # ------------------------------------------------------------------

    def test_assignments_parsed_correctly(self, assignments):
        """Verify the Excel was parsed into a reasonable number of assignments."""
        assert len(assignments) >= 80, (
            f"Expected at least 80 assignments from the Excel, got {len(assignments)}"
        )

    def test_all_assignments_have_timeslot(self, assignments):
        """Every parsed assignment must have a timeslot."""
        for a in assignments:
            assert a.timeslot is not None
            assert a.timeslot_id is not None

    def test_all_assignments_have_dosen1(self, assignments):
        """Every parsed assignment must have dosen1."""
        for a in assignments:
            assert a.dosen1 is not None
            assert a.dosen1_id is not None
