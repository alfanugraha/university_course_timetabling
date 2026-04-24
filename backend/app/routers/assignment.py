"""
backend/app/routers/assignment.py
Endpoint untuk manajemen JadwalAssignment dalam sebuah SesiJadwal.

GET  /sesi/{id}/assignments — daftar assignment dengan filtering dan pagination
POST /sesi/{id}/assignments — tambah assignment baru
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import ALL_ROLES, EDITOR_ROLES_JURUSAN, EDITOR_ROLES_PRODI, require_role
from app.database import get_db
from app.models.dosen import Dosen
from app.models.jadwal_assignment import JadwalAssignment
from app.models.kurikulum import Kurikulum
from app.models.mata_kuliah import MataKuliah, MataKuliahKelas
from app.models.ruang import Ruang
from app.models.sesi_jadwal import SesiJadwal
from app.models.timeslot import Timeslot
from app.models.jadwal_assignment import TeamTeachingOrder
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentListResponse,
    AssignmentResponse,
    AssignmentUpdate,
    MkKelasInfo,
    ProdiInfo,
    TeamTeachingResponse,
    TeamTeachingSetRequest,
    TeamTeachingSwapRequest,
)

router = APIRouter(prefix="/sesi", tags=["assignment"])


def _get_sesi_or_404(db: Session, sesi_id: uuid.UUID) -> SesiJadwal:
    sesi = db.get(SesiJadwal, sesi_id)
    if sesi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SesiJadwal dengan id '{sesi_id}' tidak ditemukan",
        )
    return sesi


def _build_assignment_response(a: JadwalAssignment) -> AssignmentResponse:
    """Build AssignmentResponse from ORM object with joined relationships."""
    mk_kelas = a.mk_kelas
    mk = mk_kelas.mata_kuliah
    kurikulum = mk.kurikulum
    prodi = kurikulum.prodi

    prodi_info = ProdiInfo(
        id=prodi.id,
        kode=prodi.kode,
        nama=prodi.nama,
        singkat=prodi.singkat,
    )

    mk_kelas_info = MkKelasInfo(
        id=mk_kelas.id,
        label=mk_kelas.label,
        kelas=mk_kelas.kelas,
        mata_kuliah_kode=mk.kode,
        mata_kuliah_nama=mk.nama,
        semester=mk.semester,
        sks=mk.sks,
        prodi=prodi_info,
    )

    return AssignmentResponse(
        id=a.id,
        sesi_id=a.sesi_id,
        mk_kelas_id=a.mk_kelas_id,
        dosen1_id=a.dosen1_id,
        dosen2_id=a.dosen2_id,
        timeslot_id=a.timeslot_id,
        ruang_id=a.ruang_id,
        override_floor_priority=a.override_floor_priority,
        catatan=a.catatan,
        created_at=a.created_at,
        updated_at=a.updated_at,
        mk_kelas=mk_kelas_info,
        dosen1=a.dosen1,
        dosen2=a.dosen2,
        timeslot=a.timeslot,
        ruang=a.ruang,
    )


@router.get("/{sesi_id}/assignments", response_model=AssignmentListResponse)
def list_assignments(
    sesi_id: uuid.UUID,
    prodi_id: Optional[uuid.UUID] = Query(None),
    hari: Optional[str] = Query(None),
    semester: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Kembalikan daftar assignment dalam sesi dengan filtering dan pagination.

    Role-based filtering:
    - koordinator_prodi / tendik_prodi: hanya prodi sendiri
    - dosen: hanya assignment dirinya (dosen1 atau dosen2)
    - ketua_jurusan / admin / sekretaris_jurusan / tendik_jurusan: semua
    """
    _get_sesi_or_404(db, sesi_id)

    q = (
        db.query(JadwalAssignment)
        .join(JadwalAssignment.mk_kelas)
        .join(MataKuliahKelas.mata_kuliah)
        .join(MataKuliah.kurikulum)
        .join(Kurikulum.prodi)
        .join(JadwalAssignment.timeslot)
        .filter(JadwalAssignment.sesi_id == sesi_id)
    )

    # --- Role-based filtering ---
    role = current_user.role

    if role in ("koordinator_prodi", "tendik_prodi"):
        if current_user.prodi_id is None:
            # No prodi assigned → return empty
            return AssignmentListResponse(items=[], total=0, page=page, page_size=page_size)
        q = q.filter(Kurikulum.prodi_id == current_user.prodi_id)

    elif role == "dosen":
        # Find the Dosen record linked to this user
        dosen = db.query(Dosen).filter(Dosen.user_id == current_user.id).first()
        if dosen is None:
            return AssignmentListResponse(items=[], total=0, page=page, page_size=page_size)
        q = q.filter(
            (JadwalAssignment.dosen1_id == dosen.id)
            | (JadwalAssignment.dosen2_id == dosen.id)
        )

    # else: ketua_jurusan, admin, sekretaris_jurusan, tendik_jurusan → no extra filter

    # --- Additional filters ---
    if prodi_id is not None:
        q = q.filter(Kurikulum.prodi_id == prodi_id)

    if hari is not None:
        q = q.filter(Timeslot.hari == hari)

    if semester is not None:
        q = q.filter(MataKuliah.semester == semester)

    total = q.count()

    assignments = (
        q.order_by(JadwalAssignment.created_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_build_assignment_response(a) for a in assignments]

    return AssignmentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{sesi_id}/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    sesi_id: uuid.UUID,
    body: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(EDITOR_ROLES_PRODI)),
):
    """Tambah assignment baru ke dalam sesi jadwal.

    Validasi:
    - Sesi harus ada dan berstatus Draft atau Aktif (bukan Arsip)
    - dosen1 harus ada dan berstatus Aktif
    - dosen2 (jika ada) harus ada dan berstatus Aktif
    - timeslot_id harus ada
    - ruang_id (jika ada) harus ada dan is_active=True
    - mk_kelas_id harus ada
    - HC-05: tidak boleh duplikat (sesi_id, mk_kelas_id)
    - koordinator_prodi / tendik_prodi: hanya boleh untuk prodi sendiri
    """
    # 1. Validasi sesi
    sesi = _get_sesi_or_404(db, sesi_id)
    if sesi.status == "Arsip":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tidak dapat menambah assignment pada sesi berstatus 'Arsip'.",
        )

    # 2. Validasi mk_kelas
    mk_kelas = db.get(MataKuliahKelas, body.mk_kelas_id)
    if mk_kelas is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MataKuliahKelas dengan id '{body.mk_kelas_id}' tidak ditemukan.",
        )

    # 3. Prodi-scoped access check (koordinator_prodi / tendik_prodi)
    role = current_user.role
    if role in ("koordinator_prodi", "tendik_prodi"):
        mk = mk_kelas.mata_kuliah
        kurikulum = mk.kurikulum
        if current_user.prodi_id is None or kurikulum.prodi_id != current_user.prodi_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda hanya dapat menambah assignment untuk prodi Anda sendiri.",
            )

    # 4. Validasi dosen1
    dosen1 = db.get(Dosen, body.dosen1_id)
    if dosen1 is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dosen dengan id '{body.dosen1_id}' tidak ditemukan.",
        )
    if dosen1.status != "Aktif":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dosen '{dosen1.nama}' tidak aktif.",
        )

    # 5. Validasi dosen2 (opsional)
    if body.dosen2_id is not None:
        dosen2 = db.get(Dosen, body.dosen2_id)
        if dosen2 is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dosen2 dengan id '{body.dosen2_id}' tidak ditemukan.",
            )
        if dosen2.status != "Aktif":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dosen2 '{dosen2.nama}' tidak aktif.",
            )

    # 6. Validasi timeslot
    timeslot = db.get(Timeslot, body.timeslot_id)
    if timeslot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timeslot dengan id '{body.timeslot_id}' tidak ditemukan.",
        )

    # 7. Validasi ruang (opsional)
    if body.ruang_id is not None:
        ruang = db.get(Ruang, body.ruang_id)
        if ruang is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ruang dengan id '{body.ruang_id}' tidak ditemukan.",
            )
        if not ruang.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Ruang '{ruang.nama}' tidak aktif.",
            )

    # 8. HC-05: cek duplikat (sesi_id, mk_kelas_id)
    existing = (
        db.query(JadwalAssignment)
        .filter(
            JadwalAssignment.sesi_id == sesi_id,
            JadwalAssignment.mk_kelas_id == body.mk_kelas_id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Assignment untuk mk_kelas '{body.mk_kelas_id}' "
                f"sudah ada dalam sesi ini (HC-05)."
            ),
        )

    # 9. Buat assignment baru
    assignment = JadwalAssignment(
        sesi_id=sesi_id,
        mk_kelas_id=body.mk_kelas_id,
        dosen1_id=body.dosen1_id,
        dosen2_id=body.dosen2_id,
        timeslot_id=body.timeslot_id,
        ruang_id=body.ruang_id,
        override_floor_priority=body.override_floor_priority,
        catatan=body.catatan,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return _build_assignment_response(assignment)


@router.put(
    "/{sesi_id}/assignments/{assignment_id}",
    response_model=AssignmentResponse,
)
def update_assignment(
    sesi_id: uuid.UUID,
    assignment_id: uuid.UUID,
    body: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(EDITOR_ROLES_PRODI)),
):
    """Update assignment yang sudah ada dalam sesi jadwal.

    Validasi:
    - Sesi harus ada dan berstatus Draft atau Aktif (bukan Arsip)
    - Assignment harus ada dan milik sesi tersebut
    - koordinator_prodi / tendik_prodi: hanya boleh update assignment prodi sendiri
    - Jika mk_kelas_id diubah: cek tidak duplikat (sesi_id, mk_kelas_id)
    - dosen1 (jika diubah) harus ada dan Aktif
    - dosen2 (jika diubah) harus ada dan Aktif
    - timeslot (jika diubah) harus ada
    - ruang (jika diubah) harus ada dan is_active=True
    - updated_at diperbarui otomatis oleh SQLAlchemy onupdate
    """
    # 1. Validasi sesi
    sesi = _get_sesi_or_404(db, sesi_id)
    if sesi.status == "Arsip":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat mengubah assignment pada sesi berstatus 'Arsip'.",
        )

    # 2. Ambil assignment dan pastikan milik sesi ini
    assignment = db.get(JadwalAssignment, assignment_id)
    if assignment is None or assignment.sesi_id != sesi_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment dengan id '{assignment_id}' tidak ditemukan dalam sesi ini.",
        )

    # 3. Prodi-scoped access check (koordinator_prodi / tendik_prodi)
    role = current_user.role
    if role in ("koordinator_prodi", "tendik_prodi"):
        mk_kelas_current = db.get(MataKuliahKelas, assignment.mk_kelas_id)
        if mk_kelas_current is not None:
            kurikulum = mk_kelas_current.mata_kuliah.kurikulum
            if current_user.prodi_id is None or kurikulum.prodi_id != current_user.prodi_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Anda hanya dapat mengubah assignment untuk prodi Anda sendiri.",
                )

    # 4. Validasi mk_kelas_id baru (jika diubah)
    if body.mk_kelas_id is not None and body.mk_kelas_id != assignment.mk_kelas_id:
        new_mk_kelas = db.get(MataKuliahKelas, body.mk_kelas_id)
        if new_mk_kelas is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MataKuliahKelas dengan id '{body.mk_kelas_id}' tidak ditemukan.",
            )
        # Prodi check for new mk_kelas too
        if role in ("koordinator_prodi", "tendik_prodi"):
            kurikulum = new_mk_kelas.mata_kuliah.kurikulum
            if current_user.prodi_id is None or kurikulum.prodi_id != current_user.prodi_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Anda hanya dapat mengubah assignment untuk prodi Anda sendiri.",
                )
        # HC-05: cek duplikat
        existing = (
            db.query(JadwalAssignment)
            .filter(
                JadwalAssignment.sesi_id == sesi_id,
                JadwalAssignment.mk_kelas_id == body.mk_kelas_id,
                JadwalAssignment.id != assignment_id,
            )
            .first()
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Assignment untuk mk_kelas '{body.mk_kelas_id}' "
                    f"sudah ada dalam sesi ini (HC-05)."
                ),
            )
        assignment.mk_kelas_id = body.mk_kelas_id

    # 5. Validasi dosen1 (jika diubah)
    if body.dosen1_id is not None:
        dosen1 = db.get(Dosen, body.dosen1_id)
        if dosen1 is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dosen dengan id '{body.dosen1_id}' tidak ditemukan.",
            )
        if dosen1.status != "Aktif":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dosen '{dosen1.nama}' tidak aktif.",
            )
        assignment.dosen1_id = body.dosen1_id

    # 6. Validasi dosen2 (jika diubah — None berarti hapus, UUID berarti set)
    if "dosen2_id" in body.model_fields_set:
        if body.dosen2_id is not None:
            dosen2 = db.get(Dosen, body.dosen2_id)
            if dosen2 is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dosen2 dengan id '{body.dosen2_id}' tidak ditemukan.",
                )
            if dosen2.status != "Aktif":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Dosen2 '{dosen2.nama}' tidak aktif.",
                )
        assignment.dosen2_id = body.dosen2_id

    # 7. Validasi timeslot (jika diubah)
    if body.timeslot_id is not None:
        timeslot = db.get(Timeslot, body.timeslot_id)
        if timeslot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timeslot dengan id '{body.timeslot_id}' tidak ditemukan.",
            )
        assignment.timeslot_id = body.timeslot_id

    # 8. Validasi ruang (jika diubah — None berarti hapus, UUID berarti set)
    if "ruang_id" in body.model_fields_set:
        if body.ruang_id is not None:
            ruang = db.get(Ruang, body.ruang_id)
            if ruang is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ruang dengan id '{body.ruang_id}' tidak ditemukan.",
                )
            if not ruang.is_active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Ruang '{ruang.nama}' tidak aktif.",
                )
        assignment.ruang_id = body.ruang_id

    # 9. Update catatan (jika diubah)
    if "catatan" in body.model_fields_set:
        assignment.catatan = body.catatan

    db.commit()
    db.refresh(assignment)

    return _build_assignment_response(assignment)


