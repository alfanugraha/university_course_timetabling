"""
backend/tests/test_e2e_workflow.py

T8.2.1 - End-to-End Workflow Validation
Sistem Penjadwalan Kuliah, Jurusan Matematika FMIPA UNRI

Full workflow test:
  1. Import master data from db.xlsx (prodi, dosen, ruang)
  2. Import jadwal historis from ED-8_Jadwal Kuliah Jurusan Matematika_Genap 2025-2026 v3.xlsx
  3. Run conflict detection (ConflictEngine on mock assignments parsed from real Excel)
  4. Verify known conflicts are detected with correct severity

Known conflicts verified manually from the Excel:
  HC-01 LECTURER_DOUBLE (ERROR): Rizka Amalia, Imran M., Susilawati, Mashadi
  HC-07 PARALLEL_MISMATCH (ERROR): Aljabar Linear, Algoritma dan Pemrograman, Pengantar Algoritma
  HC-08 STUDENT_DAILY_OVERLOAD (ERROR): S1 Mat Smt II on Senin (4 MK)
  HC-09 LECTURER_DAILY_OVERLOAD (ERROR): dosen with 3+ MK on same day
  SC-01 STUDENT_CONFLICT (WARNING): multiple MK same prodi+semester at same slot

Architecture:
  - Import pipeline: SQLite in-memory (mirrors test_import_integration.py pattern)
  - Conflict detection: mock assignment objects parsed from real Excel
    (mirrors test_conflict_engine_integration.py pattern)
  - Combined E2E: single test that runs full workflow and reports results
"""

from __future__ import annotations

import datetime
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import pytest
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, SmallInteger,
    String, Text, Time, UniqueConstraint, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

# Patch psycopg2 so app modules can be imported without a real PG driver
sys.modules.setdefault("psycopg2", MagicMock())
sys.modules.setdefault("psycopg2.extensions", MagicMock())

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent.parent.parent
_DB_XLSX = _ROOT / "data_dukung_aktualisasi" / "db.xlsx"
_JADWAL_XLSX = (
    _ROOT
    / "data_dukung_aktualisasi"
    / "Jadwal Kuliah Semester Sebelumnya"
    / "ED-8_Jadwal Kuliah Jurusan Matematika_Genap 2025-2026 v3.xlsx"
)

pytestmark = pytest.mark.skipif(
    not _DB_XLSX.exists() or not _JADWAL_XLSX.exists(),
    reason="Real Excel files not found -- skipping E2E workflow tests",
)


# ---------------------------------------------------------------------------
# Minimal SQLite-compatible ORM schema (mirrors test_import_integration.py)
# ---------------------------------------------------------------------------


class _Base(DeclarativeBase):
    pass


def _uuid4_str() -> str:
    return str(uuid.uuid4())


class _Prodi(_Base):
    __tablename__ = "prodi"
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    kode = Column(String(10), unique=True, nullable=False)
    strata = Column(String(5), nullable=False)
    nama = Column(String(100), nullable=False)
    singkat = Column(String(20), nullable=False)
    kategori = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    kurikulums = relationship("_Kurikulum", back_populates="prodi")


