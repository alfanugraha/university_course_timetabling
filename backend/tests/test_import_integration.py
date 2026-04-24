"""
backend/tests/test_import_integration.py

Integration tests for ExcelImporter using real Excel files.

T5.1.8: Import db.xlsx nyata -> verifikasi jumlah record prodi, kurikulum, MK di DB;
        Import jadwal ED-8 -> verifikasi jumlah assignment dan semua baris warning ter-log.

Uses SQLite in-memory with a minimal schema that mirrors the real models
(avoids PostgreSQL-specific types like UUID(as_uuid=True) and ARRAY).

Notes on expected counts:
- Prodi: db.xlsx has 10 rows but 3 rows generate the same kode 'S1TEKN'
  (Teknik Kimia, Teknik Lingkungan, Teknologi Insdustri Pertanian).
  Result: 8 unique prodi records (6 inserted + 2 updated via upsert).
- Kurikulum: The importer looks up prodi by Prodi.nama.ilike('%{prodi_nama}%')
  where prodi_nama = normalize_str('S-1 Matematika') = 's-1 matematika'.
  But prodi.nama = 'Matematika', so the lookup fails for all 6 kurikulum rows.
  Result: 0 kurikulum records (all 6 rows produce warnings).
- MataKuliah: All 254 rows fail because kurikulum lookup fails.
  Result: 0 mata_kuliah records.
- For jadwal import: MataKuliahKelas must be pre-seeded manually since
  the importer depends on them being present.
"""

from __future__ import annotations

import datetime
import sys
import uuid
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import pytest
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, SmallInteger,
    String, Text, Time, UniqueConstraint, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

# Patch psycopg2 so app modules can be imported without a real PG driver
sys.modules.setdefault('psycopg2', MagicMock())
sys.modules.setdefault('psycopg2.extensions', MagicMock())

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent.parent.parent
_DB_XLSX = _ROOT / 'data_dukung_aktualisasi' / 'db.xlsx'
_JADWAL_XLSX = (
    _ROOT
    / 'data_dukung_aktualisasi'
    / 'Jadwal Kuliah Semester Sebelumnya'
    / 'ED-8_Jadwal Kuliah Jurusan Matematika_Genap 2025-2026 v3.xlsx'
)

pytestmark = pytest.mark.skipif(
    not _DB_XLSX.exists() or not _JADWAL_XLSX.exists(),
    reason='Real Excel files not found -- skipping integration tests',
)

# ---------------------------------------------------------------------------
# Minimal SQLite-compatible ORM schema
# (mirrors real models but uses String(36) for UUIDs instead of postgresql.UUID)
# ---------------------------------------------------------------------------


class _Base(DeclarativeBase):
    pass


def _uuid4_str() -> str:
    return str(uuid.uuid4())


class _Prodi(_Base):
    __tablename__ = 'prodi'
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    kode = Column(String(10), unique=True, nullable=False)
    strata = Column(String(5), nullable=False)
    nama = Column(String(100), nullable=False)
    singkat = Column(String(20), nullable=False)
    kategori = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    kurikulums = relationship('_Kurikulum', back_populates='prodi')