@router.delete(
    "/{sesi_id}/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assignment(
    sesi_id: uuid.UUID,
    assignment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Hapus assignment (hard delete).

    Akses: EDITOR_ROLES_JURUSAN (admin, sekretaris_jurusan, tendik_jurusan).
    Kembalikan HTTP 204 No Content jika berhasil.
    """
    _get_sesi_or_404(db, sesi_id)

    assignment = db.get(JadwalAssignment, assignment_id)
    if assignment is None or assignment.sesi_id != sesi_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment dengan id '{assignment_id}' tidak ditemukan dalam sesi ini.",
        )

    db.delete(assignment)
    db.commit()


@router.patch(
    "/{sesi_id}/assignments/{assignment_id}/override-floor",
    response_model=AssignmentResponse,
)
def toggle_override_floor_priority(
    sesi_id: uuid.UUID,
    assignment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(EDITOR_ROLES_JURUSAN)),
):
    """Toggle override_floor_priority pada assignment.

    Akses: EDITOR_ROLES_JURUSAN (admin, sekretaris_jurusan, tendik_jurusan).
    Kembalikan assignment yang diupdate.
    """
    _get_sesi_or_404(db, sesi_id)

    assignment = db.get(JadwalAssignment, assignment_id)
    if assignment is None or assignment.sesi_id != sesi_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment dengan id '{assignment_id}' tidak ditemukan dalam sesi ini.",
        )

    assignment.override_floor_priority = not assignment.override_floor_priority
    db.commit()
    db.refresh(assignment)

    return _build_assignment_response(assignment)


# ---------------------------------------------------------------------------
# Team Teaching endpoints
# ---------------------------------------------------------------------------

def _get_assignment_or_404(db: Session, sesi_id: uuid.UUID, assignment_id: uuid.UUID) -> JadwalAssignment:
    assignment = db.get(JadwalAssignment, assignment_id)
    if assignment is None or assignment.sesi_id != sesi_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment dengan id '{assignment_id}' tidak ditemukan dalam sesi ini.",
        )
    return assignment


def _validate_team_teaching(assignment: JadwalAssignment) -> None:
    """Raise 400 if assignment has no dosen2_id (not a team teaching assignment)."""
    if assignment.dosen2_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignment ini bukan team teaching (dosen2_id kosong)",
        )


def _validate_dosen_own(db: Session, current_user, assignment: JadwalAssignment) -> None:
    """Raise 403 if the authenticated dosen is not dosen1 or dosen2 of the assignment."""
    dosen = db.query(Dosen).filter(Dosen.user_id == current_user.id).first()
    if dosen is None or (dosen.id != assignment.dosen1_id and dosen.id != assignment.dosen2_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Anda bukan dosen pengampu assignment ini.",
        )


@router.get(
    "/{sesi_id}/assignments/{assignment_id}/team-teaching",
    response_model=TeamTeachingResponse,
)
def get_team_teaching(
    sesi_id: uuid.UUID,
    assignment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Kembalikan daftar TeamTeachingOrder untuk assignment ini.

    Akses: semua role (termasuk dosen).
    Validasi: assignment harus memiliki dosen2_id (team teaching).
    """
    _get_sesi_or_404(db, sesi_id)
    assignment = _get_assignment_or_404(db, sesi_id, assignment_id)
    _validate_team_teaching(assignment)

    orders = (
        db.query(TeamTeachingOrder)
        .filter(TeamTeachingOrder.assignment_id == assignment_id)
        .all()
    )
    return TeamTeachingResponse(items=orders)


@router.put(
    "/{sesi_id}/assignments/{assignment_id}/team-teaching",
    response_model=TeamTeachingResponse,
)
def set_team_teaching_order(
    sesi_id: uuid.UUID,
    assignment_id: uuid.UUID,
    body: TeamTeachingSetRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["dosen"])),
):
    """Set urutan masuk kelas pra-UTS untuk team teaching.

    Akses: Dosen own saja (dosen1 atau dosen2 dari assignment).
    Validasi: assignment harus memiliki dosen2_id.
    Upsert TeamTeachingOrder berdasarkan (assignment_id, dosen_id).
    """
    _get_sesi_or_404(db, sesi_id)
    assignment = _get_assignment_or_404(db, sesi_id, assignment_id)
    _validate_team_teaching(assignment)
    _validate_dosen_own(db, current_user, assignment)

    for item in body.orders:
        existing = (
            db.query(TeamTeachingOrder)
            .filter(
                TeamTeachingOrder.assignment_id == assignment_id,
                TeamTeachingOrder.dosen_id == item.dosen_id,
            )
            .first()
        )
        if existing:
            existing.urutan_pra_uts = item.urutan_pra_uts
        else:
            new_order = TeamTeachingOrder(
                assignment_id=assignment_id,
                dosen_id=item.dosen_id,
                urutan_pra_uts=item.urutan_pra_uts,
            )
            db.add(new_order)

    db.commit()

    orders = (
        db.query(TeamTeachingOrder)
        .filter(TeamTeachingOrder.assignment_id == assignment_id)
        .all()
    )
    return TeamTeachingResponse(items=orders)