class _Kurikulum(_Base):
    __tablename__ = "kurikulum"
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    kode = Column(String(20), unique=True, nullable=False)
    tahun = Column(String(4), nullable=False)
    prodi_id = Column(String(36), ForeignKey("prodi.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    prodi = relationship("_Prodi", back_populates="kurikulums")
    mata_kuliahs = relationship("_MataKuliah", back_populates="kurikulum", cascade="all, delete-orphan")


class _MataKuliah(_Base):
    __tablename__ = "mata_kuliah"
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    kode = Column(String(20), nullable=False)
    kurikulum_id = Column(String(36), ForeignKey("kurikulum.id"), nullable=False)
    nama = Column(String(200), nullable=False)
    sks = Column(SmallInteger, nullable=False)
    semester = Column(SmallInteger, nullable=False)
    jenis = Column(String(10), nullable=False)
    prasyarat = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    __table_args__ = (UniqueConstraint("kode", "kurikulum_id", name="uq_mata_kuliah_kode_kurikulum"),)
    kurikulum = relationship("_Kurikulum", back_populates="mata_kuliahs")
    kelas_list = relationship("_MataKuliahKelas", back_populates="mata_kuliah", cascade="all, delete-orphan")


class _MataKuliahKelas(_Base):
    __tablename__ = "mata_kuliah_kelas"
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    mata_kuliah_id = Column(String(36), ForeignKey("mata_kuliah.id"), nullable=False)
    kelas = Column(String(5), nullable=True)
    label = Column(String(200), nullable=False)
    ket = Column(Text, nullable=True)
    __table_args__ = (UniqueConstraint("mata_kuliah_id", "kelas", name="uq_mk_kelas"),)
    mata_kuliah = relationship("_MataKuliah", back_populates="kelas_list")


class _Ruang(_Base):
    __tablename__ = "ruang"
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    nama = Column(String(20), unique=True, nullable=False)
    kapasitas = Column(SmallInteger, default=45, nullable=False)
    lantai = Column(SmallInteger, nullable=True)
    gedung = Column(String(100), nullable=True)
    jenis = Column(String(20), default="Kelas", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class _Dosen(_Base):
    __tablename__ = "dosen"
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    nidn = Column(String(20), unique=True, nullable=True)
    nip = Column(String(25), unique=True, nullable=True)
    kode = Column(String(10), unique=True, nullable=False)
    nama = Column(String(200), nullable=False)
    jabfung = Column(String(50), nullable=True)
    kjfd = Column(String(100), nullable=True)
    homebase_prodi_id = Column(String(36), ForeignKey("prodi.id"), nullable=True)
    tgl_lahir = Column(Date, nullable=True)
    status = Column(String(20), default="Aktif", nullable=False)


class _Timeslot(_Base):
    __tablename__ = "timeslot"
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    kode = Column(String(20), unique=True, nullable=False)
    hari = Column(String(10), nullable=False)
    sesi = Column(SmallInteger, nullable=False)
    jam_mulai = Column(Time, nullable=False)
    jam_selesai = Column(Time, nullable=False)
    label = Column(String(30), nullable=False)
    sks = Column(SmallInteger, nullable=False)


class _SesiJadwal(_Base):
    __tablename__ = "sesi_jadwal"
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    nama = Column(String(100), nullable=False)
    semester = Column(String(10), nullable=False)
    tahun_akademik = Column(String(10), nullable=False)
    status = Column(String(20), default="Draft", nullable=False)
    __table_args__ = (UniqueConstraint("semester", "tahun_akademik", name="uq_sesi_semester_tahun"),)


class _JadwalAssignment(_Base):
    __tablename__ = "jadwal_assignment"
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    sesi_id = Column(String(36), ForeignKey("sesi_jadwal.id"), nullable=False)
    mk_kelas_id = Column(String(36), ForeignKey("mata_kuliah_kelas.id"), nullable=False)
    dosen1_id = Column(String(36), ForeignKey("dosen.id"), nullable=False)
    dosen2_id = Column(String(36), ForeignKey("dosen.id"), nullable=True)
    timeslot_id = Column(String(36), ForeignKey("timeslot.id"), nullable=False)
    ruang_id = Column(String(36), ForeignKey("ruang.id"), nullable=True)
    override_floor_priority = Column(Boolean, default=False, nullable=False)
    catatan = Column(Text, nullable=True)
    __table_args__ = (UniqueConstraint("sesi_id", "mk_kelas_id", name="uq_assignment_sesi_mk_kelas"),)


# ---------------------------------------------------------------------------
# Timeslot seed data (15 fixed slots)
# ---------------------------------------------------------------------------

_TIMESLOT_SEED = [
    ("mon_s1", "Senin",  1, datetime.time(7, 30),  datetime.time(10, 0),  "Senin 07:30-10:00",  3),
    ("mon_s2", "Senin",  2, datetime.time(10, 0),  datetime.time(12, 30), "Senin 10:00-12:30",  3),
    ("mon_s3", "Senin",  3, datetime.time(13, 0),  datetime.time(15, 30), "Senin 13:00-15:30",  3),
    ("tue_s1", "Selasa", 1, datetime.time(7, 30),  datetime.time(10, 0),  "Selasa 07:30-10:00", 3),
    ("tue_s2", "Selasa", 2, datetime.time(10, 0),  datetime.time(12, 30), "Selasa 10:00-12:30", 3),
    ("tue_s3", "Selasa", 3, datetime.time(13, 0),  datetime.time(15, 30), "Selasa 13:00-15:30", 3),
    ("wed_s1", "Rabu",   1, datetime.time(7, 30),  datetime.time(10, 0),  "Rabu 07:30-10:00",   3),
    ("wed_s2", "Rabu",   2, datetime.time(10, 0),  datetime.time(12, 30), "Rabu 10:00-12:30",   3),
    ("wed_s3", "Rabu",   3, datetime.time(13, 0),  datetime.time(15, 30), "Rabu 13:00-15:30",   3),
    ("thu_s1", "Kamis",  1, datetime.time(7, 30),  datetime.time(10, 0),  "Kamis 07:30-10:00",  3),
    ("thu_s2", "Kamis",  2, datetime.time(10, 0),  datetime.time(12, 30), "Kamis 10:00-12:30",  3),
    ("thu_s3", "Kamis",  3, datetime.time(13, 0),  datetime.time(15, 30), "Kamis 13:00-15:30",  3),
    ("fri_s1", "Jumat",  1, datetime.time(7, 30),  datetime.time(10, 0),  "Jumat 07:30-10:00",  3),
    ("fri_s2", "Jumat",  2, datetime.time(10, 0),  datetime.time(12, 30), "Jumat 10:00-12:30",  3),
    ("fri_s3", "Jumat",  3, datetime.time(13, 0),  datetime.time(15, 30), "Jumat 13:00-15:30",  3),
]

# ---------------------------------------------------------------------------
# Constants for Excel parsing (mirrors test_conflict_engine_integration.py)
# ---------------------------------------------------------------------------

_VALID_HARI = {"Senin", "Selasa", "Rabu", "Kamis", "Jumat"}
_VALID_WAKTU = {"07:30-10:00", "10:00-12:30", "10:05-12:35", "13:00-15:30"}

_HARI_TO_DAY = {
    "Senin": "mon", "Selasa": "tue", "Rabu": "wed", "Kamis": "thu", "Jumat": "fri",
}

_WAKTU_TO_SESI = {
    "07:30-10:00": "s1",
    "10:00-12:30": "s2",
    "10:05-12:35": "s2",
    "13:00-15:30": "s3",
}

# ---------------------------------------------------------------------------
# Helper: patch importer module to use local SQLite models
# ---------------------------------------------------------------------------


def _patch_importer_models():
    import app.services.excel_importer as _ei
    _ei.Prodi = _Prodi
    _ei.Kurikulum = _Kurikulum
    _ei.MataKuliah = _MataKuliah
    _ei.MataKuliahKelas = _MataKuliahKelas
    _ei.Ruang = _Ruang
    _ei.Dosen = _Dosen
    _ei.Timeslot = _Timeslot
    _ei.JadwalAssignment = _JadwalAssignment


def _make_importer(session):
    from app.services.excel_importer import ExcelImporter
    _patch_importer_models()
    importer = ExcelImporter.__new__(ExcelImporter)
    importer.db_session = session
    return importer


# ---------------------------------------------------------------------------
# Mock factory helpers for conflict engine (no DB required)
# ---------------------------------------------------------------------------


def _make_ts_mock(kode: str, hari: str, sesi: str, label: str) -> MagicMock:
    ts = MagicMock()
    ts.id = uuid.uuid4()
    ts.kode = kode
    ts.hari = hari
    ts.sesi = sesi
    ts.label = label
    ts.sks = 3
    return ts


def _make_dosen_mock(nama: str) -> MagicMock:
    d = MagicMock()
    d.id = uuid.uuid4()
    d.nama = nama
    d.kode = nama[:3].upper()
    d.tgl_lahir = None
    return d


def _make_prodi_mock(nama: str) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.nama = nama
    return p


def _make_mk_mock(nama: str, prodi: MagicMock, semester: str, sks: int = 3) -> MagicMock:
    mk = MagicMock()
    mk.id = uuid.uuid4()
    mk.nama = nama
    mk.semester = semester
    mk.sks = sks
    mk.kurikulum = MagicMock()
    mk.kurikulum.prodi_id = prodi.id
    mk.kurikulum.prodi = prodi
    return mk


def _make_mk_kelas_mock(mk: MagicMock, kelas: Optional[str] = None) -> MagicMock:
    mkk = MagicMock()
    mkk.id = uuid.uuid4()
    mkk.mata_kuliah_id = mk.id
    mkk.mata_kuliah = mk
    mkk.kelas = kelas
    mkk.label = f"{mk.nama} {kelas or ''}".strip()
    return mkk


def _make_assignment_mock(
    sesi_id: uuid.UUID,
    mk_kelas: MagicMock,
    dosen1: MagicMock,
    timeslot: MagicMock,
    dosen2: Optional[MagicMock] = None,
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
    a.ruang = None
    a.ruang_id = None
    a.override_floor_priority = False
    return a


# ---------------------------------------------------------------------------
# Excel parser — builds mock assignment objects from the real jadwal file
# (same approach as test_conflict_engine_integration.py)
# ---------------------------------------------------------------------------


def _parse_jadwal_excel() -> list[MagicMock]:
    """
    Parse the real Genap 2025-2026 schedule Excel into mock JadwalAssignment objects.

    Shared objects (timeslots, dosen, prodi, mk, mk_kelas) are keyed by their
    natural identifiers so that parallel classes share the same mata_kuliah mock,
    enabling HC-07 parallel mismatch detection.
    """
    import openpyxl

    wb = openpyxl.load_workbook(str(_JADWAL_XLSX), data_only=True)
    ws = wb["Jadwal Genap 2025 2026"]

    sesi_id = uuid.uuid4()

    timeslots: dict[str, MagicMock] = {}
    dosens: dict[str, MagicMock] = {}
    prodis: dict[str, MagicMock] = {}
    mks: dict[tuple, MagicMock] = {}
    mk_kelas_map: dict[tuple, MagicMock] = {}

    assignments: list[MagicMock] = []

    for row in ws.iter_rows(min_row=10, values_only=True):
        hari = row[1]
        waktu = row[4]
        mk_nama = row[10]

        if hari is None or (isinstance(hari, str) and hari.startswith("=")):
            continue
        if mk_nama is None or (isinstance(mk_nama, str) and mk_nama.startswith("=")):
            continue
        if hari not in _VALID_HARI:
            continue
        if waktu not in _VALID_WAKTU:
            continue

        prodi_nama = str(row[6]) if row[6] else "Unknown"
        kelas = str(row[12]) if row[12] else None
        smt = str(row[13]) if row[13] else "?"
        sks = int(row[15]) if row[15] else 3
        dosen1_nama = str(row[17]).strip() if row[17] else None
        dosen2_nama = str(row[18]).strip() if row[18] else None

        if not dosen1_nama:
            continue

        # Timeslot
        day = _HARI_TO_DAY[hari]
        sesi = _WAKTU_TO_SESI[waktu]
        ts_kode = f"{day}_{sesi}"
        if ts_kode not in timeslots:
            timeslots[ts_kode] = _make_ts_mock(ts_kode, hari, sesi, f"{hari} {waktu}")
        timeslot = timeslots[ts_kode]

        # Prodi
        if prodi_nama not in prodis:
            prodis[prodi_nama] = _make_prodi_mock(prodi_nama)
        prodi = prodis[prodi_nama]

        # MataKuliah — strip kelas suffix to get base name for parallel grouping
        mk_base = mk_nama
        if kelas and mk_nama.endswith(f" {kelas}"):
            mk_base = mk_nama[: -len(f" {kelas}")].strip()

        mk_key = (mk_base, prodi_nama, smt)
        if mk_key not in mks:
            mks[mk_key] = _make_mk_mock(mk_base, prodi, smt, sks)
        mk = mks[mk_key]

        # MataKuliahKelas
        mkk_key = (mk.id, kelas)
        if mkk_key not in mk_kelas_map:
            mk_kelas_map[mkk_key] = _make_mk_kelas_mock(mk, kelas)
        mk_kelas = mk_kelas_map[mkk_key]

        # Dosen
        if dosen1_nama not in dosens:
            dosens[dosen1_nama] = _make_dosen_mock(dosen1_nama)
        dosen1 = dosens[dosen1_nama]

        dosen2 = None
        if dosen2_nama and dosen2_nama != dosen1_nama:
            if dosen2_nama not in dosens:
                dosens[dosen2_nama] = _make_dosen_mock(dosen2_nama)
            dosen2 = dosens[dosen2_nama]

        assignments.append(
            _make_assignment_mock(sesi_id, mk_kelas, dosen1, timeslot, dosen2)
        )

    return assignments


# ---------------------------------------------------------------------------
# Module-scoped SQLite engine fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    _Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def db_session(sqlite_engine):
    SessionLocal = sessionmaker(bind=sqlite_engine)
    session = SessionLocal()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Phase 1: Import master data from db.xlsx
# ---------------------------------------------------------------------------


class TestPhase1ImportMaster:
    """
    Phase 1 of E2E workflow: import master data from db.xlsx.

    Verifies:
    - Import runs without crashing
    - Prodi records are created (8 unique prodi from 10 rows)
    - Dosen records are created (46 rows in sheet)
    - Ruang records are created (9 rows in sheet)
    - Accounting integrity: total == inserted + updated + skipped
    """

    @pytest.fixture(scope="class")
    def master_result(self, db_session):
        importer = _make_importer(db_session)
        result = importer.import_master_db(str(_DB_XLSX))
        return result

    def test_import_completes_without_exception(self, master_result):
        """Import master data runs end-to-end without raising exceptions."""
        from app.services.excel_importer import ImportResult
        assert isinstance(master_result, ImportResult)

    def test_import_total_positive(self, master_result):
        """At least some rows were processed."""
        assert master_result.total > 0, (
            f"Expected total > 0, got {master_result.total}"
        )

    def test_import_accounting_integrity(self, master_result):
        """total == inserted + updated + skipped."""
        r = master_result
        assert r.total == r.inserted + r.updated + r.skipped, (
            f"Accounting mismatch: total={r.total}, "
            f"inserted={r.inserted}, updated={r.updated}, skipped={r.skipped}"
        )

    def test_prodi_records_created(self, db_session, master_result):
        """8 unique prodi records created (3 rows share kode S1TEKN)."""
        count = db_session.query(_Prodi).count()
        assert count == 8, (
            f"Expected 8 prodi records (3 rows share kode S1TEKN), got {count}"
        )

    def test_dosen_records_created(self, db_session, master_result):
        """At least some dosen records created from Dosen sheet."""
        count = db_session.query(_Dosen).count()
        assert count > 0, f"Expected dosen records, got 0"

    def test_ruang_records_created(self, db_session, master_result):
        """9 ruang records created from Ruang Kuliah sheet."""
        count = db_session.query(_Ruang).count()
        assert count == 9, f"Expected 9 ruang records, got {count}"

    def test_warnings_have_correct_structure(self, master_result):
        """All warnings have required fields."""
        from app.services.excel_importer import ImportWarning
        for w in master_result.warnings:
            assert isinstance(w, ImportWarning)
            assert isinstance(w.row, int) and w.row >= 0
            assert isinstance(w.sheet, str) and w.sheet
            assert isinstance(w.reason, str) and w.reason


# ---------------------------------------------------------------------------
# Phase 2: Import jadwal historis
# ---------------------------------------------------------------------------


class TestPhase2ImportJadwal:
    """
    Phase 2 of E2E workflow: import jadwal historis from ED-8 Genap 2025-2026.

    The jadwal importer requires timeslots and a SesiJadwal to be present.
    MataKuliahKelas are not pre-seeded here (they depend on kurikulum which
    fails to import due to prodi name mismatch), so most rows will be skipped
    with warnings. The test verifies the import pipeline runs without crashing
    and accounting integrity holds.
    """

    @pytest.fixture(scope="class")
    def seeded_session(self, db_session):
        """Seed timeslots and a SesiJadwal for jadwal import."""
        for kode, hari, sesi, jam_mulai, jam_selesai, label, sks in _TIMESLOT_SEED:
            existing = db_session.query(_Timeslot).filter_by(kode=kode).first()
            if not existing:
                db_session.add(_Timeslot(
                    id=_uuid4_str(), kode=kode, hari=hari, sesi=sesi,
                    jam_mulai=jam_mulai, jam_selesai=jam_selesai,
                    label=label, sks=sks,
                ))
        sesi = db_session.query(_SesiJadwal).filter_by(
            semester="Genap", tahun_akademik="2025-2026"
        ).first()
        if not sesi:
            sesi = _SesiJadwal(
                id=_uuid4_str(),
                nama="Genap 2025-2026",
                semester="Genap",
                tahun_akademik="2025-2026",
                status="Draft",
            )
            db_session.add(sesi)
        db_session.commit()
        return db_session

    @pytest.fixture(scope="class")
    def jadwal_result(self, seeded_session):
        sesi = seeded_session.query(_SesiJadwal).filter_by(
            semester="Genap", tahun_akademik="2025-2026"
        ).first()
        importer = _make_importer(seeded_session)
        result = importer.import_jadwal(str(_JADWAL_XLSX), str(sesi.id))
        return result

    def test_jadwal_import_completes_without_exception(self, jadwal_result):
        """Jadwal import runs end-to-end without raising exceptions."""
        from app.services.excel_importer import ImportResult
        assert isinstance(jadwal_result, ImportResult)

    def test_jadwal_import_total_positive(self, jadwal_result):
        """At least some rows were processed from the jadwal Excel."""
        assert jadwal_result.total > 0, (
            f"Expected total > 0, got {jadwal_result.total}"
        )

    def test_jadwal_import_accounting_integrity(self, jadwal_result):
        """total == inserted + updated + skipped."""
        r = jadwal_result
        assert r.total == r.inserted + r.updated + r.skipped, (
            f"Accounting mismatch: total={r.total}, "
            f"inserted={r.inserted}, updated={r.updated}, skipped={r.skipped}"
        )

    def test_jadwal_warnings_for_unresolvable_rows(self, jadwal_result):
        """Skipped rows have corresponding warning entries."""
        assert len(jadwal_result.warnings) == jadwal_result.skipped, (
            f"Expected {jadwal_result.skipped} warnings for skipped rows, "
            f"got {len(jadwal_result.warnings)}"
        )

    def test_jadwal_warnings_have_correct_structure(self, jadwal_result):
        """All jadwal warnings have required fields."""
        from app.services.excel_importer import ImportWarning
        for w in jadwal_result.warnings:
            assert isinstance(w, ImportWarning)
            assert isinstance(w.row, int) and w.row > 0
            assert isinstance(w.sheet, str) and w.sheet
            assert isinstance(w.reason, str) and w.reason

    def test_jadwal_reimport_is_idempotent(self, seeded_session):
        """Re-importing the same file does not create duplicate assignments."""
        sesi = seeded_session.query(_SesiJadwal).filter_by(
            semester="Genap", tahun_akademik="2025-2026"
        ).first()
        count_before = seeded_session.query(_JadwalAssignment).filter_by(
            sesi_id=sesi.id
        ).count()
        importer = _make_importer(seeded_session)
        importer.import_jadwal(str(_JADWAL_XLSX), str(sesi.id))
        count_after = seeded_session.query(_JadwalAssignment).filter_by(
            sesi_id=sesi.id
        ).count()
        assert count_after == count_before, (
            f"Re-import created duplicates: before={count_before}, after={count_after}"
        )


# ---------------------------------------------------------------------------
# Phase 3: Conflict detection on mock assignments from real Excel
# ---------------------------------------------------------------------------


class TestPhase3ConflictDetection:
    """
    Phase 3 of E2E workflow: run ConflictEngine on mock assignments parsed
    from the real Genap 2025-2026 Excel file.

    Uses mock objects (no DB required) so conflict detection works even when
    the import pipeline cannot resolve MataKuliahKelas (due to missing kurikulum).

    Verifies all known conflicts detected manually from the Excel:
      HC-01 LECTURER_DOUBLE (ERROR): 4+ dosen double-booked
      HC-07 PARALLEL_MISMATCH (ERROR): 3+ MK with parallel classes at different slots
      HC-08 STUDENT_DAILY_OVERLOAD (ERROR): S1 Mat Smt II on Senin (4 MK)
      HC-09 LECTURER_DAILY_OVERLOAD (ERROR): dosen with 3+ MK on same day
      SC-01 STUDENT_CONFLICT (WARNING): multiple MK same prodi+semester at same slot
    """

    @pytest.fixture(scope="class")
    def assignments(self):
        return _parse_jadwal_excel()

    @pytest.fixture(scope="class")
    def engine(self):
        from app.services.conflict_engine import ConflictEngine
        return ConflictEngine(MagicMock())

    @pytest.fixture(scope="class")
    def all_conflicts(self, assignments, engine):
        """Run all conflict rules and collect results."""
        from app.services.conflict_engine import ConflictJenis
        results = []
        results += engine.check_lecturer_double(assignments)
        results += engine.check_room_double(assignments)
        results += engine.check_parallel_mismatch(assignments)
        results += engine.check_student_daily_load(assignments)
        results += engine.check_lecturer_daily_load(assignments)
        results += engine.check_student_conflict(assignments)
        return results

    # ------------------------------------------------------------------
    # Sanity: assignments parsed correctly
    # ------------------------------------------------------------------

    def test_assignments_parsed_from_excel(self, assignments):
        """At least 80 assignments parsed from the real Excel file."""
        assert len(assignments) >= 80, (
            f"Expected at least 80 assignments, got {len(assignments)}"
        )

    def test_all_assignments_have_timeslot(self, assignments):
        """Every assignment has a timeslot."""
        for a in assignments:
            assert a.timeslot is not None
            assert a.timeslot_id is not None

    def test_all_assignments_have_dosen1(self, assignments):
        """Every assignment has dosen1."""
        for a in assignments:
            assert a.dosen1 is not None
            assert a.dosen1_id is not None

    # ------------------------------------------------------------------
    # HC-01: LECTURER_DOUBLE
    # ------------------------------------------------------------------

    def test_hc01_lecturer_double_detected(self, all_conflicts):
        """At least 4 LECTURER_DOUBLE (ERROR) conflicts detected."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity
        errors = [r for r in all_conflicts if r.jenis == ConflictJenis.LECTURER_DOUBLE]
        assert len(errors) >= 4, (
            f"Expected at least 4 LECTURER_DOUBLE conflicts, got {len(errors)}"
        )
        assert all(r.severity == ConflictSeverity.ERROR for r in errors)

    def test_hc01_rizka_amalia_double_booked(self, all_conflicts):
        """Rizka Amalia Putri is double-booked (Senin sesi 2)."""
        from app.services.conflict_engine import ConflictJenis
        errors = [r for r in all_conflicts if r.jenis == ConflictJenis.LECTURER_DOUBLE]
        dosen_names = {r.detail["dosen_nama"] for r in errors}
        assert any("Rizka" in name for name in dosen_names), (
            f"Expected Rizka Amalia in LECTURER_DOUBLE, got: {dosen_names}"
        )

    def test_hc01_imran_double_booked(self, all_conflicts):
        """Imran M. is double-booked (Selasa sesi 3)."""
        from app.services.conflict_engine import ConflictJenis
        errors = [r for r in all_conflicts if r.jenis == ConflictJenis.LECTURER_DOUBLE]
        dosen_names = {r.detail["dosen_nama"] for r in errors}
        assert any("Imran" in name for name in dosen_names), (
            f"Expected Imran M. in LECTURER_DOUBLE, got: {dosen_names}"
        )

    def test_hc01_susilawati_double_booked(self, all_conflicts):
        """Susilawati is double-booked (Rabu sesi 1)."""
        from app.services.conflict_engine import ConflictJenis
        errors = [r for r in all_conflicts if r.jenis == ConflictJenis.LECTURER_DOUBLE]
        dosen_names = {r.detail["dosen_nama"] for r in errors}
        assert any("Susilawati" in name for name in dosen_names), (
            f"Expected Susilawati in LECTURER_DOUBLE, got: {dosen_names}"
        )

    def test_hc01_mashadi_double_booked(self, all_conflicts):
        """Mashadi is double-booked (Kamis sesi 2)."""
        from app.services.conflict_engine import ConflictJenis
        errors = [r for r in all_conflicts if r.jenis == ConflictJenis.LECTURER_DOUBLE]
        dosen_names = {r.detail["dosen_nama"] for r in errors}
        assert any("Mashadi" in name for name in dosen_names), (
            f"Expected Mashadi in LECTURER_DOUBLE, got: {dosen_names}"
        )

    # ------------------------------------------------------------------
    # HC-07: PARALLEL_MISMATCH
    # ------------------------------------------------------------------

    def test_hc07_parallel_mismatch_detected(self, all_conflicts):
        """At least 3 PARALLEL_MISMATCH (ERROR) conflicts detected."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity
        errors = [r for r in all_conflicts if r.jenis == ConflictJenis.PARALLEL_MISMATCH]
        assert len(errors) >= 3, (
            f"Expected at least 3 PARALLEL_MISMATCH conflicts, got {len(errors)}"
        )
        assert all(r.severity == ConflictSeverity.ERROR for r in errors)

    def test_hc07_aljabar_linear_mismatch(self, all_conflicts):
        """Aljabar Linear parallel classes are at different slots."""
        from app.services.conflict_engine import ConflictJenis
        errors = [r for r in all_conflicts if r.jenis == ConflictJenis.PARALLEL_MISMATCH]
        mk_names = {r.detail["mata_kuliah_nama"] for r in errors}
        assert any("Aljabar Linear" in name for name in mk_names), (
            f"Expected 'Aljabar Linear' in PARALLEL_MISMATCH, got: {mk_names}"
        )

    def test_hc07_algoritma_pemrograman_mismatch(self, all_conflicts):
        """Algoritma dan Pemrograman parallel classes are at different slots."""
        from app.services.conflict_engine import ConflictJenis
        errors = [r for r in all_conflicts if r.jenis == ConflictJenis.PARALLEL_MISMATCH]
        mk_names = {r.detail["mata_kuliah_nama"] for r in errors}
        assert any("Algoritma" in name for name in mk_names), (
            f"Expected 'Algoritma' in PARALLEL_MISMATCH, got: {mk_names}"
        )

    # ------------------------------------------------------------------
    # HC-08: STUDENT_DAILY_OVERLOAD
    # ------------------------------------------------------------------

    def test_hc08_student_daily_overload_detected(self, all_conflicts):
        """At least 1 STUDENT_DAILY_OVERLOAD (ERROR) conflict detected."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity
        errors = [r for r in all_conflicts if r.jenis == ConflictJenis.STUDENT_DAILY_OVERLOAD]
        assert len(errors) >= 1, "Expected at least 1 STUDENT_DAILY_OVERLOAD conflict"
        assert all(r.severity == ConflictSeverity.ERROR for r in errors)

    def test_hc08_s1_mat_smt2_senin_overload(self, all_conflicts):
        """S1 Mat Smt II on Senin has 4 MK (exceeds 2 MK/day limit)."""
        from app.services.conflict_engine import ConflictJenis
        errors = [r for r in all_conflicts if r.jenis == ConflictJenis.STUDENT_DAILY_OVERLOAD]
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
        assert any(r.detail["jumlah_mk"] > 2 for r in target)

    # ------------------------------------------------------------------
    # HC-09: LECTURER_DAILY_OVERLOAD
    # ------------------------------------------------------------------

    def test_hc09_lecturer_daily_overload_detected(self, all_conflicts):
        """At least 1 LECTURER_DAILY_OVERLOAD (ERROR) conflict detected."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity
        errors = [r for r in all_conflicts if r.jenis == ConflictJenis.LECTURER_DAILY_OVERLOAD]
        assert len(errors) >= 1, "Expected at least 1 LECTURER_DAILY_OVERLOAD conflict"
        assert all(r.severity == ConflictSeverity.ERROR for r in errors)

    # ------------------------------------------------------------------
    # SC-01: STUDENT_CONFLICT
    # ------------------------------------------------------------------

    def test_sc01_student_conflict_detected(self, all_conflicts):
        """At least 1 STUDENT_CONFLICT (WARNING) detected."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity
        warnings = [r for r in all_conflicts if r.jenis == ConflictJenis.STUDENT_CONFLICT]
        assert len(warnings) >= 1, "Expected at least 1 STUDENT_CONFLICT warning"
        assert all(r.severity == ConflictSeverity.WARNING for r in warnings)

    def test_sc01_severity_is_warning_not_error(self, all_conflicts):
        """SC-01 must be WARNING, not ERROR."""
        from app.services.conflict_engine import ConflictJenis, ConflictSeverity
        for r in all_conflicts:
            if r.jenis == ConflictJenis.STUDENT_CONFLICT:
                assert r.severity == ConflictSeverity.WARNING, (
                    f"STUDENT_CONFLICT should be WARNING, got {r.severity}"
                )

    # ------------------------------------------------------------------
    # No unexpected exceptions
    # ------------------------------------------------------------------

    def test_conflict_detection_runs_without_exception(self, assignments, engine):
        """Full conflict engine run completes without raising exceptions."""
        try:
            results = []
            results += engine.check_lecturer_double(assignments)
            results += engine.check_room_double(assignments)
            results += engine.check_parallel_mismatch(assignments)
            results += engine.check_student_daily_load(assignments)
            results += engine.check_lecturer_daily_load(assignments)
            results += engine.check_student_conflict(assignments)
            results += engine.check_workload_equity(assignments)
            results += engine.check_lecturer_preference(assignments)
            results += engine.check_floor_priority(assignments)
        except Exception as exc:
            pytest.fail(f"Conflict engine raised unexpected exception: {exc}")


# ---------------------------------------------------------------------------
# Phase 4: Full E2E narrative test — single test that runs the complete workflow
# ---------------------------------------------------------------------------


class TestFullE2EWorkflow:
    """
    Single end-to-end test that runs the complete workflow and reports results.

    This test is intentionally tolerant — it verifies the workflow completes
    without crashing and that the minimum expected outputs are present.
    """

    def test_full_workflow_end_to_end(self, db_session):
        """
        Full workflow: import master → import jadwal → detect conflicts → verify results.

        Reports:
        - How many records were imported (prodi, dosen, ruang)
        - How many jadwal rows were processed (total, inserted, skipped)
        - What conflicts were detected (by type and severity)
        - Whether the workflow completed successfully end-to-end
        """
        from app.services.conflict_engine import ConflictEngine, ConflictJenis, ConflictSeverity
        from app.services.excel_importer import ImportResult

        # --- Step 1: Import master data ---
        importer = _make_importer(db_session)
        master_result = importer.import_master_db(str(_DB_XLSX))
        assert isinstance(master_result, ImportResult), "Master import must return ImportResult"
        assert master_result.total > 0, "Master import must process at least 1 row"

        prodi_count = db_session.query(_Prodi).count()
        dosen_count = db_session.query(_Dosen).count()
        ruang_count = db_session.query(_Ruang).count()

        # --- Step 2: Ensure sesi exists ---
        sesi = db_session.query(_SesiJadwal).filter_by(
            semester="Genap", tahun_akademik="2025-2026"
        ).first()
        if not sesi:
            sesi = _SesiJadwal(
                id=_uuid4_str(),
                nama="Genap 2025-2026",
                semester="Genap",
                tahun_akademik="2025-2026",
                status="Draft",
            )
            db_session.add(sesi)
            db_session.commit()

        # --- Step 3: Import jadwal ---
        jadwal_result = importer.import_jadwal(str(_JADWAL_XLSX), str(sesi.id))
        assert isinstance(jadwal_result, ImportResult), "Jadwal import must return ImportResult"
        assert jadwal_result.total > 0, "Jadwal import must process at least 1 row"
        assert jadwal_result.total == jadwal_result.inserted + jadwal_result.updated + jadwal_result.skipped

        # --- Step 4: Run conflict detection on mock assignments from real Excel ---
        mock_assignments = _parse_jadwal_excel()
        assert len(mock_assignments) >= 80, (
            f"Expected at least 80 mock assignments, got {len(mock_assignments)}"
        )

        engine = ConflictEngine(MagicMock())
        all_conflicts = []
        all_conflicts += engine.check_lecturer_double(mock_assignments)
        all_conflicts += engine.check_room_double(mock_assignments)
        all_conflicts += engine.check_parallel_mismatch(mock_assignments)
        all_conflicts += engine.check_student_daily_load(mock_assignments)
        all_conflicts += engine.check_lecturer_daily_load(mock_assignments)
        all_conflicts += engine.check_student_conflict(mock_assignments)

        # --- Step 5: Verify expected conflict types are present ---
        conflict_types = {r.jenis for r in all_conflicts}
        error_conflicts = [r for r in all_conflicts if r.severity == ConflictSeverity.ERROR]
        warning_conflicts = [r for r in all_conflicts if r.severity == ConflictSeverity.WARNING]

        # Must have HC-01 LECTURER_DOUBLE
        assert ConflictJenis.LECTURER_DOUBLE in conflict_types, (
            f"Expected LECTURER_DOUBLE in conflicts, got: {conflict_types}"
        )

        # Must have HC-07 PARALLEL_MISMATCH
        assert ConflictJenis.PARALLEL_MISMATCH in conflict_types, (
            f"Expected PARALLEL_MISMATCH in conflicts, got: {conflict_types}"
        )

        # Must have HC-08 STUDENT_DAILY_OVERLOAD
        assert ConflictJenis.STUDENT_DAILY_OVERLOAD in conflict_types, (
            f"Expected STUDENT_DAILY_OVERLOAD in conflicts, got: {conflict_types}"
        )

        # Must have SC-01 STUDENT_CONFLICT
        assert ConflictJenis.STUDENT_CONFLICT in conflict_types, (
            f"Expected STUDENT_CONFLICT in conflicts, got: {conflict_types}"
        )

        # Must have at least some ERROR conflicts
        assert len(error_conflicts) >= 4, (
            f"Expected at least 4 ERROR conflicts, got {len(error_conflicts)}"
        )

        # Must have at least some WARNING conflicts
        assert len(warning_conflicts) >= 1, (
            f"Expected at least 1 WARNING conflict, got {len(warning_conflicts)}"
        )

        # --- Report results (printed to stdout for visibility) ---
        print("\n" + "=" * 60)
        print("E2E WORKFLOW RESULTS — Genap 2025-2026")
        print("=" * 60)
        print(f"\nPhase 1 — Master Import (db.xlsx):")
        print(f"  Prodi:  {prodi_count} records")
        print(f"  Dosen:  {dosen_count} records")
        print(f"  Ruang:  {ruang_count} records")
        print(f"  Total rows processed: {master_result.total}")
        print(f"  Inserted: {master_result.inserted}, Updated: {master_result.updated}, Skipped: {master_result.skipped}")

        print(f"\nPhase 2 — Jadwal Import (ED-8 Genap 2025-2026):")
        print(f"  Total rows processed: {jadwal_result.total}")
        print(f"  Inserted: {jadwal_result.inserted}, Updated: {jadwal_result.updated}, Skipped: {jadwal_result.skipped}")
        print(f"  (Note: rows skipped because MataKuliahKelas not pre-seeded)")

        print(f"\nPhase 3 — Mock Assignments from Excel:")
        print(f"  Assignments parsed: {len(mock_assignments)}")

        print(f"\nPhase 4 — Conflict Detection Results:")
        print(f"  Total conflicts: {len(all_conflicts)}")
        print(f"  ERROR conflicts: {len(error_conflicts)}")
        print(f"  WARNING conflicts: {len(warning_conflicts)}")

        # Group by type
        by_type: dict = defaultdict(list)
        for r in all_conflicts:
            by_type[r.jenis].append(r)

        print(f"\n  Conflicts by type:")
        for jenis, items in sorted(by_type.items()):
            severities = {r.severity for r in items}
            print(f"    {jenis}: {len(items)} ({', '.join(sorted(severities))})")

        # Show LECTURER_DOUBLE details
        ld_conflicts = by_type.get(ConflictJenis.LECTURER_DOUBLE, [])
        if ld_conflicts:
            print(f"\n  HC-01 LECTURER_DOUBLE details:")
            for r in ld_conflicts:
                print(f"    - {r.detail['dosen_nama']} @ {r.detail['timeslot_label']}")

        # Show PARALLEL_MISMATCH details
        pm_conflicts = by_type.get(ConflictJenis.PARALLEL_MISMATCH, [])
        if pm_conflicts:
            print(f"\n  HC-07 PARALLEL_MISMATCH details:")
            for r in pm_conflicts:
                print(f"    - {r.detail['mata_kuliah_nama']}")

        # Show STUDENT_DAILY_OVERLOAD details
        sdo_conflicts = by_type.get(ConflictJenis.STUDENT_DAILY_OVERLOAD, [])
        if sdo_conflicts:
            print(f"\n  HC-08 STUDENT_DAILY_OVERLOAD details:")
            for r in sdo_conflicts:
                print(f"    - {r.detail['prodi_nama']} Smt {r.detail['semester']} on {r.detail['hari']}: {r.detail['jumlah_mk']} MK")

        # Show LECTURER_DAILY_OVERLOAD details
        ldo_conflicts = by_type.get(ConflictJenis.LECTURER_DAILY_OVERLOAD, [])
        if ldo_conflicts:
            print(f"\n  HC-09 LECTURER_DAILY_OVERLOAD details:")
            for r in ldo_conflicts:
                print(f"    - {r.detail['dosen_nama']} on {r.detail['hari']}: {r.detail['jumlah_mk']} MK")

        print("\n" + "=" * 60)
        print("WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 60)
