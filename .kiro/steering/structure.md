---
inclusion: always
---

# Project Structure — Sistem Penjadwalan Kuliah (CTS)

## Root Layout

```
university_course_timetabling/
├── .kiro/
│   ├── specs/timetabling/       # Spec files (requirements, design, tasks)
│   └── steering/                # Steering files (product, tech, structure)
├── backend/                     # FastAPI application
├── frontend/                    # React + TypeScript application
├── nginx/                       # Nginx reverse proxy config
├── data_dukung_aktualisasi/     # Data Excel sumber (read-only reference)
├── docker-compose.yml           # Production compose
├── docker-compose.override.yml  # Development overrides (hot reload)
└── .env.example                 # Environment variable template
```

## Backend Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app entry point, include semua router
│   ├── config.py                # Settings (pydantic-settings, baca .env)
│   ├── database.py              # SQLAlchemy engine, SessionLocal, get_db()
│   │
│   ├── models/                  # SQLAlchemy ORM models — satu file per entitas
│   │   ├── user.py              # User (5 role: admin, sekretaris_jurusan, koordinator_prodi, kaprodi, dosen)
│   │   ├── prodi.py
│   │   ├── kurikulum.py
│   │   ├── mata_kuliah.py       # MataKuliah + MataKuliahKelas
│   │   ├── dosen.py             # Dosen + DosenUnavailability + DosenPreference
│   │   ├── ruang.py
│   │   ├── timeslot.py          # 15 slot tetap (seed data)
│   │   ├── sesi_jadwal.py
│   │   ├── jadwal_assignment.py # JadwalAssignment + TeamTeachingOrder
│   │   └── conflict_log.py
│   │
│   ├── schemas/                 # Pydantic v2 schemas — satu file per domain
│   │   ├── auth.py
│   │   ├── prodi.py
│   │   ├── kurikulum.py
│   │   ├── mata_kuliah.py
│   │   ├── dosen.py
│   │   ├── ruang.py
│   │   ├── timeslot.py
│   │   ├── sesi_jadwal.py
│   │   ├── assignment.py
│   │   ├── conflict.py
│   │   └── report.py
│   │
│   ├── routers/                 # FastAPI APIRouter — satu file per domain
│   │   ├── auth.py              # POST /auth/login, GET /auth/me
│   │   ├── prodi.py
│   │   ├── kurikulum.py
│   │   ├── mata_kuliah.py
│   │   ├── dosen.py             # CRUD dosen + unavailability + preferences
│   │   ├── ruang.py
│   │   ├── timeslot.py
│   │   ├── sesi.py              # CRUD sesi jadwal
│   │   ├── assignment.py        # CRUD assignment + team teaching endpoints
│   │   ├── conflict.py          # check-conflicts, list conflicts, resolve
│   │   ├── report.py            # sks-rekap, room-map, preferences-summary
│   │   └── import_export.py     # POST /import/master, POST /import/jadwal, GET /export
│   │
│   ├── services/                # Business logic layer
│   │   ├── conflict_engine.py   # ConflictEngine class + semua rule methods
│   │   ├── excel_importer.py    # ExcelImporter: import_master_db, import_jadwal
│   │   └── excel_exporter.py    # ExcelExporter: export_jadwal
│   │
│   └── core/
│       ├── auth.py              # JWT: create_token, verify_token, get_current_user
│       ├── security.py          # bcrypt: hash_password, verify_password
│       └── permissions.py       # RBAC: require_role(), EDITOR_ROLES
│
├── alembic/                     # Database migrations
│   ├── env.py                   # Baca DATABASE_URL dari environment
│   └── versions/                # Migration files
│
├── tests/
│   ├── conftest.py              # Fixtures: test DB, test client, seed data
│   ├── test_auth.py
│   ├── test_master.py
│   ├── test_assignment.py
│   ├── test_conflict_engine.py  # Unit tests per HC/SC rule
│   ├── test_import.py
│   └── test_export.py
│
├── scripts/
│   └── seed.py                  # Seed 15 timeslot tetap + user admin default
│
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Frontend Structure

