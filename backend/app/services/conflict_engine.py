"""
Conflict Detection Engine — Fase 1
Sistem Penjadwalan Kuliah, Jurusan Matematika FMIPA UNRI

Engine ini adalah Python murni (rule-based, tanpa ML/external solver).
Setiap rule adalah method terpisah yang mengembalikan list[ConflictResult].
Severity: ERROR untuk Hard Constraints, WARNING untuk Soft Constraints.
HC-03 dan HC-04 DEFERRED — tidak diimplementasikan di Fase 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session


class ConflictJenis(str, Enum):
    """Tipe konflik yang valid untuk conflict detection engine."""

    # Hard Constraints — severity = ERROR
    LECTURER_DOUBLE = "LECTURER_DOUBLE"          # HC-01: Dosen double-booking
    ROOM_DOUBLE = "ROOM_DOUBLE"                  # HC-02: Ruang double-booking (kondisional)
    ROOM_CAPACITY = "ROOM_CAPACITY"              # HC-03: Kapasitas ruang (DEFERRED)
    BKD_WORKLOAD = "BKD_WORKLOAD"                # HC-04: Beban BKD (DEFERRED)
    SINGLE_ASSIGNMENT = "SINGLE_ASSIGNMENT"      # HC-05: Satu kelas MK satu assignment
    LECTURER_UNAVAILABLE = "LECTURER_UNAVAILABLE"  # HC-06: Dosen tidak tersedia
    PARALLEL_MISMATCH = "PARALLEL_MISMATCH"      # HC-07: Kelas paralel beda slot
    STUDENT_DAILY_OVERLOAD = "STUDENT_DAILY_OVERLOAD"    # HC-08: Beban harian mahasiswa
    LECTURER_DAILY_OVERLOAD = "LECTURER_DAILY_OVERLOAD"  # HC-09: Beban harian dosen

    # Soft Constraints — severity = WARNING
    STUDENT_CONFLICT = "STUDENT_CONFLICT"                        # SC-01
    WORKLOAD_INEQUITY = "WORKLOAD_INEQUITY"                      # SC-02
    LECTURER_PREFERENCE_VIOLATED = "LECTURER_PREFERENCE_VIOLATED"  # SC-03
    FLOOR_PRIORITY_VIOLATED = "FLOOR_PRIORITY_VIOLATED"          # SC-05


class ConflictSeverity(str, Enum):
    ERROR = "ERROR"      # Hard Constraint — memblokir validasi
    WARNING = "WARNING"  # Soft Constraint — informatif


@dataclass
class ConflictResult:
    """
    Hasil deteksi satu konflik dari conflict engine.

    Fields:
        jenis           : Kode tipe konflik (ConflictJenis)
        severity        : ERROR (Hard Constraint) atau WARNING (Soft Constraint)
        assignment_ids  : Daftar UUID assignment yang terlibat dalam konflik
        pesan           : Deskripsi konflik yang dapat dibaca manusia
        detail          : Data tambahan opsional (nama dosen, slot, dll)
    """

    jenis: str
    severity: str
    assignment_ids: list[UUID]
    pesan: str
    detail: dict | None = field(default=None)


class ConflictEngine:
    """
    Conflict Detection Engine untuk Sistem Penjadwalan Kuliah.

    Mengorkestrasikan semua rule deteksi konflik untuk satu sesi jadwal.
    Dipanggil via POST /sesi/{id}/check-conflicts.

    Usage:
        engine = ConflictEngine(db)
        results = engine.run(sesi_id)
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self, sesi_id: UUID) -> list[ConflictResult]:
        """
        Jalankan semua rule deteksi konflik untuk sesi yang diberikan.

        Urutan eksekusi:
          Hard Constraints (ERROR):
            HC-01 check_lecturer_double
            HC-02 check_room_double        (kondisional: hanya jika ruang_id terisi)
            HC-06 check_lecturer_unavail
            HC-07 check_parallel_mismatch
            HC-08 check_student_daily_load
            HC-09 check_lecturer_daily_load
          Soft Constraints (WARNING):
            SC-01 check_student_conflict
            SC-02 check_workload_equity
            SC-03 check_lecturer_preference
            SC-05 check_floor_priority     (kondisional: hanya jika ruang_id & tgl_lahir terisi)

          DEFERRED (tidak dijalankan di Fase 1):
            HC-03 check_room_capacity
            HC-04 check_bkd_limit

        Returns:
            list[ConflictResult] — semua konflik yang ditemukan, diurutkan ERROR dulu lalu WARNING.
        """
        assignments = self._fetch_assignments(sesi_id)

        results: list[ConflictResult] = []

        # --- Hard Constraints (ERROR) ---
        results += self.check_lecturer_double(assignments)       # HC-01
        results += self.check_room_double(assignments)           # HC-02 (kondisional)
        # HC-03 DEFERRED
        # HC-04 DEFERRED
        results += self.check_lecturer_unavail(assignments)      # HC-06
        results += self.check_parallel_mismatch(assignments)     # HC-07
        results += self.check_student_daily_load(assignments)    # HC-08
        results += self.check_lecturer_daily_load(assignments)   # HC-09

        # --- Soft Constraints (WARNING) ---
        results += self.check_student_conflict(assignments)      # SC-01
        results += self.check_workload_equity(assignments)       # SC-02
        results += self.check_lecturer_preference(assignments)   # SC-03
        results += self.check_floor_priority(assignments)        # SC-05

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_assignments(self, sesi_id: UUID) -> list[Any]:
        """
        Ambil semua assignment untuk sesi yang diberikan beserta relasi yang dibutuhkan.
        Eager-load: mk_kelas → mata_kuliah → kurikulum → prodi, dosen1, dosen2, timeslot, ruang.
        """
        from sqlalchemy.orm import joinedload

        from app.models.jadwal_assignment import JadwalAssignment
        from app.models.kurikulum import Kurikulum
        from app.models.mata_kuliah import MataKuliah, MataKuliahKelas

        return (
            self.db.query(JadwalAssignment)
            .options(
                joinedload(JadwalAssignment.mk_kelas)
                .joinedload(MataKuliahKelas.mata_kuliah)
                .joinedload(MataKuliah.kurikulum)
                .joinedload(Kurikulum.prodi),
                joinedload(JadwalAssignment.dosen1),
                joinedload(JadwalAssignment.dosen2),
                joinedload(JadwalAssignment.timeslot),
                joinedload(JadwalAssignment.ruang),
            )
            .filter(JadwalAssignment.sesi_id == sesi_id)
            .all()
        )

    # ------------------------------------------------------------------
    # Hard Constraints
    # ------------------------------------------------------------------

    def check_lecturer_double(self, assignments: list[Any]) -> list[ConflictResult]:
        """HC-01: Dosen tidak boleh mengajar dua kelas di timeslot yang sama."""
        from collections import defaultdict

        # Map: (dosen_id, timeslot_id) -> list of assignment
        dosen_timeslot: dict[tuple, list] = defaultdict(list)

        for a in assignments:
            dosen_timeslot[(a.dosen1_id, a.timeslot_id)].append(a)
            if a.dosen2_id is not None:
                dosen_timeslot[(a.dosen2_id, a.timeslot_id)].append(a)

        results: list[ConflictResult] = []

        for (dosen_id, timeslot_id), involved in dosen_timeslot.items():
            if len(involved) <= 1:
                continue

            # Deduplicate assignment ids (a dosen could appear as both dosen1 & dosen2
            # in different assignments — keep unique assignment UUIDs)
            seen_ids: set[UUID] = set()
            unique_assignments = []
            for a in involved:
                if a.id not in seen_ids:
                    seen_ids.add(a.id)
                    unique_assignments.append(a)

            if len(unique_assignments) <= 1:
                continue

            # Resolve display info from the first assignment's loaded relations
            sample = unique_assignments[0]
            timeslot_label = sample.timeslot.label if sample.timeslot else str(timeslot_id)

            # Find dosen name — check dosen1 first, then dosen2
            dosen_obj = None
            if sample.dosen1_id == dosen_id and sample.dosen1:
                dosen_obj = sample.dosen1
            elif sample.dosen2_id == dosen_id and sample.dosen2:
                dosen_obj = sample.dosen2
            else:
                # Search other assignments in the group
                for a in unique_assignments[1:]:
                    if a.dosen1_id == dosen_id and a.dosen1:
                        dosen_obj = a.dosen1
                        break
                    if a.dosen2_id == dosen_id and a.dosen2:
                        dosen_obj = a.dosen2
                        break

            dosen_nama = dosen_obj.nama if dosen_obj else str(dosen_id)
            dosen_kode = dosen_obj.kode if dosen_obj else ""

            mk_labels = [
                a.mk_kelas.label if a.mk_kelas else str(a.mk_kelas_id)
                for a in unique_assignments
            ]

            results.append(
                ConflictResult(
                    jenis=ConflictJenis.LECTURER_DOUBLE,
                    severity=ConflictSeverity.ERROR,
                    assignment_ids=[a.id for a in unique_assignments],
                    pesan=(
                        f"Dosen {dosen_nama} ({dosen_kode}) dijadwalkan "
                        f"{len(unique_assignments)} kali pada timeslot {timeslot_label}: "
                        f"{', '.join(mk_labels)}"
                    ),
                    detail={
                        "dosen_id": str(dosen_id),
                        "dosen_nama": dosen_nama,
                        "dosen_kode": dosen_kode,
                        "timeslot_id": str(timeslot_id),
                        "timeslot_label": timeslot_label,
                        "mk_kelas_labels": mk_labels,
                    },
                )
            )

        return results

    def check_room_double(self, assignments: list[Any]) -> list[ConflictResult]:
        """HC-02: Ruang tidak boleh dipakai dua kelas di timeslot yang sama (kondisional).

        Hanya diperiksa jika ruang_id tidak NULL — jika NULL, assignment dilewati.
        """
        from collections import defaultdict

        # Map: (timeslot_id, ruang_id) -> list of assignment
        # Skip assignments where ruang_id is NULL
        ruang_timeslot: dict[tuple, list] = defaultdict(list)

        for a in assignments:
            if a.ruang_id is None:
                continue
            ruang_timeslot[(a.timeslot_id, a.ruang_id)].append(a)

        results: list[ConflictResult] = []

        for (timeslot_id, ruang_id), involved in ruang_timeslot.items():
            if len(involved) <= 1:
                continue

            sample = involved[0]
            timeslot_label = sample.timeslot.label if sample.timeslot else str(timeslot_id)
            ruang_nama = sample.ruang.nama if sample.ruang else str(ruang_id)

            mk_labels = [
                a.mk_kelas.label if a.mk_kelas else str(a.mk_kelas_id)
                for a in involved
            ]

            results.append(
                ConflictResult(
                    jenis=ConflictJenis.ROOM_DOUBLE,
                    severity=ConflictSeverity.ERROR,
                    assignment_ids=[a.id for a in involved],
                    pesan=(
                        f"Ruang {ruang_nama} dipakai {len(involved)} kelas "
                        f"pada timeslot {timeslot_label}: {', '.join(mk_labels)}"
                    ),
                    detail={
                        "ruang_id": str(ruang_id),
                        "ruang_nama": ruang_nama,
                        "timeslot_id": str(timeslot_id),
                        "timeslot_label": timeslot_label,
                        "mk_kelas_labels": mk_labels,
                    },
                )
            )

        return results

    def check_lecturer_unavail(self, assignments: list[Any]) -> list[ConflictResult]:
        """HC-06: Dosen tidak boleh dijadwalkan di slot yang ia tandai tidak tersedia.

        Memeriksa dosen1_id dan dosen2_id pada setiap assignment.
        Rekaman dosen_unavailability dengan sesi_id NULL berlaku untuk semua sesi.
        Rekaman dengan sesi_id yang cocok dengan sesi assignment juga berlaku.
        """
        from app.models.dosen import DosenUnavailability

        if not assignments:
            return []

        # Ambil sesi_id dari assignment pertama (semua assignment dalam satu sesi)
        sesi_id = assignments[0].sesi_id

        # Kumpulkan semua dosen_id yang terlibat
        dosen_ids: set[UUID] = set()
        for a in assignments:
            dosen_ids.add(a.dosen1_id)
            if a.dosen2_id is not None:
                dosen_ids.add(a.dosen2_id)

        if not dosen_ids:
            return []

        # Query semua unavailability records yang relevan:
        # sesi_id IS NULL (berlaku semua sesi) ATAU sesi_id == sesi_id saat ini
        from sqlalchemy import or_

        unavail_records = (
            self.db.query(DosenUnavailability)
            .filter(
                DosenUnavailability.dosen_id.in_(dosen_ids),
                or_(
                    DosenUnavailability.sesi_id.is_(None),
                    DosenUnavailability.sesi_id == sesi_id,
                ),
            )
            .all()
        )

        # Bangun set (dosen_id, timeslot_id) yang tidak tersedia
        unavail_set: set[tuple] = {
            (rec.dosen_id, rec.timeslot_id) for rec in unavail_records
        }

        if not unavail_set:
            return []

        results: list[ConflictResult] = []

        for a in assignments:
            timeslot_label = a.timeslot.label if a.timeslot else str(a.timeslot_id)

            # Periksa dosen1
            if (a.dosen1_id, a.timeslot_id) in unavail_set:
                dosen_nama = a.dosen1.nama if a.dosen1 else str(a.dosen1_id)
                dosen_kode = a.dosen1.kode if a.dosen1 else ""
                mk_label = a.mk_kelas.label if a.mk_kelas else str(a.mk_kelas_id)
                results.append(
                    ConflictResult(
                        jenis=ConflictJenis.LECTURER_UNAVAILABLE,
                        severity=ConflictSeverity.ERROR,
                        assignment_ids=[a.id],
                        pesan=(
                            f"Dosen {dosen_nama} ({dosen_kode}) dijadwalkan pada timeslot "
                            f"{timeslot_label} padahal ditandai tidak tersedia "
                            f"(sebagai dosen1 pada {mk_label})"
                        ),
                        detail={
                            "dosen_id": str(a.dosen1_id),
                            "dosen_nama": dosen_nama,
                            "dosen_kode": dosen_kode,
                            "role": "dosen1",
                            "timeslot_id": str(a.timeslot_id),
                            "timeslot_label": timeslot_label,
                            "mk_kelas_label": mk_label,
                        },
                    )
                )

            # Periksa dosen2 (jika ada)
            if a.dosen2_id is not None and (a.dosen2_id, a.timeslot_id) in unavail_set:
                dosen_nama = a.dosen2.nama if a.dosen2 else str(a.dosen2_id)
                dosen_kode = a.dosen2.kode if a.dosen2 else ""
                mk_label = a.mk_kelas.label if a.mk_kelas else str(a.mk_kelas_id)
                results.append(
                    ConflictResult(
                        jenis=ConflictJenis.LECTURER_UNAVAILABLE,
                        severity=ConflictSeverity.ERROR,
                        assignment_ids=[a.id],
                        pesan=(
                            f"Dosen {dosen_nama} ({dosen_kode}) dijadwalkan pada timeslot "
                            f"{timeslot_label} padahal ditandai tidak tersedia "
                            f"(sebagai dosen2 pada {mk_label})"
                        ),
                        detail={
                            "dosen_id": str(a.dosen2_id),
                            "dosen_nama": dosen_nama,
                            "dosen_kode": dosen_kode,
                            "role": "dosen2",
                            "timeslot_id": str(a.timeslot_id),
                            "timeslot_label": timeslot_label,
                            "mk_kelas_label": mk_label,
                        },
                    )
                )

        return results

    def check_parallel_mismatch(self, assignments: list[Any]) -> list[ConflictResult]:
        """HC-07: Kelas paralel dari MK yang sama wajib di timeslot yang sama."""
        from collections import defaultdict

        # Map: mata_kuliah_id -> list of assignment
        mk_groups: dict[Any, list] = defaultdict(list)

        for a in assignments:
            # Defensive: skip if mk_kelas or mata_kuliah_id is None
            if a.mk_kelas is None or a.mk_kelas.mata_kuliah_id is None:
                continue
            mk_groups[a.mk_kelas.mata_kuliah_id].append(a)

        results: list[ConflictResult] = []

        for mk_id, group in mk_groups.items():
            # Only process groups with more than 1 assignment (parallel classes)
            if len(group) <= 1:
                continue

            # Collect unique timeslot_ids in this group
            timeslot_ids = {a.timeslot_id for a in group}

            # If all share the same timeslot → no conflict
            if len(timeslot_ids) <= 1:
                continue

            # Build per-kelas slot info for the message and detail
            kelas_slots = []
            for a in group:
                kelas_label = a.mk_kelas.kelas if a.mk_kelas.kelas else "?"
                ts_label = a.timeslot.label if a.timeslot else str(a.timeslot_id)
                kelas_slots.append({
                    "kelas": kelas_label,
                    "timeslot_label": ts_label,
                    "assignment_id": str(a.id),
                })

            # Resolve MK name from the first assignment
            sample = group[0]
            mk_nama = (
                sample.mk_kelas.mata_kuliah.nama
                if sample.mk_kelas.mata_kuliah
                else str(mk_id)
            )

            # Build human-readable slot description
            slot_parts = ", ".join(
                f"Kelas {ks['kelas']} di {ks['timeslot_label']}"
                for ks in kelas_slots
            )
            pesan = (
                f"Kelas paralel {mk_nama} memiliki slot berbeda: {slot_parts}"
            )

            results.append(
                ConflictResult(
                    jenis=ConflictJenis.PARALLEL_MISMATCH,
                    severity=ConflictSeverity.ERROR,
                    assignment_ids=[a.id for a in group],
                    pesan=pesan,
                    detail={
                        "mata_kuliah_id": str(mk_id),
                        "mata_kuliah_nama": mk_nama,
                        "kelas_slots": kelas_slots,
                    },
                )
            )

        return results

    def check_student_daily_load(self, assignments: list[Any]) -> list[ConflictResult]:
        """HC-08: Mahasiswa satu prodi+semester maks 2 MK atau 6 SKS per hari.

        Untuk setiap kombinasi (prodi_id, semester, hari):
          - Hitung jumlah MK unik (berdasarkan mata_kuliah_id)
          - Hitung total SKS (dari timeslot.sks, atau mata_kuliah.sks sebagai fallback)
          - ERROR STUDENT_DAILY_OVERLOAD jika jumlah_mk > 2 atau total_sks > 6

        Catatan: kelas paralel (A, B, C) dari MK yang sama dihitung sebagai 1 MK.
        """
        from collections import defaultdict

        # Map: (prodi_id, semester, hari) -> list of assignment
        groups: dict[tuple, list] = defaultdict(list)

        for a in assignments:
            # Defensive: skip jika relasi tidak lengkap
            if (
                a.mk_kelas is None
                or a.mk_kelas.mata_kuliah is None
                or a.mk_kelas.mata_kuliah.kurikulum is None
                or a.timeslot is None
            ):
                continue

            mk = a.mk_kelas.mata_kuliah
            kurikulum = mk.kurikulum
            prodi_id = kurikulum.prodi_id
            semester = mk.semester
            hari = a.timeslot.hari

            groups[(prodi_id, semester, hari)].append(a)

        results: list[ConflictResult] = []

        for (prodi_id, semester, hari), group in groups.items():
            # Hitung MK unik (kelas paralel A/B/C dari MK yang sama = 1 MK)
            mk_ids: set = {a.mk_kelas.mata_kuliah_id for a in group}
            jumlah_mk = len(mk_ids)

            # Hitung total SKS — gunakan timeslot.sks (semua slot = 3 SKS)
            # Untuk MK yang sama (paralel), hitung SKS-nya sekali saja
            sks_per_mk: dict = {}
            for a in group:
                mk_id = a.mk_kelas.mata_kuliah_id
                if mk_id not in sks_per_mk:
                    # Ambil SKS dari timeslot (canonical) atau fallback ke mk.sks
                    sks_per_mk[mk_id] = (
                        a.timeslot.sks
                        if a.timeslot.sks
                        else a.mk_kelas.mata_kuliah.sks
                    )
            total_sks = sum(sks_per_mk.values())

            # Tidak ada pelanggaran
            if jumlah_mk <= 2 and total_sks <= 6:
                continue

            # Bangun info untuk pesan dan detail
            # Ambil nama prodi dari assignment pertama
            sample = group[0]
            prodi_nama = (
                sample.mk_kelas.mata_kuliah.kurikulum.prodi.nama
                if hasattr(sample.mk_kelas.mata_kuliah.kurikulum, "prodi")
                and sample.mk_kelas.mata_kuliah.kurikulum.prodi
                else str(prodi_id)
            )

            # Kumpulkan label MK unik untuk pesan
            mk_labels: dict = {}
            for a in group:
                mk_id = a.mk_kelas.mata_kuliah_id
                if mk_id not in mk_labels:
                    mk_labels[mk_id] = (
                        a.mk_kelas.mata_kuliah.nama
                        if a.mk_kelas.mata_kuliah
                        else str(mk_id)
                    )

            mk_names_str = ", ".join(mk_labels.values())

            # Tentukan alasan pelanggaran
            reasons = []
            if jumlah_mk > 2:
                reasons.append(f"{jumlah_mk} MK (maks 2)")
            if total_sks > 6:
                reasons.append(f"{total_sks} SKS (maks 6)")
            reason_str = " dan ".join(reasons)

            pesan = (
                f"Beban harian mahasiswa {prodi_nama} Semester {semester} "
                f"pada hari {hari} melebihi batas: {reason_str}. "
                f"MK terjadwal: {mk_names_str}"
            )

            results.append(
                ConflictResult(
                    jenis=ConflictJenis.STUDENT_DAILY_OVERLOAD,
                    severity=ConflictSeverity.ERROR,
                    assignment_ids=[a.id for a in group],
                    pesan=pesan,
                    detail={
                        "prodi_id": str(prodi_id),
                        "prodi_nama": prodi_nama,
                        "semester": semester,
                        "hari": hari,
                        "jumlah_mk": jumlah_mk,
                        "total_sks": total_sks,
                        "mk_names": list(mk_labels.values()),
                    },
                )
            )

        return results

    def check_lecturer_daily_load(self, assignments: list[Any]) -> list[ConflictResult]:
        """HC-09: Dosen maks 2 MK atau 6 SKS per hari.

        Untuk setiap kombinasi (dosen_id, hari):
          - Kumpulkan semua assignment di mana dosen muncul sebagai dosen1 atau dosen2
          - Hitung jumlah MK unik (berdasarkan mata_kuliah_id)
          - Hitung total SKS (dari timeslot.sks, atau mk.sks sebagai fallback)
          - ERROR LECTURER_DAILY_OVERLOAD jika jumlah_mk > 2 atau total_sks > 6

        Catatan: jika dosen mengajar kelas paralel A dan B dari MK yang sama,
        itu tetap dihitung sebagai 1 MK (bukan 2).
        """
        from collections import defaultdict

        # Map: (dosen_id, hari) -> list of (assignment, dosen_obj)
        # Satu assignment bisa muncul dua kali jika dosen adalah dosen1 DAN dosen2
        # (edge case team teaching dengan dosen yang sama — tidak mungkin secara bisnis,
        # tapi kita handle defensif dengan dedup per assignment_id per dosen)
        dosen_hari: dict[tuple, list] = defaultdict(list)

        for a in assignments:
            if a.timeslot is None:
                continue
            hari = a.timeslot.hari

            # Tambahkan sebagai dosen1
            if a.dosen1_id is not None:
                dosen_hari[(a.dosen1_id, hari)].append(a)

            # Tambahkan sebagai dosen2 (jika berbeda dari dosen1)
            if a.dosen2_id is not None and a.dosen2_id != a.dosen1_id:
                dosen_hari[(a.dosen2_id, hari)].append(a)

        results: list[ConflictResult] = []

        for (dosen_id, hari), group in dosen_hari.items():
            # Deduplicate: satu assignment hanya dihitung sekali per dosen
            seen_ids: set = set()
            unique_group = []
            for a in group:
                if a.id not in seen_ids:
                    seen_ids.add(a.id)
                    unique_group.append(a)

            # Hitung MK unik
            mk_ids: set = set()
            for a in unique_group:
                if a.mk_kelas is not None and a.mk_kelas.mata_kuliah_id is not None:
                    mk_ids.add(a.mk_kelas.mata_kuliah_id)
            jumlah_mk = len(mk_ids)

            # Hitung total SKS per MK unik
            sks_per_mk: dict = {}
            for a in unique_group:
                if a.mk_kelas is None or a.mk_kelas.mata_kuliah_id is None:
                    continue
                mk_id = a.mk_kelas.mata_kuliah_id
                if mk_id not in sks_per_mk:
                    sks_per_mk[mk_id] = (
                        a.timeslot.sks
                        if a.timeslot and a.timeslot.sks
                        else (a.mk_kelas.mata_kuliah.sks if a.mk_kelas.mata_kuliah else 0)
                    )
            total_sks = sum(sks_per_mk.values())

            # Tidak ada pelanggaran
            if jumlah_mk <= 2 and total_sks <= 6:
                continue

            # Resolve nama dosen dari assignment dalam group
            dosen_obj = None
            for a in unique_group:
                if a.dosen1_id == dosen_id and a.dosen1:
                    dosen_obj = a.dosen1
                    break
                if a.dosen2_id == dosen_id and a.dosen2:
                    dosen_obj = a.dosen2
                    break

            dosen_nama = dosen_obj.nama if dosen_obj else str(dosen_id)
            dosen_kode = dosen_obj.kode if dosen_obj else ""

            # Kumpulkan label MK unik untuk pesan
            mk_labels: dict = {}
            for a in unique_group:
                if a.mk_kelas is None or a.mk_kelas.mata_kuliah_id is None:
                    continue
                mk_id = a.mk_kelas.mata_kuliah_id
                if mk_id not in mk_labels:
                    mk_labels[mk_id] = (
                        a.mk_kelas.mata_kuliah.nama
                        if a.mk_kelas.mata_kuliah
                        else str(mk_id)
                    )

            mk_names_str = ", ".join(mk_labels.values())

            reasons = []
            if jumlah_mk > 2:
                reasons.append(f"{jumlah_mk} MK (maks 2)")
            if total_sks > 6:
                reasons.append(f"{total_sks} SKS (maks 6)")
            reason_str = " dan ".join(reasons)

            pesan = (
                f"Beban harian dosen {dosen_nama} ({dosen_kode}) "
                f"pada hari {hari} melebihi batas: {reason_str}. "
                f"MK terjadwal: {mk_names_str}"
            )

            results.append(
                ConflictResult(
                    jenis=ConflictJenis.LECTURER_DAILY_OVERLOAD,
                    severity=ConflictSeverity.ERROR,
                    assignment_ids=[a.id for a in unique_group],
                    pesan=pesan,
                    detail={
                        "dosen_id": str(dosen_id),
                        "dosen_nama": dosen_nama,
                        "dosen_kode": dosen_kode,
                        "hari": hari,
                        "jumlah_mk": jumlah_mk,
                        "total_sks": total_sks,
                        "mk_names": list(mk_labels.values()),
                    },
                )
            )

        return results

    # ------------------------------------------------------------------
    # Soft Constraints
    # ------------------------------------------------------------------

    def check_student_conflict(self, assignments: list[Any]) -> list[ConflictResult]:
        """SC-01: MK satu semester satu prodi sebaiknya tidak dijadwalkan bersamaan.

        Untuk setiap kombinasi (prodi_id, semester, timeslot_id):
          - Kumpulkan semua MK unik yang dijadwalkan di slot tersebut
          - WARNING STUDENT_CONFLICT jika ada lebih dari 1 MK unik

        Ini adalah pelengkap informatif dari HC-08: HC-08 memeriksa beban per hari,
        SC-01 memeriksa tabrakan di slot yang persis sama.
        """
        from collections import defaultdict

        # Map: (prodi_id, semester, timeslot_id) -> list of assignment
        groups: dict[tuple, list] = defaultdict(list)

        for a in assignments:
            if (
                a.mk_kelas is None
                or a.mk_kelas.mata_kuliah is None
                or a.mk_kelas.mata_kuliah.kurikulum is None
                or a.timeslot is None
            ):
                continue

            mk = a.mk_kelas.mata_kuliah
            prodi_id = mk.kurikulum.prodi_id
            semester = mk.semester
            timeslot_id = a.timeslot_id

            groups[(prodi_id, semester, timeslot_id)].append(a)

        results: list[ConflictResult] = []

        for (prodi_id, semester, timeslot_id), group in groups.items():
            # Hitung MK unik di slot ini
            mk_ids: set = {a.mk_kelas.mata_kuliah_id for a in group}
            if len(mk_ids) <= 1:
                continue

            sample = group[0]
            timeslot_label = sample.timeslot.label if sample.timeslot else str(timeslot_id)
            prodi_nama = (
                sample.mk_kelas.mata_kuliah.kurikulum.prodi.nama
                if hasattr(sample.mk_kelas.mata_kuliah.kurikulum, "prodi")
                and sample.mk_kelas.mata_kuliah.kurikulum.prodi
                else str(prodi_id)
            )

            # Kumpulkan nama MK unik
            mk_labels: dict = {}
            for a in group:
                mk_id = a.mk_kelas.mata_kuliah_id
                if mk_id not in mk_labels:
                    mk_labels[mk_id] = (
                        a.mk_kelas.mata_kuliah.nama if a.mk_kelas.mata_kuliah else str(mk_id)
                    )

            mk_names_str = ", ".join(mk_labels.values())
            pesan = (
                f"{len(mk_ids)} MK Semester {semester} {prodi_nama} "
                f"dijadwalkan bersamaan di {timeslot_label}: {mk_names_str}"
            )

            results.append(
                ConflictResult(
                    jenis=ConflictJenis.STUDENT_CONFLICT,
                    severity=ConflictSeverity.WARNING,
                    assignment_ids=[a.id for a in group],
                    pesan=pesan,
                    detail={
                        "prodi_id": str(prodi_id),
                        "prodi_nama": prodi_nama,
                        "semester": semester,
                        "timeslot_id": str(timeslot_id),
                        "timeslot_label": timeslot_label,
                        "jumlah_mk": len(mk_ids),
                        "mk_names": list(mk_labels.values()),
                    },
                )
            )

        return results

    def check_workload_equity(self, assignments: list[Any]) -> list[ConflictResult]:
        """SC-02: Distribusi beban SKS antar dosen dalam satu prodi sebaiknya merata.

        Untuk setiap prodi (berdasarkan homebase_prodi_id dosen):
          - Hitung total SKS per dosen (dari semua assignment sebagai dosen1 atau dosen2)
          - Hitung simpangan baku (std dev) beban SKS
          - WARNING WORKLOAD_INEQUITY jika std_dev > threshold (default: 6 SKS)

        Threshold dapat dikonfigurasi via WORKLOAD_EQUITY_THRESHOLD_SKS.
        """
        import math
        from collections import defaultdict

        THRESHOLD_STD_DEV = 6  # SKS — dapat dijadikan konfigurasi di masa depan

        # Map: dosen_id -> total SKS (dihitung dari semua assignment)
        dosen_sks: dict = defaultdict(int)
        # Map: dosen_id -> prodi_id (homebase)
        dosen_prodi: dict = {}
        # Map: dosen_id -> dosen_obj (untuk nama)
        dosen_obj_map: dict = {}

        for a in assignments:
            if a.timeslot is None:
                continue
            sks = a.timeslot.sks or 0

            if a.dosen1_id is not None:
                dosen_sks[a.dosen1_id] += sks
                if a.dosen1_id not in dosen_prodi and a.dosen1:
                    dosen_prodi[a.dosen1_id] = getattr(a.dosen1, "homebase_prodi_id", None)
                    dosen_obj_map[a.dosen1_id] = a.dosen1

            if a.dosen2_id is not None:
                dosen_sks[a.dosen2_id] += sks
                if a.dosen2_id not in dosen_prodi and a.dosen2:
                    dosen_prodi[a.dosen2_id] = getattr(a.dosen2, "homebase_prodi_id", None)
                    dosen_obj_map[a.dosen2_id] = a.dosen2

        if not dosen_sks:
            return []

        # Kelompokkan dosen per prodi
        prodi_dosen: dict = defaultdict(list)
        for dosen_id, sks in dosen_sks.items():
            prodi_id = dosen_prodi.get(dosen_id)
            prodi_dosen[prodi_id].append((dosen_id, sks))

        results: list[ConflictResult] = []

        for prodi_id, dosen_list in prodi_dosen.items():
            if len(dosen_list) < 2:
                continue  # Tidak bisa hitung std dev dengan < 2 dosen

            sks_values = [sks for _, sks in dosen_list]
            mean = sum(sks_values) / len(sks_values)
            variance = sum((x - mean) ** 2 for x in sks_values) / len(sks_values)
            std_dev = math.sqrt(variance)

            if std_dev <= THRESHOLD_STD_DEV:
                continue

            # Resolve nama prodi dari dosen pertama yang punya homebase
            prodi_nama = str(prodi_id) if prodi_id else "Tidak Diketahui"
            for dosen_id, _ in dosen_list:
                dosen_obj = dosen_obj_map.get(dosen_id)
                if dosen_obj and hasattr(dosen_obj, "homebase_prodi") and dosen_obj.homebase_prodi:
                    prodi_nama = dosen_obj.homebase_prodi.nama
                    break

            # Bangun breakdown per dosen
            breakdown = []
            for dosen_id, sks in sorted(dosen_list, key=lambda x: x[1], reverse=True):
                dosen_obj = dosen_obj_map.get(dosen_id)
                breakdown.append({
                    "dosen_id": str(dosen_id),
                    "dosen_nama": dosen_obj.nama if dosen_obj else str(dosen_id),
                    "dosen_kode": dosen_obj.kode if dosen_obj else "",
                    "total_sks": sks,
                })

            pesan = (
                f"Distribusi beban SKS dosen di {prodi_nama} tidak merata: "
                f"std dev = {std_dev:.1f} SKS (threshold {THRESHOLD_STD_DEV} SKS). "
                f"Rentang: {min(sks_values)}–{max(sks_values)} SKS"
            )

            # Kumpulkan semua assignment_ids yang terlibat dosen di prodi ini
            dosen_ids_in_prodi = {d_id for d_id, _ in dosen_list}
            involved_ids = [
                a.id for a in assignments
                if a.dosen1_id in dosen_ids_in_prodi
                or (a.dosen2_id is not None and a.dosen2_id in dosen_ids_in_prodi)
            ]

            results.append(
                ConflictResult(
                    jenis=ConflictJenis.WORKLOAD_INEQUITY,
                    severity=ConflictSeverity.WARNING,
                    assignment_ids=involved_ids,
                    pesan=pesan,
                    detail={
                        "prodi_id": str(prodi_id) if prodi_id else None,
                        "prodi_nama": prodi_nama,
                        "std_dev": round(std_dev, 2),
                        "mean_sks": round(mean, 2),
                        "threshold": THRESHOLD_STD_DEV,
                        "breakdown": breakdown,
                    },
                )
            )

        return results

    def check_lecturer_preference(self, assignments: list[Any]) -> list[ConflictResult]:
        """SC-03: Preferensi hari mengajar dosen sebaiknya diprioritaskan.

        Untuk setiap dosen dalam sesi:
          - Ambil semua DosenPreference yang terkait sesi ini
          - Bandingkan timeslot preferensi dengan assignment aktual dosen
          - Jika dosen dijadwalkan di hari yang TIDAK ada dalam preferensinya → violated
          - Update is_violated = TRUE pada record DosenPreference yang dilanggar
          - Kembalikan WARNING LECTURER_PREFERENCE_VIOLATED per preferensi yang dilanggar
        """
        from app.models.dosen import DosenPreference

        if not assignments:
            return []

        sesi_id = assignments[0].sesi_id

        # Kumpulkan semua dosen_id yang terlibat
        dosen_ids: set[UUID] = set()
        for a in assignments:
            if a.dosen1_id:
                dosen_ids.add(a.dosen1_id)
            if a.dosen2_id:
                dosen_ids.add(a.dosen2_id)

        if not dosen_ids:
            return []

        # Query semua preferensi untuk sesi ini
        prefs = (
            self.db.query(DosenPreference)
            .filter(
                DosenPreference.dosen_id.in_(dosen_ids),
                DosenPreference.sesi_id == sesi_id,
            )
            .all()
        )

        if not prefs:
            return []

        # Bangun map: dosen_id -> set of timeslot_id yang dipreferensikan
        dosen_pref_timeslots: dict[UUID, set] = {}
        for pref in prefs:
            dosen_pref_timeslots.setdefault(pref.dosen_id, set()).add(pref.timeslot_id)

        # Bangun map: dosen_id -> set of timeslot_id yang aktual dijadwalkan
        dosen_actual_timeslots: dict[UUID, set] = {}
        dosen_obj_map: dict[UUID, Any] = {}
        for a in assignments:
            if a.timeslot_id is None:
                continue
            for dosen_id, dosen_obj in [
                (a.dosen1_id, a.dosen1),
                (a.dosen2_id, a.dosen2),
            ]:
                if dosen_id is None:
                    continue
                dosen_actual_timeslots.setdefault(dosen_id, set()).add(a.timeslot_id)
                if dosen_id not in dosen_obj_map and dosen_obj:
                    dosen_obj_map[dosen_id] = dosen_obj

        results: list[ConflictResult] = []
        total_violated = 0

        for pref in prefs:
            dosen_id = pref.dosen_id
            pref_timeslot_id = pref.timeslot_id

            # Cek apakah dosen dijadwalkan di timeslot yang dipreferensikan
            actual = dosen_actual_timeslots.get(dosen_id, set())

            # Preferensi dilanggar jika timeslot preferensi tidak ada dalam jadwal aktual
            # (dosen tidak mendapat slot yang ia inginkan)
            is_violated = pref_timeslot_id not in actual

            # Update is_violated di DB
            if pref.is_violated != is_violated:
                pref.is_violated = is_violated
                self.db.add(pref)

            if not is_violated:
                continue

            total_violated += 1

            dosen_obj = dosen_obj_map.get(dosen_id)
            dosen_nama = dosen_obj.nama if dosen_obj else str(dosen_id)
            dosen_kode = dosen_obj.kode if dosen_obj else ""

            # Cari label timeslot preferensi dari assignment yang ada
            pref_ts_label = str(pref_timeslot_id)
            for a in assignments:
                if a.timeslot_id == pref_timeslot_id and a.timeslot:
                    pref_ts_label = a.timeslot.label
                    break

            # Kumpulkan assignment_ids dosen ini
            dosen_assignment_ids = [
                a.id for a in assignments
                if a.dosen1_id == dosen_id or a.dosen2_id == dosen_id
            ]

            pesan = (
                f"Preferensi dosen {dosen_nama} ({dosen_kode}) tidak dipenuhi: "
                f"menginginkan slot {pref_ts_label} "
                f"(fase: {pref.fase})"
            )

            results.append(
                ConflictResult(
                    jenis=ConflictJenis.LECTURER_PREFERENCE_VIOLATED,
                    severity=ConflictSeverity.WARNING,
                    assignment_ids=dosen_assignment_ids,
                    pesan=pesan,
                    detail={
                        "dosen_id": str(dosen_id),
                        "dosen_nama": dosen_nama,
                        "dosen_kode": dosen_kode,
                        "preference_id": str(pref.id),
                        "timeslot_id": str(pref_timeslot_id),
                        "timeslot_label": pref_ts_label,
                        "fase": pref.fase,
                        "total_violated": total_violated,
                    },
                )
            )

        # Commit perubahan is_violated ke DB
        if results:
            self.db.commit()

        return results

    def check_floor_priority(self, assignments: list[Any]) -> list[ConflictResult]:
        """SC-05: Dosen senior diprioritaskan di lantai lebih rendah (kondisional).

        Untuk setiap timeslot dalam sesi:
          - Ambil semua assignment yang memiliki ruang_id, dosen.tgl_lahir terisi,
            dan override_floor_priority = FALSE
          - Urutkan dosen berdasarkan usia (senior = tgl_lahir lebih awal = lebih tua)
          - Bandingkan dengan urutan lantai ruang (senior seharusnya di lantai lebih rendah)
          - WARNING FLOOR_PRIORITY_VIOLATED jika dosen senior di lantai lebih tinggi
            dari dosen yang lebih muda
          - Lewati jika ruang.lantai NULL
        """
        from collections import defaultdict
        from itertools import combinations

        # Map: timeslot_id -> list of assignment (yang eligible untuk pengecekan)
        timeslot_groups: dict = defaultdict(list)

        for a in assignments:
            # Skip jika tidak ada ruang
            if a.ruang_id is None or a.ruang is None:
                continue
            # Skip jika lantai NULL
            if a.ruang.lantai is None:
                continue
            # Skip jika override aktif
            if a.override_floor_priority:
                continue
            # Skip jika dosen1 tidak punya tgl_lahir
            if a.dosen1 is None or a.dosen1.tgl_lahir is None:
                continue

            timeslot_groups[a.timeslot_id].append(a)

        results: list[ConflictResult] = []

        for timeslot_id, group in timeslot_groups.items():
            if len(group) < 2:
                continue

            # Periksa setiap pasangan assignment di timeslot yang sama
            for a1, a2 in combinations(group, 2):
                dosen1_tgl = a1.dosen1.tgl_lahir
                dosen2_tgl = a2.dosen1.tgl_lahir

                lantai1 = a1.ruang.lantai
                lantai2 = a2.ruang.lantai

                # Tentukan siapa yang lebih senior (tgl_lahir lebih awal = lebih tua)
                # senior_a = assignment dengan dosen lebih tua
                if dosen1_tgl < dosen2_tgl:
                    # a1 lebih senior
                    senior_a, junior_a = a1, a2
                    senior_lantai, junior_lantai = lantai1, lantai2
                elif dosen2_tgl < dosen1_tgl:
                    # a2 lebih senior
                    senior_a, junior_a = a2, a1
                    senior_lantai, junior_lantai = lantai2, lantai1
                else:
                    # Usia sama — tidak ada pelanggaran
                    continue

                # Pelanggaran: senior di lantai LEBIH TINGGI dari junior
                if senior_lantai <= junior_lantai:
                    continue  # Urutan benar atau sama

                # Pelanggaran ditemukan
                senior_dosen = senior_a.dosen1
                junior_dosen = junior_a.dosen1
                ts_label = senior_a.timeslot.label if senior_a.timeslot else str(timeslot_id)

                pesan = (
                    f"Prioritas lantai dilanggar pada {ts_label}: "
                    f"dosen senior {senior_dosen.nama} ({senior_dosen.kode}) "
                    f"di lantai {senior_lantai}, "
                    f"dosen junior {junior_dosen.nama} ({junior_dosen.kode}) "
                    f"di lantai {junior_lantai}"
                )

                results.append(
                    ConflictResult(
                        jenis=ConflictJenis.FLOOR_PRIORITY_VIOLATED,
                        severity=ConflictSeverity.WARNING,
                        assignment_ids=[senior_a.id, junior_a.id],
                        pesan=pesan,
                        detail={
                            "timeslot_id": str(timeslot_id),
                            "timeslot_label": ts_label,
                            "senior_dosen_id": str(senior_a.dosen1_id),
                            "senior_dosen_nama": senior_dosen.nama,
                            "senior_dosen_kode": senior_dosen.kode,
                            "senior_tgl_lahir": str(senior_dosen.tgl_lahir),
                            "senior_lantai": senior_lantai,
                            "junior_dosen_id": str(junior_a.dosen1_id),
                            "junior_dosen_nama": junior_dosen.nama,
                            "junior_dosen_kode": junior_dosen.kode,
                            "junior_tgl_lahir": str(junior_dosen.tgl_lahir),
                            "junior_lantai": junior_lantai,
                        },
                    )
                )

        return results