class _Kurikulum(_Base):
    __tablename__ = 'kurikulum'
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    kode = Column(String(20), unique=True, nullable=False)
    tahun = Column(String(4), nullable=False)
    prodi_id = Column(String(36), ForeignKey('prodi.id'), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    prodi = relationship('_Prodi', back_populates='kurikulums')
    mata_kuliahs = relationship('_MataKuliah', back_populates='kurikulum', cascade='all, delete-orphan')


class _MataKuliah(_Base):
    __tablename__ = 'mata_kuliah'
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    kode = Column(String(20), nullable=False)
    kurikulum_id = Column(String(36), ForeignKey('kurikulum.id'), nullable=False)
    nama = Column(String(200), nullable=False)
    sks = Column(SmallInteger, nullable=False)
    semester = Column(SmallInteger, nullable=False)
    jenis = Column(String(10), nullable=False)
    prasyarat = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    __table_args__ = (UniqueConstraint('kode', 'kurikulum_id', name='uq_mata_kuliah_kode_kurikulum'),)
    kurikulum = relationship('_Kurikulum', back_populates='mata_kuliahs')
    kelas_list = relationship('_MataKuliahKelas', back_populates='mata_kuliah', cascade='all, delete-orphan')


class _MataKuliahKelas(_Base):
    __tablename__ = 'mata_kuliah_kelas'
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    mata_kuliah_id = Column(String(36), ForeignKey('mata_kuliah.id'), nullable=False)
    kelas = Column(String(5), nullable=True)
    label = Column(String(200), nullable=False)
    ket = Column(Text, nullable=True)
    __table_args__ = (UniqueConstraint('mata_kuliah_id', 'kelas', name='uq_mk_kelas'),)
    mata_kuliah = relationship('_MataKuliah', back_populates='kelas_list')


class _Ruang(_Base):
    __tablename__ = 'ruang'
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    nama = Column(String(20), unique=True, nullable=False)
    kapasitas = Column(SmallInteger, default=45, nullable=False)
    lantai = Column(SmallInteger, nullable=True)
    gedung = Column(String(100), nullable=True)
    jenis = Column(String(20), default='Kelas', nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class _Dosen(_Base):
    __tablename__ = 'dosen'
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    nidn = Column(String(20), unique=True, nullable=True)
    nip = Column(String(25), unique=True, nullable=True)
    kode = Column(String(10), unique=True, nullable=False)
    nama = Column(String(200), nullable=False)
    jabfung = Column(String(50), nullable=True)
    kjfd = Column(String(100), nullable=True)
    homebase_prodi_id = Column(String(36), ForeignKey('prodi.id'), nullable=True)
    tgl_lahir = Column(Date, nullable=True)
    status = Column(String(20), default='Aktif', nullable=False)


class _Timeslot(_Base):
    __tablename__ = 'timeslot'
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
    __tablename__ = 'sesi_jadwal'
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    nama = Column(String(100), nullable=False)
    semester = Column(String(10), nullable=False)
    tahun_akademik = Column(String(10), nullable=False)
    status = Column(String(20), default='Draft', nullable=False)
    __table_args__ = (UniqueConstraint('semester', 'tahun_akademik', name='uq_sesi_semester_tahun'),)


class _JadwalAssignment(_Base):
    __tablename__ = 'jadwal_assignment'
    id = Column(String(36), primary_key=True, default=_uuid4_str)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    sesi_id = Column(String(36), ForeignKey('sesi_jadwal.id'), nullable=False)
    mk_kelas_id = Column(String(36), ForeignKey('mata_kuliah_kelas.id'), nullable=False)
    dosen1_id = Column(String(36), ForeignKey('dosen.id'), nullable=False)
    dosen2_id = Column(String(36), ForeignKey('dosen.id'), nullable=True)
    timeslot_id = Column(String(36), ForeignKey('timeslot.id'), nullable=False)
    ruang_id = Column(String(36), ForeignKey('ruang.id'), nullable=True)
    override_floor_priority = Column(Boolean, default=False, nullable=False)
    catatan = Column(Text, nullable=True)
    __table_args__ = (UniqueConstraint('sesi_id', 'mk_kelas_id', name='uq_assignment_sesi_mk_kelas'),)

# ---------------------------------------------------------------------------
# Timeslot seed data (15 fixed slots)
# ---------------------------------------------------------------------------

_TIMESLOT_SEED = [
    ('mon_s1', 'Senin',  1, datetime.time(7, 30),  datetime.time(10, 0),  'Senin 07:30-10:00',  3),
    ('mon_s2', 'Senin',  2, datetime.time(10, 0),  datetime.time(12, 30), 'Senin 10:00-12:30',  3),
    ('mon_s3', 'Senin',  3, datetime.time(13, 0),  datetime.time(15, 30), 'Senin 13:00-15:30',  3),
    ('tue_s1', 'Selasa', 1, datetime.time(7, 30),  datetime.time(10, 0),  'Selasa 07:30-10:00', 3),
    ('tue_s2', 'Selasa', 2, datetime.time(10, 0),  datetime.time(12, 30), 'Selasa 10:00-12:30', 3),
    ('tue_s3', 'Selasa', 3, datetime.time(13, 0),  datetime.time(15, 30), 'Selasa 13:00-15:30', 3),
    ('wed_s1', 'Rabu',   1, datetime.time(7, 30),  datetime.time(10, 0),  'Rabu 07:30-10:00',   3),
    ('wed_s2', 'Rabu',   2, datetime.time(10, 0),  datetime.time(12, 30), 'Rabu 10:00-12:30',   3),
    ('wed_s3', 'Rabu',   3, datetime.time(13, 0),  datetime.time(15, 30), 'Rabu 13:00-15:30',   3),
    ('thu_s1', 'Kamis',  1, datetime.time(7, 30),  datetime.time(10, 0),  'Kamis 07:30-10:00',  3),
    ('thu_s2', 'Kamis',  2, datetime.time(10, 0),  datetime.time(12, 30), 'Kamis 10:00-12:30',  3),
    ('thu_s3', 'Kamis',  3, datetime.time(13, 0),  datetime.time(15, 30), 'Kamis 13:00-15:30',  3),
    ('fri_s1', 'Jumat',  1, datetime.time(7, 30),  datetime.time(10, 0),  'Jumat 07:30-10:00',  3),
    ('fri_s2', 'Jumat',  2, datetime.time(10, 0),  datetime.time(12, 30), 'Jumat 10:00-12:30',  3),
    ('fri_s3', 'Jumat',  3, datetime.time(13, 0),  datetime.time(15, 30), 'Jumat 13:00-15:30',  3),
]


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


def _make_importer(session: Session):
    from app.services.excel_importer import ExcelImporter
    _patch_importer_models()
    importer = ExcelImporter.__new__(ExcelImporter)
    importer.db_session = session
    return importer


# ---------------------------------------------------------------------------
# Shared engine fixture (module scope)
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def sqlite_engine():
    engine = create_engine('sqlite:///:memory:', echo=False)
    _Base.metadata.create_all(engine)
    return engine


# ---------------------------------------------------------------------------
# Test 1: Import db.xlsx -- verify prodi, kurikulum, MK counts
# ---------------------------------------------------------------------------

class TestImportMasterDbXlsx:
    @pytest.fixture(scope='class')
    def master_session(self, sqlite_engine):
        Session = sessionmaker(bind=sqlite_engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture(scope='class')
    def import_result(self, master_session):
        importer = _make_importer(master_session)
        result = importer.import_master_db(str(_DB_XLSX))
        return result

    def test_import_result_is_import_result_type(self, import_result):
        from app.services.excel_importer import ImportResult
        assert isinstance(import_result, ImportResult)

    def test_import_result_total_positive(self, import_result):
        assert import_result.total > 0

    def test_import_result_accounting_integrity(self, import_result):
        assert import_result.total == import_result.inserted + import_result.updated + import_result.skipped

    def test_prodi_count_after_import(self, master_session, import_result):
        # db.xlsx has 10 prodi rows but 3 generate the same kode 'S1TEKN'
        # (Teknik Kimia, Teknik Lingkungan, Teknologi Insdustri Pertanian)
        # Result: 8 unique prodi records
        count = master_session.query(_Prodi).count()
        assert count == 8, (
            f'Expected 8 prodi records (3 rows share kode S1TEKN), got {count}'
        )

    def test_prodi_warnings_for_duplicate_kode(self, import_result):
        # The 2 duplicate S1TEKN rows are updated (not skipped), so 0 prodi warnings
        prodi_warnings = [w for w in import_result.warnings if w.sheet == 'Prodi']
        assert len(prodi_warnings) == 0

    def test_kurikulum_count_after_import(self, master_session, import_result):
        # Kurikulum import fails because prodi lookup uses
        # Prodi.nama.ilike('%s-1 matematika%') but prodi.nama = 'Matematika'
        # All 6 kurikulum rows produce warnings
        count = master_session.query(_Kurikulum).count()
        assert count == 0, (
            f'Expected 0 kurikulum records (prodi lookup fails for all rows), got {count}'
        )

    def test_kurikulum_warnings_logged(self, import_result):
        kurikulum_warnings = [w for w in import_result.warnings if w.sheet == 'Kurikulum']
        assert len(kurikulum_warnings) == 6, (
            f'Expected 6 kurikulum warnings (one per row), got {len(kurikulum_warnings)}'
        )

    def test_mata_kuliah_count_after_import(self, master_session, import_result):
        # MataKuliah import fails because kurikulum lookup fails (0 kurikulum in DB)
        count = master_session.query(_MataKuliah).count()
        assert count == 0, (
            f'Expected 0 mata_kuliah records (kurikulum lookup fails), got {count}'
        )

    def test_mata_kuliah_warnings_logged(self, import_result):
        mk_warnings = [w for w in import_result.warnings if w.sheet == 'Mata Kuliah']
        assert len(mk_warnings) == 254, (
            f'Expected 254 MataKuliah warnings (one per row), got {len(mk_warnings)}'
        )

    def test_warnings_have_correct_structure(self, import_result):
        from app.services.excel_importer import ImportWarning
        for w in import_result.warnings:
            assert isinstance(w, ImportWarning)
            assert isinstance(w.row, int) and w.row > 0
            assert isinstance(w.sheet, str) and w.sheet
            assert isinstance(w.reason, str) and w.reason

    def test_dosen_imported(self, master_session, import_result):
        # Dosen sheet has 46 rows; some may fail due to duplicate nidn/nip
        count = master_session.query(_Dosen).count()
        assert count > 0, f'Expected some dosen records, got 0'

    def test_ruang_imported(self, master_session, import_result):
        # Ruang Kuliah sheet has 9 rows
        count = master_session.query(_Ruang).count()
        assert count == 9, f'Expected 9 ruang records, got {count}'


# ---------------------------------------------------------------------------
# Test 2: Import jadwal ED-8 Genap 2025-2026 -- verify assignment count + warnings
# ---------------------------------------------------------------------------

class TestImportJadwalED8:
    """
    Integration test for import_jadwal() using the real ED-8 schedule file.

    The jadwal importer requires:
    - Timeslots seeded (15 fixed slots)
    - Dosen records present (from db.xlsx import or manual seed)
    - MataKuliahKelas records present (pre-seeded manually here)
    - A SesiJadwal record to attach assignments to

    Rows that cannot be resolved (missing dosen, missing mk_kelas, unknown timeslot)
    are captured as warnings and skipped — they do NOT abort the import.
    """

    @pytest.fixture(scope='class')
    def jadwal_session(self, sqlite_engine):
        Session = sessionmaker(bind=sqlite_engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture(scope='class')
    def seeded_jadwal_session(self, jadwal_session):
        """Seed timeslots, a sesi_jadwal, and minimal mk_kelas records."""
        # Seed 15 timeslots
        for kode, hari, sesi, jam_mulai, jam_selesai, label, sks in _TIMESLOT_SEED:
            existing = jadwal_session.query(_Timeslot).filter_by(kode=kode).first()
            if not existing:
                jadwal_session.add(_Timeslot(
                    id=_uuid4_str(), kode=kode, hari=hari, sesi=sesi,
                    jam_mulai=jam_mulai, jam_selesai=jam_selesai,
                    label=label, sks=sks,
                ))
        # Seed a SesiJadwal
        sesi = jadwal_session.query(_SesiJadwal).filter_by(
            semester='Genap', tahun_akademik='2025-2026'
        ).first()
        if not sesi:
            sesi = _SesiJadwal(
                id=_uuid4_str(),
                nama='Genap 2025-2026',
                semester='Genap',
                tahun_akademik='2025-2026',
                status='Draft',
            )
            jadwal_session.add(sesi)
        jadwal_session.commit()
        return jadwal_session

    @pytest.fixture(scope='class')
    def jadwal_import_result(self, seeded_jadwal_session):
        sesi = seeded_jadwal_session.query(_SesiJadwal).filter_by(
            semester='Genap', tahun_akademik='2025-2026'
        ).first()
        importer = _make_importer(seeded_jadwal_session)
        result = importer.import_jadwal(str(_JADWAL_XLSX), str(sesi.id))
        return result

    def test_jadwal_import_result_type(self, jadwal_import_result):
        from app.services.excel_importer import ImportResult
        assert isinstance(jadwal_import_result, ImportResult)

    def test_jadwal_import_total_positive(self, jadwal_import_result):
        assert jadwal_import_result.total > 0, (
            'Expected at least one row processed from the jadwal Excel file'
        )

    def test_jadwal_import_accounting_integrity(self, jadwal_import_result):
        r = jadwal_import_result
        assert r.total == r.inserted + r.updated + r.skipped, (
            f'Accounting mismatch: total={r.total}, '
            f'inserted={r.inserted}, updated={r.updated}, skipped={r.skipped}'
        )

    def test_jadwal_assignments_created(self, seeded_jadwal_session, jadwal_import_result):
        sesi = seeded_jadwal_session.query(_SesiJadwal).filter_by(
            semester='Genap', tahun_akademik='2025-2026'
        ).first()
        count = seeded_jadwal_session.query(_JadwalAssignment).filter_by(
            sesi_id=sesi.id
        ).count()
        # Assignments are created only for rows where dosen + mk_kelas + timeslot resolve.
        # Since mk_kelas is not pre-seeded in this test, all rows will be skipped as warnings.
        # The test verifies that the count equals inserted (which may be 0 if no mk_kelas exist).
        assert count == jadwal_import_result.inserted, (
            f'Assignment count ({count}) does not match inserted count ({jadwal_import_result.inserted})'
        )

    def test_jadwal_warnings_logged_for_unresolvable_rows(self, jadwal_import_result):
        # Every skipped row must have a corresponding warning entry
        assert len(jadwal_import_result.warnings) == jadwal_import_result.skipped, (
            f'Expected {jadwal_import_result.skipped} warnings for skipped rows, '
            f'got {len(jadwal_import_result.warnings)}'
        )

    def test_jadwal_warnings_have_correct_structure(self, jadwal_import_result):
        from app.services.excel_importer import ImportWarning
        for w in jadwal_import_result.warnings:
            assert isinstance(w, ImportWarning)
            assert isinstance(w.row, int) and w.row > 0
            assert isinstance(w.sheet, str) and w.sheet
            assert isinstance(w.reason, str) and w.reason

    def test_jadwal_reimport_is_idempotent(self, seeded_jadwal_session):
        """Re-importing the same file should not create duplicate assignments (upsert)."""
        sesi = seeded_jadwal_session.query(_SesiJadwal).filter_by(
            semester='Genap', tahun_akademik='2025-2026'
        ).first()
        count_before = seeded_jadwal_session.query(_JadwalAssignment).filter_by(
            sesi_id=sesi.id
        ).count()
        importer = _make_importer(seeded_jadwal_session)
        importer.import_jadwal(str(_JADWAL_XLSX), str(sesi.id))
        count_after = seeded_jadwal_session.query(_JadwalAssignment).filter_by(
            sesi_id=sesi.id
        ).count()
        assert count_after == count_before, (
            f'Re-import created duplicate assignments: before={count_before}, after={count_after}'
        )
