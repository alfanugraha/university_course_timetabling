"""initial_schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- prodi ---
    op.create_table(
        "prodi",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("kode", sa.String(10), nullable=False),
        sa.Column("strata", sa.String(5), nullable=False),
        sa.Column("nama", sa.String(100), nullable=False),
        sa.Column("singkat", sa.String(20), nullable=False),
        sa.Column("kategori", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("kode", name="uq_prodi_kode"),
    )

    # --- kurikulum ---
    op.create_table(
        "kurikulum",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("kode", sa.String(20), nullable=False),
        sa.Column("tahun", sa.String(4), nullable=False),
        sa.Column("prodi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["prodi_id"], ["prodi.id"]),
        sa.UniqueConstraint("kode", name="uq_kurikulum_kode"),
    )

    # --- mata_kuliah ---
    op.create_table(
        "mata_kuliah",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("kode", sa.String(20), nullable=False),
        sa.Column("kurikulum_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nama", sa.String(200), nullable=False),
        sa.Column("sks", sa.SmallInteger(), nullable=False),
        sa.Column("semester", sa.SmallInteger(), nullable=False),
        sa.Column("jenis", sa.String(10), nullable=False),
        sa.Column("prasyarat", sa.String(200), nullable=True),
        sa.ForeignKeyConstraint(["kurikulum_id"], ["kurikulum.id"]),
        sa.UniqueConstraint("kode", "kurikulum_id", name="uq_mata_kuliah_kode_kurikulum"),
    )

    # --- mata_kuliah_kelas ---
    op.create_table(
        "mata_kuliah_kelas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("mata_kuliah_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kelas", sa.String(5), nullable=True),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("ket", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["mata_kuliah_id"], ["mata_kuliah.id"]),
        sa.UniqueConstraint("mata_kuliah_id", "kelas", name="uq_mk_kelas"),
    )

    # --- ruang ---
    op.create_table(
        "ruang",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("nama", sa.String(20), nullable=False),
        sa.Column("kapasitas", sa.SmallInteger(), nullable=False, server_default=sa.text("45")),
        sa.Column("lantai", sa.SmallInteger(), nullable=True),
        sa.Column("gedung", sa.String(100), nullable=True),
        sa.Column("jenis", sa.String(20), nullable=False, server_default=sa.text("'Kelas'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("nama", name="uq_ruang_nama"),
    )

    # --- timeslot ---
    op.create_table(
        "timeslot",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("kode", sa.String(20), nullable=False),
        sa.Column("hari", sa.String(10), nullable=False),
        sa.Column("sesi", sa.SmallInteger(), nullable=False),
        sa.Column("jam_mulai", sa.Time(), nullable=False),
        sa.Column("jam_selesai", sa.Time(), nullable=False),
        sa.Column("label", sa.String(30), nullable=False),
        sa.Column("sks", sa.SmallInteger(), nullable=False),
        sa.UniqueConstraint("kode", name="uq_timeslot_kode"),
    )

    # --- user (store role as VARCHAR to avoid enum DDL issues) ---
    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(100), nullable=True),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("prodi_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["prodi_id"], ["prodi.id"]),
        sa.UniqueConstraint("username", name="uq_user_username"),
        sa.UniqueConstraint("email", name="uq_user_email"),
    )

    # --- dosen ---
    op.create_table(
        "dosen",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("nidn", sa.String(20), nullable=True),
        sa.Column("nip", sa.String(25), nullable=True),
        sa.Column("kode", sa.String(10), nullable=False),
        sa.Column("nama", sa.String(200), nullable=False),
        sa.Column("jabfung", sa.String(50), nullable=True),
        sa.Column("kjfd", sa.String(100), nullable=True),
        sa.Column("homebase_prodi_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bkd_limit_sks", sa.SmallInteger(), nullable=True),
        sa.Column("tgl_lahir", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'Aktif'")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["homebase_prodi_id"], ["prodi.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.UniqueConstraint("nidn", name="uq_dosen_nidn"),
        sa.UniqueConstraint("nip", name="uq_dosen_nip"),
        sa.UniqueConstraint("kode", name="uq_dosen_kode"),
    )

    # --- sesi_jadwal ---
    op.create_table(
        "sesi_jadwal",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("nama", sa.String(100), nullable=False),
        sa.Column("semester", sa.String(10), nullable=False),
        sa.Column("tahun_akademik", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'Draft'")),
        sa.UniqueConstraint("semester", "tahun_akademik", name="uq_sesi_semester_tahun"),
    )

    # --- dosen_unavailability ---
    op.create_table(
        "dosen_unavailability",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("dosen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeslot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sesi_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("catatan", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["dosen_id"], ["dosen.id"]),
        sa.ForeignKeyConstraint(["timeslot_id"], ["timeslot.id"]),
        sa.ForeignKeyConstraint(["sesi_id"], ["sesi_jadwal.id"]),
        sa.UniqueConstraint("dosen_id", "timeslot_id", "sesi_id", name="uq_dosen_unavail"),
    )

    # --- dosen_preference ---
    op.create_table(
        "dosen_preference",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("dosen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sesi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeslot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fase", sa.String(15), nullable=False),
        sa.Column("catatan", sa.Text(), nullable=True),
        sa.Column("is_violated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["dosen_id"], ["dosen.id"]),
        sa.ForeignKeyConstraint(["sesi_id"], ["sesi_jadwal.id"]),
        sa.ForeignKeyConstraint(["timeslot_id"], ["timeslot.id"]),
        sa.UniqueConstraint("dosen_id", "sesi_id", "timeslot_id", "fase", name="uq_dosen_preference"),
    )

    # --- jadwal_assignment ---
    op.create_table(
        "jadwal_assignment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sesi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mk_kelas_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dosen1_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dosen2_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeslot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ruang_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("override_floor_priority", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("catatan", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["sesi_id"], ["sesi_jadwal.id"]),
        sa.ForeignKeyConstraint(["mk_kelas_id"], ["mata_kuliah_kelas.id"]),
        sa.ForeignKeyConstraint(["dosen1_id"], ["dosen.id"]),
        sa.ForeignKeyConstraint(["dosen2_id"], ["dosen.id"]),
        sa.ForeignKeyConstraint(["timeslot_id"], ["timeslot.id"]),
        sa.ForeignKeyConstraint(["ruang_id"], ["ruang.id"]),
        sa.UniqueConstraint("sesi_id", "mk_kelas_id", name="uq_assignment_sesi_mk_kelas"),
    )
    op.create_index("idx_assignment_dosen1", "jadwal_assignment", ["sesi_id", "dosen1_id", "timeslot_id"])
    op.create_index("idx_assignment_dosen2", "jadwal_assignment", ["sesi_id", "dosen2_id", "timeslot_id"])
    op.create_index("idx_assignment_ruang", "jadwal_assignment", ["sesi_id", "ruang_id", "timeslot_id"])

    # --- team_teaching_order ---
    op.create_table(
        "team_teaching_order",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dosen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("urutan_pra_uts", sa.SmallInteger(), nullable=False),
        sa.Column("urutan_pasca_uts", sa.SmallInteger(), nullable=True),
        sa.Column("catatan", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["jadwal_assignment.id"]),
        sa.ForeignKeyConstraint(["dosen_id"], ["dosen.id"]),
        sa.UniqueConstraint("assignment_id", "dosen_id", name="uq_team_teaching_order"),
    )

    # --- conflict_log ---
    op.create_table(
        "conflict_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sesi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jenis", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("assignment_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("pesan", sa.Text(), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["sesi_id"], ["sesi_jadwal.id"]),
    )


def downgrade() -> None:
    op.drop_table("conflict_log")
    op.drop_table("team_teaching_order")
    op.drop_index("idx_assignment_ruang", table_name="jadwal_assignment")
    op.drop_index("idx_assignment_dosen2", table_name="jadwal_assignment")
    op.drop_index("idx_assignment_dosen1", table_name="jadwal_assignment")
    op.drop_table("jadwal_assignment")
    op.drop_table("dosen_preference")
    op.drop_table("dosen_unavailability")
    op.drop_table("sesi_jadwal")
    op.drop_table("dosen")
    op.drop_table("user")
    op.drop_table("timeslot")
    op.drop_table("ruang")
    op.drop_table("mata_kuliah_kelas")
    op.drop_table("mata_kuliah")
    op.drop_table("kurikulum")
    op.drop_table("prodi")