@router.post(
    "/{sesi_id}/assignments/{assignment_id}/team-teaching/swap",
    response_model=TeamTeachingResponse,
)
def swap_team_teaching_order(
    sesi_id: uuid.UUID,
    assignment_id: uuid.UUID,
    body: TeamTeachingSwapRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["dosen"])),
):
    """Jadwalkan pertukaran pasca-UTS untuk team teaching.

    Akses: Dosen own saja (dosen1 atau dosen2 dari assignment).
    Validasi: assignment harus memiliki dosen2_id.
    Upsert TeamTeachingOrder — update urutan_pasca_uts.
    """
    _get_sesi_or_404(db, sesi_id)
    assignment = _get_assignment_or_404(db, sesi_id, assignment_id)
    _validate_team_teaching(assignment)
    _validate_dosen_own(db, current_user, assignment)

    for item in body.orders:
        existing = (
            db.query(TeamTeachingOrder)
            .filter(
                TeamTeachingOrder.assignment_id == assignment_id,
                TeamTeachingOrder.dosen_id == item.dosen_id,
            )
            .first()
        )
        if existing:
            existing.urutan_pasca_uts = item.urutan_pasca_uts
        else:
            # Create with a placeholder urutan_pra_uts=0 if no prior record exists
            new_order = TeamTeachingOrder(
                assignment_id=assignment_id,
                dosen_id=item.dosen_id,
                urutan_pra_uts=0,
                urutan_pasca_uts=item.urutan_pasca_uts,
            )
            db.add(new_order)

    db.commit()

    orders = (
        db.query(TeamTeachingOrder)
        .filter(TeamTeachingOrder.assignment_id == assignment_id)
        .all()
    )
    return TeamTeachingResponse(items=orders)
