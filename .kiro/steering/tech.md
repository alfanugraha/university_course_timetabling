---
inclusion: always
---

# Technology Stack — Sistem Penjadwalan Kuliah (CTS)

## Stack Utama

| Layer | Teknologi | Versi Minimum |
|-------|-----------|---------------|
| Backend API | Python + FastAPI | Python 3.11, FastAPI 0.110 |
| ORM | SQLAlchemy | 2.0 |
| Database Migration | Alembic | 1.13 |
| Database | PostgreSQL | 15 |
| Frontend | React + TypeScript | React 18, Node 20 |
| UI Components | Tailwind CSS + shadcn/ui | Tailwind 3 |
| State Management | Zustand | latest |
| Data Fetching | TanStack Query (@tanstack/react-query) | v5 |
| HTTP Client | Axios | latest |
| Routing | React Router DOM | v6 |
| Build Tool | Vite | latest |
| Excel I/O | openpyxl + pandas | openpyxl 3.1 |
| Auth | JWT (stateless) + bcrypt (passlib) | — |
| Containerization | Docker + Docker Compose | Docker 24 |
| Reverse Proxy | Nginx | latest stable |

## Backend — Konvensi Penting

### Struktur Aplikasi
```
backend/app/
├── main.py          # FastAPI app, include semua router
├── config.py        # Settings via pydantic-settings, baca dari .env
├── database.py      # SQLAlchemy engine, SessionLocal, get_db dependency
├── models/          # SQLAlchemy ORM models (satu file per entitas)
├── schemas/         # Pydantic v2 schemas (request/response)
├── routers/         # FastAPI APIRouter (satu file per domain)
├── services/        # Business logic (conflict_engine, excel_importer, excel_exporter)
└── core/
    ├── auth.py      # JWT: create_token, verify_token, get_current_user
    ├── security.py  # bcrypt hashing
    └── permissions.py  # RBAC: require_role(), EDITOR_ROLES constant
```

### RBAC Pattern
Gunakan konstanta RBAC yang sudah didefinisikan, jangan hardcode string role:
```python
EDITOR_ROLES_JURUSAN = ["admin", "sekretaris_jurusan", "tendik_jurusan"]
EDITOR_ROLES_PRODI   = ["admin", "sekretaris_jurusan", "tendik_jurusan",
                         "koordinator_prodi", "tendik_prodi"]
VIEWER_ROLES         = ["ketua_jurusan"]
```
Gunakan `require_role(EDITOR_ROLES_JURUSAN)` atau `require_role(EDITOR_ROLES_PRODI)` di router sesuai cakupan endpoint.

### Database
- Semua PK menggunakan **UUID v4** — bukan integer autoincrement
- Gunakan **soft delete** via kolom `is_active: bool` untuk entitas master (dosen, MK, ruang)
- Kolom `ruang_id` pada `jadwal_assignment` bersifat **NULLABLE** — jangan validasi wajib
- Kolom `dosen2_id` pada `jadwal_assignment` bersifat **NULLABLE** — team teaching opsional
- PostgreSQL-specific types yang digunakan: `UUID[]` (array) untuk `conflict_log.assignment_ids`, `JSONB` untuk `conflict_log.detail`

### Timeslot
15 timeslot tetap di-seed saat init, **tidak boleh ditambah via import Excel**:
- Kode format: `mon_s1`, `mon_s2`, `mon_s3`, `tue_s1`, ..., `fri_s3`
- 3 sesi per hari: Sesi 1 (07:30–10:00), Sesi 2 (10:00–12:30), Sesi 3 (13:00–15:30)
- Semua slot = 3 SKS

### ETL / Import Excel
Strategi **tolerant import** — jangan batalkan seluruh import karena satu baris gagal:
```python
for row in sheet.iter_rows():
    try:
        # proses baris
    except Exception as e:
        warnings.append(ImportWarning(row=row_num, reason=str(e)))
        continue
```
Selalu gunakan `normalize_str()` untuk lookup nama/kode dari Excel (strip + lowercase).
Gunakan `resolve_dosen(nama_or_kode, session)` yang mengembalikan `None` (bukan raise) jika tidak ditemukan.

### Conflict Engine
Engine di `services/conflict_engine.py` adalah **Python murni** — tidak ada ML, tidak ada external solver.
Setiap rule adalah method terpisah yang mengembalikan `list[ConflictResult]`.
Severity: `ERROR` untuk Hard Constraints, `WARNING` untuk Soft Constraints.
HC-03 dan HC-04 **DEFERRED** — jangan implementasikan di Fase 1.

## Frontend — Konvensi Penting

### Struktur
```
frontend/src/
├── pages/       # Halaman per route
├── components/  # Shared components (DataTable, FormModal, dll)
├── hooks/       # Custom React hooks
├── api/         # Axios instance + API functions per domain
└── store/       # Zustand stores (authStore, dll)
```

### Auth Flow
- Token JWT disimpan di Zustand `authStore`
- Axios interceptor inject `Authorization: Bearer <token>` di setiap request
- Jika response 401 → redirect ke `/login`
- Route guard `<PrivateRoute>` dan `<RoleGuard role={...}>` untuk proteksi halaman

### Indikator Konflik di Tabel
- Baris dengan konflik `ERROR` → background merah muda
- Baris dengan konflik `WARNING` → background kuning
- Ikon konflik clickable → buka detail pesan

### Komponen Shared Wajib
Selalu gunakan komponen shared berikut, jangan buat ulang:
- `DataTable` — sortable, paginated
- `FormModal` — modal dengan form
- `ConfirmDialog` — konfirmasi hapus/aksi destruktif
- `Badge` — status sesi, severity konflik

## Docker Compose Services

```
db        → PostgreSQL 15 (port 5432, internal only)
api       → FastAPI/uvicorn (port 8000, internal only)
frontend  → React build served by Nginx (port 3000, internal only)
proxy     → Nginx reverse proxy (port 80, exposed ke intranet)
```

Hanya port **80** yang di-expose ke jaringan intranet kampus.

## Environment Variables

File `.env` (dari `.env.example`):
```
DATABASE_URL=postgresql://user:pass@db:5432/cts
SECRET_KEY=<random-secret>
CORS_ORIGINS=http://localhost,http://proxy
```

## Testing

- Backend: `pytest` + `httpx` (async test client)
- Test DB: PostgreSQL test database atau SQLite in-memory untuk unit tests
- Jalankan test dengan: `pytest` (bukan watch mode)
- Setiap router handler harus punya minimal 1 happy path + 1 error path test
