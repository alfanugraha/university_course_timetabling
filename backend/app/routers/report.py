"""
backend/app/routers/report.py
Endpoints laporan untuk sesi jadwal.

GET /sesi/{sesi_id}/reports/sks-rekap  — rekap total SKS per dosen dengan breakdown per prodi
GET /sesi/{sesi_id}/reports/room-map   — peta penggunaan ruang: matrix hari × slot × ruang
"""

import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import EDITOR_ROLES_JURUSAN, VIEWER_ROLES, require_role
from app.database import get_db
from app.models.jadwal_assignment import JadwalAssignment
from app.models.mata_kuliah import MataKuliahKelas, MataKuliah
from app.models.kurikulum import Kurikulum
from app.models.prodi import Prodi
from app.models.dosen import Dosen
from app.models.ruang import Ruang
from app.models.timeslot import Timeslot
from app.models.sesi_jadwal import SesiJadwal
from app.schemas.report import DosenSksRekap, SksRekapResponse, RoomCellInfo, RoomMapSlot, RoomMapResponse

router = APIRouter(prefix="/sesi", tags=["report"])

# Roles yang dapat mengakses laporan SKS rekap
_SKS_REKAP_ROLES = EDITOR_ROLES_JURUSAN + VIEWER_ROLES + ["koordinator_prodi"]


def _get_sesi_or_404(db: Session, sesi_id: uuid.UUID) -> SesiJadwal:
    sesi = db.get(SesiJadwal, sesi_id)
    if sesi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SesiJadwal dengan id '{sesi_id}' tidak ditemukan",
        )
    return sesi


def _compute_bkd_flag(total_sks: int, bkd_limit_sks: int | None) -> str:
    """Hitung BKD flag berdasarkan total SKS dan limit BKD dosen.

    - NULL limit  → "no_limit"
    - >= limit    → "over_limit"
    - >= 80% limit → "near_limit"
    - otherwise   → "ok"
    """
    if bkd_limit_sks is None:
        return "no_limit"
    if total_sks >= bkd_limit_sks:
        return "over_limit"
    if total_sks >= 0.8 * bkd_limit_sks:
        return "near_limit"
    return "ok"


# ---------------------------------------------------------------------------
# GET /sesi/{sesi_id}/reports/sks-rekap
# ---------------------------------------------------------------------------

@router.get(
    "/{sesi_id}/reports/sks-rekap",
    response_model=SksRekapResponse,
)
def get_sks_rekap(
    sesi_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(_SKS_REKAP_ROLES)),
):
    """Rekap total SKS per dosen untuk sesi yang diberikan.

    Setiap dosen mendapat breakdown SKS per prodi (S1 MTK, S1 STK, S2 MTK, Layanan, dll).
    Untuk MK dengan kategori prodi "Layanan", breakdown key = "Layanan" (bukan singkat prodi).
    Dosen1 dan dosen2 masing-masing mendapat kredit penuh SKS (tidak dibagi).

    BKD flag (informasional, tidak memblokir):
    - "no_limit"   → bkd_limit_sks NULL
    - "over_limit" → total_sks >= bkd_limit_sks
    - "near_limit" → total_sks >= 80% bkd_limit_sks
    - "ok"         → di bawah threshold

    Akses: admin, sekretaris_jurusan, tendik_jurusan, ketua_jurusan, koordinator_prodi
    """
    _get_sesi_or_404(db, sesi_id)

    # Query semua assignment dalam sesi ini dengan eager loading relasi yang dibutuhkan
    assignments = (
        db.query(JadwalAssignment)
        .filter(JadwalAssignment.sesi_id == sesi_id)
        .options(
            joinedload(JadwalAssignment.timeslot),
            joinedload(JadwalAssignment.dosen1),
            joinedload(JadwalAssignment.dosen2),
            joinedload(JadwalAssignment.mk_kelas).joinedload(
                MataKuliahKelas.mata_kuliah
            ).joinedload(
                MataKuliah.kurikulum
            ).joinedload(
                Kurikulum.prodi
            ),
        )
        .all()
    )

    # Akumulasi SKS per dosen per prodi_key
    # dosen_sks[dosen_id] = {"S1 MTK": 6, "Layanan": 3, ...}
    dosen_sks: dict[uuid.UUID, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # Cache info dosen
    dosen_info: dict[uuid.UUID, Dosen] = {}

    for assignment in assignments:
        sks = assignment.timeslot.sks

        # Tentukan breakdown key berdasarkan kategori prodi
        prodi: Prodi = assignment.mk_kelas.mata_kuliah.kurikulum.prodi
        if prodi.kategori == "Layanan":
            prodi_key = "Layanan"
        else:
            prodi_key = prodi.singkat

        # Kredit ke dosen1
        d1: Dosen = assignment.dosen1
        dosen_sks[d1.id][prodi_key] += sks
        dosen_info[d1.id] = d1

        # Kredit ke dosen2 jika ada
        if assignment.dosen2 is not None:
            d2: Dosen = assignment.dosen2
            dosen_sks[d2.id][prodi_key] += sks
            dosen_info[d2.id] = d2

    # Bangun response items
    items: list[DosenSksRekap] = []
    for dosen_id, breakdown in dosen_sks.items():
        dosen = dosen_info[dosen_id]
        total_sks = sum(breakdown.values())
        items.append(
            DosenSksRekap(
                dosen_id=dosen_id,
                dosen_nama=dosen.nama,
                dosen_kode=dosen.kode,
                total_sks=total_sks,
                breakdown=dict(breakdown),
                bkd_limit_sks=dosen.bkd_limit_sks,
                bkd_flag=_compute_bkd_flag(total_sks, dosen.bkd_limit_sks),
            )
        )

    # Urutkan berdasarkan total_sks descending, lalu nama ascending
    items.sort(key=lambda x: (-x.total_sks, x.dosen_nama))

    return SksRekapResponse(
        sesi_id=sesi_id,
        items=items,
        total_dosen=len(items),
    )


# ---------------------------------------------------------------------------
# GET /sesi/{sesi_id}/reports/room-map
# ---------------------------------------------------------------------------

# Urutan hari kanonik sesuai 15 timeslot tetap
_HARI_ORDER = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]