```
frontend/
├── src/
│   ├── main.tsx                 # React entry point
│   ├── App.tsx                  # Router setup
│   │
│   ├── pages/                   # Satu file per halaman/route
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── master/
│   │   │   ├── DosenPage.tsx
│   │   │   ├── MataKuliahPage.tsx
│   │   │   ├── RuangPage.tsx
│   │   │   ├── TimeslotPage.tsx
│   │   │   └── ProdiPage.tsx
│   │   ├── jadwal/
│   │   │   ├── SesiListPage.tsx
│   │   │   ├── SesiDetailPage.tsx
│   │   │   ├── TeamTeachingPage.tsx
│   │   │   └── KonflikPage.tsx
│   │   ├── laporan/
│   │   │   ├── SksRekapPage.tsx
│   │   │   ├── RoomMapPage.tsx
│   │   │   └── PreferensiSummaryPage.tsx
│   │   ├── dosen/
│   │   │   ├── JadwalSayaPage.tsx
│   │   │   └── PreferensiPage.tsx
│   │   └── admin/
│   │       └── ImportPage.tsx
│   │
│   ├── components/              # Shared reusable components
│   │   ├── DataTable.tsx        # Sortable, paginated table
│   │   ├── FormModal.tsx        # Modal wrapper dengan form
│   │   ├── ConfirmDialog.tsx    # Konfirmasi aksi destruktif
│   │   ├── Badge.tsx            # Status badge (severity, sesi status)
│   │   ├── Layout.tsx           # Sidebar + header + breadcrumb
│   │   ├── PrivateRoute.tsx     # Auth guard
│   │   └── RoleGuard.tsx        # Role-based access guard
│   │
│   ├── hooks/                   # Custom React hooks
│   │   ├── useAuth.ts
│   │   └── useConflicts.ts
│   │
│   ├── api/                     # Axios instance + API functions
│   │   ├── client.ts            # Axios instance + JWT interceptor + 401 handler
│   │   ├── auth.ts
│   │   ├── dosen.ts
│   │   ├── mataKuliah.ts
│   │   ├── sesi.ts
│   │   ├── assignment.ts
│   │   ├── conflict.ts
│   │   ├── report.ts
│   │   └── importExport.ts
│   │
│   └── store/                   # Zustand stores
│       └── authStore.ts         # user, token, role, login(), logout()
│
├── public/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── Dockerfile
```

## Nginx

```
nginx/
└── nginx.conf    # Reverse proxy: / → frontend:3000, /api → api:8000
```

## Data Sumber (Read-Only)

```
data_dukung_aktualisasi/
├── db.xlsx                          # Master: prodi, dosen, ruang, kurikulum, MK
├── db_mata_kuliah.xlsx              # Kelas paralel MK
├── Bahan untuk buku panduan/
│   ├── Buku Panduan.docx
│   └── Templat Jadwal Kuliah.xlsx
└── Jadwal Kuliah Semester Sebelumnya/
    ├── 20240225_Jadwal Kuliah S1 Matematika Genap 2023-2024 ok.xlsx
    ├── 20240912_Jadwal Kuliah Jurusan Matematika Ganjil 2024 2025.xlsx
    ├── 9_20250212_Jadwal Kuliah S1 MATEMATIKA Genap 2024 2025.xlsx
    ├── ED-8_Jadwal Kuliah Jurusan Matematika_Genap 2025-2026 v3.xlsx
    └── ED7_20250814_Jadwal Kuliah Jurusan Matematika_Ganjil 2025-2026.xlsx
```

File-file ini adalah **referensi sumber data** untuk import awal. Jangan modifikasi.

## Konvensi Penamaan

| Konteks | Konvensi | Contoh |
|---------|----------|--------|
| Python files | snake_case | `conflict_engine.py` |
| Python classes | PascalCase | `ConflictEngine`, `JadwalAssignment` |
| Python functions/vars | snake_case | `check_lecturer_double()` |
| TypeScript files | PascalCase (components), camelCase (utils) | `DataTable.tsx`, `authStore.ts` |
| TypeScript components | PascalCase | `DataTable`, `FormModal` |
| API routes | kebab-case | `/mata-kuliah`, `/check-conflicts` |
| DB tables | snake_case | `jadwal_assignment`, `dosen_preference` |
| DB columns | snake_case | `dosen1_id`, `is_violated` |
| Timeslot codes | `{day_abbr}_s{n}` | `mon_s1`, `fri_s3` |

## Aturan Penting

1. **Jangan buat file di luar struktur di atas** tanpa alasan yang jelas.
2. **Satu router = satu domain** — jangan campur endpoint dosen dengan assignment dalam satu file.
3. **Service layer wajib** untuk logic yang lebih dari sekedar DB query — jangan taruh business logic di router.
4. **Conflict engine adalah Python murni** — tidak ada HTTP call, tidak ada ML library.
5. **Timeslot tidak boleh di-import dari Excel** — selalu dari seed data programatik.
6. **UUID untuk semua PK** — jangan gunakan integer sequence.
7. **Tolerant import** — satu baris gagal tidak boleh membatalkan seluruh import.