_ROOM_MAP_ROLES = EDITOR_ROLES_JURUSAN + VIEWER_ROLES


@router.get(
    "/{sesi_id}/reports/room-map",
    response_model=RoomMapResponse,
)
def get_room_map(
    sesi_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role(_ROOM_MAP_ROLES)),
):
    """Peta penggunaan ruang untuk sesi yang diberikan.

    Mengembalikan matrix hari × slot × ruang. Setiap sel berisi kode MK
    beserta detail (nama MK, kelas, dosen) jika ada assignment, atau null
    jika kosong.

    Hanya ruang aktif (is_active=True) yang disertakan.
    Semua 15 timeslot tetap selalu muncul (sel kosong = null).

    Akses: admin, sekretaris_jurusan, tendik_jurusan, ketua_jurusan
    """
    _get_sesi_or_404(db, sesi_id)

    # Ambil semua ruang aktif, urut berdasarkan nama
    active_rooms: list[Ruang] = (
        db.query(Ruang)
        .filter(Ruang.is_active == True)  # noqa: E712
        .order_by(Ruang.nama)
        .all()
    )
    room_names = [r.nama for r in active_rooms]

    # Ambil semua 15 timeslot, urut hari → sesi
    all_timeslots: list[Timeslot] = (
        db.query(Timeslot)
        .order_by(Timeslot.hari, Timeslot.sesi)
        .all()
    )
    # Urutkan sesuai urutan hari kanonik
    all_timeslots.sort(key=lambda ts: (_HARI_ORDER.index(ts.hari) if ts.hari in _HARI_ORDER else 99, ts.sesi))

    # Ambil semua assignment dalam sesi ini yang memiliki ruang
    assignments = (
        db.query(JadwalAssignment)
        .filter(
            JadwalAssignment.sesi_id == sesi_id,
            JadwalAssignment.ruang_id.isnot(None),
        )
        .options(
            joinedload(JadwalAssignment.ruang),
            joinedload(JadwalAssignment.timeslot),
            joinedload(JadwalAssignment.dosen1),
            joinedload(JadwalAssignment.dosen2),
            joinedload(JadwalAssignment.mk_kelas).joinedload(MataKuliahKelas.mata_kuliah),
        )
        .all()
    )

    # Bangun lookup: (timeslot_id, ruang_nama) → RoomCellInfo
    cell_map: dict[tuple[uuid.UUID, str], RoomCellInfo] = {}
    for a in assignments:
        if a.ruang is None:
            continue
        mk = a.mk_kelas.mata_kuliah
        dosen_label = a.dosen1.nama
        if a.dosen2 is not None:
            dosen_label += f" / {a.dosen2.nama}"
        cell_map[(a.timeslot_id, a.ruang.nama)] = RoomCellInfo(
            kode_mk=mk.kode,
            nama_mk=mk.nama,
            kelas=a.mk_kelas.kelas,
            dosen=dosen_label,
        )

    # Bangun daftar slot dengan isi per ruang
    slots: list[RoomMapSlot] = []
    for ts in all_timeslots:
        rooms_dict: dict[str, RoomCellInfo | None] = {
            rn: cell_map.get((ts.id, rn)) for rn in room_names
        }
        slots.append(RoomMapSlot(
            hari=ts.hari,
            sesi=ts.sesi,
            label=ts.label,
            rooms=rooms_dict,
        ))

    # Hari unik dalam urutan kanonik
    days_seen = []
    for ts in all_timeslots:
        if ts.hari not in days_seen:
            days_seen.append(ts.hari)

    return RoomMapResponse(
        sesi_id=sesi_id,
        rooms=room_names,
        days=days_seen,
        slots=slots,
    )
