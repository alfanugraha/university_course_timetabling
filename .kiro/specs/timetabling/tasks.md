# Tasks — Sistem Penjadwalan Kuliah
## Jurusan Matematika FMIPA Universitas Riau

**Versi:** 1.6.0  
**Tanggal:** April 2026  
**Metodologi:** Spec-Driven Development  
**Status:** Ready to Implement  
**Changelog v1.6.0:** Tambah T4.1.13 — implementasi `check_floor_priority()` SC-05; tambah T4.3.10 — unit test SC-05; tambah field `override_floor_priority` ke model JadwalAssignment (T1.2.11); update T1.3.1 migrasi.  
**Changelog v1.5.0:** Restrukturisasi role — `kaprodi` → `ketua_jurusan`; tambah `tendik_prodi` dan `tendik_jurusan`; update model User (7 role); update RBAC constants; tambah endpoint approve/publish sesi.  
**Changelog v1.4.0:** HC-04 dikembalikan ke DEFERRED; T4.1.5b dan T4.3.3b dibatalkan; kolom model Dosen dikembalikan ke `bkd_limit_sks` (NULLABLE, placeholder).  
**Changelog v1.3.0:** Revisi akses endpoint team teaching — PUT/POST dipindahkan ke Dosen (own), GET tetap untuk semua role termasuk EDITOR_ROLES; revisi T4.1.5 — aktifkan `check_bkd_minimum()` sebagai WARNING (bukan deferred); ganti `bkd_limit_sks` → `bkd_min_sks` di model Dosen; tambah unit test HC-04; update T7.4.6 dan T7.7 untuk halaman team teaching dosen; update kapasitas default ruang 45.  
**Changelog v1.2.0:** Tambah task role baru (`sekretaris_jurusan`, `koordinator_prodi`) ke model User dan RBAC; tambah task model `DosenPreference` dan `TeamTeachingOrder`; tambah task endpoint preferensi dosen (pre-schedule/post-draft) dan team teaching scheduling; tambah task SC-03 ke conflict engine; update test role isolation.  
**Changelog v1.1.0:** Tambah task HC-07/08/09; defer task BKD (T4.1.5); update seed timeslot ke 15 slot tetap; tambah task data cleaning ETL; revisi test fixtures.

---

## Konvensi Status

| Simbol | Status |
|--------|--------|
| `[ ]` | Pending |
| `[~]` | In Progress |
| `[x]` | Completed |
| `[-]` | Skipped / Tidak berlaku |

---

## Fase 0 — Project Setup

**Tujuan:** Menyiapkan lingkungan pengembangan dan struktur proyek agar semua fase berikutnya dapat berjalan.

### 0.1 Struktur Proyek & Tooling

- [ ] **T0.1.1** — Inisialisasi struktur direktori sesuai `design.md §6` (`backend/`, `frontend/`, `nginx/`)
- [ ] **T0.1.2** — Inisialisasi Git repository dan buat `.gitignore` untuk Python, Node, Docker
- [ ] **T0.1.3** — Buat `docker-compose.yml` dengan service: `db` (PostgreSQL 15), `api` (FastAPI), `frontend` (React/Nginx), `proxy` (Nginx)
- [ ] **T0.1.4** — Buat `backend/requirements.txt` dengan dependensi: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `pydantic`, `python-jose`, `passlib[bcrypt]`, `openpyxl`, `pandas`, `pytest`, `httpx`
- [ ] **T0.1.5** — Inisialisasi project React + TypeScript dengan Vite; install `tailwindcss`, `shadcn/ui`, `axios`, `zustand`, `react-router-dom`, `@tanstack/react-query`
- [ ] **T0.1.6** — Konfigurasi environment variables: buat `.env.example` untuk `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`
- [ ] **T0.1.7** — Verifikasi: jalankan `docker compose up` dan pastikan semua service healthy

---

## Fase 1 — Database & Model

**Tujuan:** Membangun lapisan data yang menjadi fondasi seluruh sistem.

### 1.1 Setup Database

- [ ] **T1.1.1** — Setup SQLAlchemy engine dan session factory di `backend/app/database.py`
- [ ] **T1.1.2** — Inisialisasi Alembic (`alembic init`); konfigurasi `alembic/env.py` agar membaca `DATABASE_URL` dari environment
- [ ] **T1.1.3** — Buat base model SQLAlchemy dengan kolom `id` (UUID), `created_at`, `updated_at` sebagai mixin

### 1.2 ORM Models

Buat satu file per model sesuai `design.md §2.2`. Setiap task mencakup model + index + relasi.

- [ ] **T1.2.1** — Model `User` (`backend/app/models/user.py`) — enum role: `admin`, `ketua_jurusan`, `sekretaris_jurusan`, `koordinator_prodi`, `dosen`, `tendik_prodi`, `tendik_jurusan`; kolom `prodi_id` NULLABLE (untuk `koordinator_prodi` dan `tendik_prodi`)
- [ ] **T1.2.2** — Model `Prodi` (`backend/app/models/prodi.py`)
- [ ] **T1.2.3** — Model `Kurikulum` dengan relasi FK ke `Prodi`
- [ ] **T1.2.4** — Model `MataKuliah` dengan relasi FK ke `Kurikulum`
- [ ] **T1.2.5** — Model `MataKuliahKelas` dengan relasi FK ke `MataKuliah`
- [ ] **T1.2.6** — Model `Ruang`
- [ ] **T1.2.7** — Model `Timeslot`
- [ ] **T1.2.8** — Model `Dosen` dengan relasi FK ke `Prodi` (homebase) dan `User`; kolom `bkd_limit_sks` (SMALLINT, NULLABLE) sebagai placeholder untuk fase berikutnya — tidak divalidasi di Fase 1
- [ ] **T1.2.9** — Model `DosenUnavailability` dengan relasi FK ke `Dosen` dan `Timeslot`
- [ ] **T1.2.9b** — Model `DosenPreference` dengan kolom `fase` (`pre_schedule`/`post_draft`), `is_violated`, relasi FK ke `Dosen`, `Timeslot`, `SesiJadwal`
- [ ] **T1.2.9c** — Model `TeamTeachingOrder` dengan kolom `urutan_pra_uts`, `urutan_pasca_uts`, relasi FK ke `JadwalAssignment` dan `Dosen`
- [ ] **T1.2.10** — Model `SesiJadwal`
- [ ] **T1.2.11** — Model `JadwalAssignment` dengan relasi FK ke `SesiJadwal`, `MataKuliahKelas`, `Dosen` (x2), `Timeslot`, `Ruang`; tambahkan field `override_floor_priority` (BOOLEAN, DEFAULT FALSE); tambahkan index untuk conflict detection query
- [ ] **T1.2.12** — Model `ConflictLog` dengan kolom `assignment_ids` (PostgreSQL Array) dan `detail` (JSONB)

### 1.3 Migrasi Database

- [ ] **T1.3.1** — Generate migrasi Alembic awal: `alembic revision --autogenerate -m "initial_schema"` (mencakup semua model termasuk `dosen_preference` dan `team_teaching_order`)
- [ ] **T1.3.2** — Jalankan migrasi: `alembic upgrade head`
- [ ] **T1.3.3** — Verifikasi skema di PostgreSQL menggunakan `psql` atau GUI (DBeaver/pgAdmin)
- [ ] **T1.3.4** — Buat script seed data dasar: **15 timeslot tetap** (3 sesi × 5 hari: Senin–Jumat, sesi 07:30–10:00 / 10:00–12:30 / 13:00–15:30, masing-masing 3 SKS; kode: `mon_s1`…`fri_s3`), user admin default

---

## Fase 2 — Backend API: Autentikasi & Data Master

**Tujuan:** Membangun endpoint CRUD untuk semua entitas master dan sistem autentikasi.

### 2.1 Autentikasi

- [ ] **T2.1.1** — Implementasi JWT utility di `backend/app/core/auth.py`: `create_token`, `verify_token`, `get_current_user`
- [ ] **T2.1.2** — Implementasi password hashing dengan bcrypt di `core/security.py`
- [ ] **T2.1.3** — Implementasi RBAC helper di `core/permissions.py`: decorator/dependency `require_role(roles: list)`; definisikan konstanta:
  - `EDITOR_ROLES_JURUSAN = [admin, sekretaris_jurusan, tendik_jurusan]`
  - `EDITOR_ROLES_PRODI = [admin, sekretaris_jurusan, tendik_jurusan, koordinator_prodi, tendik_prodi]`
  - `VIEWER_ROLES = [ketua_jurusan]`
- [ ] **T2.1.4** — Router `POST /auth/login` — verifikasi credentials, kembalikan JWT
- [ ] **T2.1.5** — Router `GET /auth/me` — kembalikan profil user aktif
- [ ] **T2.1.6** — Test: login sukses, login gagal, token expired, akses tanpa token

### 2.2 CRUD Data Master

Setiap task di bawah mencakup: Pydantic schema (request/response), router handler, service layer, dan unit test.

- [ ] **T2.2.1** — CRUD `Prodi`: `GET /prodi`, `POST /prodi`, `PUT /prodi/{id}`
- [ ] **T2.2.2** — CRUD `Kurikulum`: `GET /kurikulum`, `POST /kurikulum`, `PUT /kurikulum/{id}`
- [ ] **T2.2.3** — CRUD `MataKuliah`: `GET /mata-kuliah` (dengan filter prodi/kurikulum/semester), `POST`, `PUT`, `DELETE`
- [ ] **T2.2.4** — CRUD `MataKuliahKelas`: `GET /mata-kuliah/{id}/kelas`, `POST`, `PUT`, `DELETE`
- [ ] **T2.2.5** — CRUD `Ruang`: `GET /ruang`, `POST`, `PUT`
- [ ] **T2.2.6** — CRUD `Timeslot`: `GET /timeslot`, `POST`, `PUT`
- [ ] **T2.2.7** — CRUD `Dosen`: `GET /dosen`, `POST`, `PUT` (termasuk filter homebase, status)
- [ ] **T2.2.8** — Endpoint `POST /dosen/{id}/unavailability` dan `GET /dosen/{id}/unavailability`
- [ ] **T2.2.8b** — Endpoint preferensi dosen: `GET /dosen/{id}/preferences`, `POST /dosen/{id}/preferences` (dengan field `fase`: `pre_schedule`/`post_draft`), `PUT /dosen/{id}/preferences/{pid}`, `DELETE /dosen/{id}/preferences/{pid}`; validasi bahwa dosen hanya dapat mengelola preferensi dirinya sendiri
- [ ] **T2.2.9** — CRUD `User` (admin only): `GET /users`, `POST /users`, `PUT /users/{id}`, `PATCH /users/{id}/reset-password`

---

## Fase 3 — Backend API: Penjadwalan

**Tujuan:** Membangun endpoint untuk manajemen sesi jadwal dan penugasan (assignment).

- [ ] **T3.1** — CRUD `SesiJadwal`: `GET /sesi`, `POST /sesi`, `PUT /sesi/{id}` (transisi status Draft → Aktif → Arsip; akses: `EDITOR_ROLES_JURUSAN`); tambah `PATCH /sesi/{id}/approve` dan `PATCH /sesi/{id}/publish` (akses: `ketua_jurusan`)
- [ ] **T3.2** — `GET /sesi/{id}/assignments` — kembalikan daftar assignment dengan filtering (prodi, hari, semester) dan pagination; filter role: `koordinator_prodi` dan `tendik_prodi` hanya melihat prodi sendiri; `dosen` hanya melihat assignment dirinya; `ketua_jurusan` melihat semua
- [ ] **T3.3** — `POST /sesi/{id}/assignments` — tambah assignment baru; validasi dasar (dosen aktif, timeslot & ruang valid, sesi masih Draft/Aktif); akses: `EDITOR_ROLES_PRODI`
- [ ] **T3.4** — `PUT /sesi/{id}/assignments/{aid}` — update assignment; catat `updated_at`; akses: `EDITOR_ROLES_PRODI`
- [ ] **T3.4b** — `PATCH /sesi/{id}/assignments/{aid}/override-floor` — toggle `override_floor_priority`; akses: `EDITOR_ROLES_JURUSAN`; kembalikan assignment yang diupdate
- [ ] **T3.5** — `DELETE /sesi/{id}/assignments/{aid}` — hapus assignment (hard delete); akses: `EDITOR_ROLES_JURUSAN`
- [ ] **T3.7** — Endpoint team teaching: `GET /sesi/{id}/assignments/{aid}/team-teaching` (akses: semua role termasuk dosen own), `PUT /sesi/{id}/assignments/{aid}/team-teaching` (set urutan masuk kelas pra-UTS; akses: **Dosen own saja**), `POST /sesi/{id}/assignments/{aid}/team-teaching/swap` (jadwalkan pertukaran pasca-UTS; akses: **Dosen own saja**); validasi bahwa assignment memiliki `dosen2_id` (bukan NULL) dan bahwa dosen yang mengakses adalah dosen1 atau dosen2 dari assignment tersebut
- [ ] **T3.8** — Endpoint `GET /sesi/{id}/preferences-summary` — kembalikan ringkasan pelanggaran preferensi dosen: total preferensi, total dilanggar, breakdown per dosen; akses: `EDITOR_ROLES_JURUSAN`, `ketua_jurusan`
- [ ] **T3.6** — Test: buat assignment valid, buat assignment dengan data tidak lengkap, update, hapus, filter per prodi; test akses `sekretaris_jurusan` dan `tendik_jurusan` dapat edit semua prodi; test akses `koordinator_prodi` dan `tendik_prodi` hanya dapat edit prodi sendiri; test akses `ketua_jurusan` hanya read; test akses `dosen` ditolak untuk edit

---

## Fase 4 — Conflict Detection Engine

**Tujuan:** Implementasi modul deteksi konflik sebagai service Python murni yang dipanggil via API.

### 4.1 Core Engine

- [ ] **T4.1.1** — Buat `ConflictResult` dataclass: `jenis`, `severity`, `assignment_ids`, `pesan`, `detail`
- [ ] **T4.1.2** — Buat `ConflictEngine` class di `backend/app/services/conflict_engine.py` dengan method `run(sesi_id)` yang mengorkestrasikan semua rule
- [ ] **T4.1.3** — Implementasi `check_lecturer_double()` — HC-01: deteksi dosen1 atau dosen2 di timeslot yang sama dalam satu sesi
- [ ] **T4.1.4** — Implementasi `check_room_double()` — HC-02: deteksi ruang yang sama di timeslot yang sama
- [-] **T4.1.5** — ~~Implementasi `check_bkd_limit()` — HC-04~~ **DEFERRED** — Ditunda ke Fase berikutnya. Ketentuan BKD bertingkat (minimum 9 SKS, distribusi berdasarkan masa kerja) belum dapat diimplementasikan karena data masa kerja dosen belum tersedia. Kolom `bkd_limit_sks` tersedia di skema sebagai placeholder.
- [-] **T4.1.5b** — ~~Implementasi `check_bkd_minimum()`~~ **DIBATALKAN** — sesuai revisi v1.4.0; HC-04 kembali ke DEFERRED.
- [ ] **T4.1.6** — Implementasi `check_lecturer_unavail()` — HC-06: deteksi assignment pada slot dosen_unavailability
- [ ] **T4.1.7** — Implementasi `check_parallel_mismatch()` — HC-07: kelompokkan assignment berdasarkan `mata_kuliah_id` induk; ERROR jika kelas paralel dalam satu MK memiliki `timeslot_id` berbeda; pesan harus menyebut kelas mana saja yang bermasalah
- [ ] **T4.1.8** — Implementasi `check_student_daily_load()` — HC-08: untuk setiap (prodi, semester, hari), hitung jumlah MK dan total SKS; ERROR jika jumlah_mk > 2 atau total_sks > 6
- [ ] **T4.1.9** — Implementasi `check_lecturer_daily_load()` — HC-09: untuk setiap (dosen, hari), kumpulkan semua assignment di mana dosen muncul sebagai dosen1 atau dosen2; ERROR jika jumlah_mk > 2 atau total_sks > 6
- [ ] **T4.1.10** — Implementasi `check_student_conflict()` — SC-01: deteksi mata kuliah satu semester satu prodi yang dijadwalkan bersamaan (WARNING; pelengkap informatif dari HC-08)
- [ ] **T4.1.11** — Implementasi `check_workload_equity()` — SC-02: hitung simpangan baku beban SKS per prodi, flag sebagai WARNING jika std dev > threshold (konfigurasi)
- [ ] **T4.1.12** — Implementasi `check_lecturer_preference()` — SC-03: untuk setiap dosen dalam sesi, bandingkan `dosen_preference` dengan assignment aktual; update `is_violated = TRUE` pada preferensi yang tidak dipenuhi; kembalikan WARNING `LECTURER_PREFERENCE_VIOLATED` per preferensi yang dilanggar; simpan ringkasan `total_violated` ke `conflict_log.detail`
- [ ] **T4.1.13** — Implementasi `check_floor_priority()` — SC-05: untuk setiap timeslot dalam sesi, ambil semua assignment yang memiliki `ruang_id` dan `dosen.tgl_lahir` terisi dan `override_floor_priority = FALSE`; urutkan dosen berdasarkan usia (senior = lebih tua); bandingkan dengan urutan lantai ruang; WARNING `FLOOR_PRIORITY_VIOLATED` jika dosen senior ditempatkan di lantai lebih tinggi dari dosen yang lebih muda; lewati jika `ruang.lantai` NULL

### 4.2 Integrasi API

- [ ] **T4.2.1** — `POST /sesi/{id}/check-conflicts` — jalankan engine, simpan hasil ke `conflict_log`, kembalikan ringkasan (jumlah ERROR, jumlah WARNING)
- [ ] **T4.2.2** — `GET /sesi/{id}/conflicts` — kembalikan daftar konflik dari `conflict_log` terbaru dengan filter jenis/severity
- [ ] **T4.2.3** — `PATCH /sesi/{id}/conflicts/{cid}/resolve` — tandai konflik sebagai resolved

### 4.3 Testing Conflict Engine

- [ ] **T4.3.1** — Unit test HC-01: fixture dua assignment dosen sama & timeslot sama → assert ERROR `LECTURER_DOUBLE`
- [ ] **T4.3.2** — Unit test HC-02: fixture dua assignment ruang sama & timeslot sama (ruang_id tidak NULL) → assert ERROR `ROOM_DOUBLE`; pastikan tidak ERROR jika ruang_id NULL
- [-] **T4.3.3** — ~~Unit test HC-04~~ **DEFERRED** — sesuai T4.1.5
- [-] **T4.3.3b** — ~~Unit test HC-04 minimum~~ **DIBATALKAN** — sesuai revisi v1.4.0
- [ ] **T4.3.4** — Unit test HC-07: fixture tiga kelas paralel (A, B, C) di mana kelas C di slot berbeda → assert ERROR `PARALLEL_MISMATCH`; pastikan tidak ERROR jika semua kelas di slot sama
- [ ] **T4.3.5** — Unit test HC-08: fixture prodi+semester dengan 3 MK di hari yang sama → assert ERROR `STUDENT_DAILY_OVERLOAD`; fixture 2 MK (6 SKS) → assert tidak ERROR
- [ ] **T4.3.6** — Unit test HC-09: fixture dosen dengan 3 MK di hari yang sama → assert ERROR `LECTURER_DAILY_OVERLOAD`; fixture 1 MK sebagai dosen2 + 1 MK sebagai dosen1 di hari sama (total 2) → assert tidak ERROR
- [ ] **T4.3.7** — Unit test SC-01: fixture dua MK semester sama & prodi sama di timeslot sama → assert WARNING `STUDENT_CONFLICT`
- [ ] **T4.3.9** — Unit test SC-03: fixture dosen dengan preferensi hari Senin, assignment dosen di hari Rabu → assert WARNING `LECTURER_PREFERENCE_VIOLATED` dan `is_violated = TRUE`; fixture dosen dengan preferensi hari Senin, assignment di hari Senin → assert tidak ada WARNING SC-03
- [ ] **T4.3.10** — Unit test SC-05: fixture dua assignment di timeslot sama — dosen senior (lahir 1965) di lantai 3, dosen junior (lahir 1985) di lantai 1 → assert WARNING `FLOOR_PRIORITY_VIOLATED`; fixture dosen senior di lantai 1, dosen junior di lantai 3 → assert tidak ada WARNING; fixture assignment dengan `override_floor_priority = TRUE` → assert tidak ada WARNING meskipun urutan lantai terbalik; fixture tanpa `tgl_lahir` atau tanpa `ruang.lantai` → assert tidak ada WARNING
- [ ] **T4.3.8** — Integration test: import jadwal dari fixture Excel (Genap 2025-2026), jalankan `check-conflicts`, verifikasi jenis konflik yang diketahui manual muncul dengan severity yang benar

---

## Fase 5 — Import / Export Excel

**Tujuan:** Membangun pipeline ETL dari format Excel yang sudah ada ke database, dan export kembali ke Excel.

### 5.0 Strategi Data Cleaning (Pra-Import)

> Basis data Excel yang ada saat ini belum dinormalisasi — strukturnya dibangun di sekitar formula XLOOKUP dan validasi manual, bukan relasi antar tabel. Importer harus menerapkan strategi **tolerant import**: setiap baris diproses secara independen dalam blok `try/except`; baris yang gagal dicatat ke `import_warning_log` (in-memory, dikembalikan ke user) tanpa membatalkan seluruh proses import.

- [ ] **T5.0.1** — Buat `ImportResult` dataclass: `total`, `inserted`, `updated`, `skipped`, `warnings: list[ImportWarning]`; setiap `ImportWarning` memuat nomor baris, nama sheet, nilai bermasalah, dan alasan dilewati
- [ ] **T5.0.2** — Buat helper `normalize_str(val)`: strip whitespace, lowercase untuk perbandingan lookup (banyak nilai di Excel memiliki spasi trailing atau kapitalisasi tidak konsisten)
- [ ] **T5.0.3** — Buat helper `resolve_dosen(nama_or_kode, session)`: lookup dosen dari DB berdasarkan nama atau kode; kembalikan `None` (bukan exception) jika tidak ditemukan, dan catat sebagai warning — ini penting karena data dosen Excel belum lengkap

### 5.1 Importer

- [ ] **T5.1.1** — Buat `ExcelImporter` class di `backend/app/services/excel_importer.py`; injeksikan `db_session`; semua method mengembalikan `ImportResult`
- [ ] **T5.1.2** — Implementasi `import_master_db(file)` — baca sheet `db_prodi`, `db_dosen`, `Ruang Kuliah`, `Mata Kuliah`, `Kurikulum` dari `db.xlsx`; upsert berdasarkan kode unik; toleran terhadap kolom kosong (khususnya kolom dosen seperti `nidn`, `nip` yang sering NULL); catat baris bermasalah sebagai warning
- [ ] **T5.1.3** — Implementasi `import_mata_kuliah_kelas(file)` — baca sheet `db_kelas` dari `db_mata_kuliah.xlsx`; buat `MataKuliahKelas` record; lewati baris di mana `kode_mk` tidak ditemukan di tabel `mata_kuliah` (foreign key miss = warning, bukan error)
- [-] **T5.1.4** — ~~Implementasi `import_timeslot(file)`~~ **TIDAK DIPERLUKAN** — Timeslot kini di-seed secara programatik (15 slot tetap, lihat T1.3.4). Sheet `db_timeslot` dari Excel tidak lagi dipakai sebagai sumber timeslot.
- [ ] **T5.1.5** — Implementasi `import_jadwal(file, sesi_id)` — baca sheet jadwal dari file historis; parsing kolom Hari → `timeslot_id` via lookup (`hari` + `sesi` dari label waktu); Kode MK → `mk_kelas_id`; Dosen I/II → `dosen1_id`/`dosen2_id` via `resolve_dosen()`; `ruang_id` = NULL jika kolom Ruang kosong (opsional); buat `JadwalAssignment` record; catat baris gagal sebagai warning
- [ ] **T5.1.6** — Endpoint `POST /import/master` — multipart upload file Excel; jalankan importer; kembalikan `ImportResult` sebagai JSON (berhasil, dilewati, daftar warnings)
- [ ] **T5.1.7** — Endpoint `POST /import/jadwal` — multipart upload + `sesi_id` query param; jalankan importer jadwal; kembalikan `ImportResult`
- [ ] **T5.1.8** — Test: import `db.xlsx` nyata → verifikasi jumlah record prodi, kurikulum, MK di DB; import jadwal `ED-8_...Genap 2025-2026 v3.xlsx` → verifikasi jumlah assignment dan semua baris warning ter-log dengan benar

### 5.2 Exporter

- [ ] **T5.2.1** — Buat `ExcelExporter` class di `backend/app/services/excel_exporter.py`
- [ ] **T5.2.2** — Implementasi `export_jadwal(sesi_id)` — generate `.xlsx` dengan sheet jadwal utama dan sheet rekap beban SKS per dosen; format kolom sesuai template standar jurusan
- [ ] **T5.2.3** — Endpoint `GET /sesi/{id}/export` — generate file dan stream sebagai download
- [ ] **T5.2.4** — Test: export sesi, buka file di Excel/openpyxl, verifikasi data konsisten dengan DB

---

## Fase 6 — Laporan

**Tujuan:** Membangun endpoint reporting yang dibutuhkan Admin dan Kaprodi.

- [ ] **T6.1** — `GET /sesi/{id}/reports/sks-rekap` — rekap total SKS per dosen; breakdown per prodi (S1 MTK, S1 STK, S2 MTK, Layanan); flag dosen yang mendekati atau melebihi BKD limit
- [ ] **T6.2** — `GET /sesi/{id}/reports/room-map` — peta penggunaan ruang: matrix hari × slot × ruang, isi sel = kode MK atau kosong; kembalikan sebagai JSON untuk dirender di frontend
- [ ] **T6.3** — Test: verifikasi kalkulasi SKS dari data fixture; verifikasi room-map mendeteksi sel kosong dan terisi

---

## Fase 7 — Frontend

**Tujuan:** Membangun antarmuka pengguna React yang terhubung ke seluruh API backend.

### 7.1 Setup & Shared Components

- [ ] **T7.1.1** — Setup React Router: definisi route per halaman sesuai `design.md §5.1`
- [ ] **T7.1.2** — Setup Axios instance dengan base URL, JWT interceptor (inject token di header, redirect ke login jika 401)
- [ ] **T7.1.3** — Setup Zustand store: `authStore` (user, token, role)
- [ ] **T7.1.4** — Komponen `Layout` (sidebar, header, breadcrumb)
- [ ] **T7.1.5** — Komponen shared: `DataTable` (sortable, paginated), `FormModal`, `ConfirmDialog`, `Badge` status/severity
- [ ] **T7.1.6** — Route guard `<PrivateRoute>` dan `<RoleGuard>` untuk proteksi halaman berdasarkan role

### 7.2 Halaman Autentikasi

- [ ] **T7.2.1** — Halaman Login (`/login`): form username/password, panggil `POST /auth/login`, simpan token di store
- [ ] **T7.2.2** — Halaman Profil (`/profile`): tampilkan info user, tombol logout

### 7.3 Halaman Data Master

- [ ] **T7.3.1** — Halaman Dosen (`/master/dosen`): DataTable daftar dosen + modal tambah/edit + filter status/homebase
- [ ] **T7.3.2** — Halaman Mata Kuliah (`/master/mata-kuliah`): DataTable + modal + sub-halaman kelas paralel
- [ ] **T7.3.3** — Halaman Ruang (`/master/ruang`): DataTable + modal tambah/edit
- [ ] **T7.3.4** — Halaman Timeslot (`/master/timeslot`): DataTable read-only + modal (admin only)
- [ ] **T7.3.5** — Halaman Prodi & Kurikulum (`/master/prodi`): DataTable + modal

### 7.4 Halaman Penjadwalan

- [ ] **T7.4.1** — Halaman Daftar Sesi (`/sesi`): tabel sesi dengan status, tombol buat sesi baru
- [ ] **T7.4.2** — Halaman Detail Sesi (`/sesi/:id`): tabel assignment lengkap dengan filter (prodi, hari, semester), pagination
- [ ] **T7.4.3** — Form Tambah Assignment: dropdown beruntun (Prodi → Kurikulum → Semester → Kelas MK → Dosen → Timeslot → Ruang)
- [ ] **T7.4.4** — Form Edit Assignment: pre-fill dari data existing
- [ ] **T7.4.5** — Indikator konflik inline di tabel assignment: warna baris merah (ERROR) / kuning (WARNING); tooltip pesan konflik
- [ ] **T7.4.6** — Halaman Team Teaching (`/sesi/:id/team-teaching`): tabel assignment team teaching (dosen2_id tidak NULL); tampilkan status konfigurasi per assignment (sudah diatur / belum); semua role pengelola hanya dapat melihat ringkasan — tombol edit tidak tersedia untuk mereka

### 7.5 Halaman Deteksi Konflik

- [ ] **T7.5.1** — Halaman Konflik (`/sesi/:id/konflik`): tombol "Periksa Konflik", ringkasan (n ERROR, n WARNING), tabel konflik dengan kolom: jenis, severity, pesan, terlibat, status resolved
- [ ] **T7.5.2** — Aksi "Tandai Resolved" per baris konflik (akses: `EDITOR_ROLES_JURUSAN`)
- [ ] **T7.5.3** — Filter konflik berdasarkan jenis dan severity

### 7.6 Halaman Laporan

- [ ] **T7.6.1** — Halaman Rekap SKS (`/laporan/sks`): tabel dosen × kolom beban SKS per prodi + total; visual bar per dosen
- [ ] **T7.6.2** — Halaman Peta Ruang (`/laporan/ruang`): grid hari × timeslot per ruang; sel berisi nama MK atau kosong
- [ ] **T7.6.3** — Halaman Ringkasan Preferensi (`/laporan/preferensi`): tabel per dosen — jumlah preferensi diajukan, jumlah dipenuhi, jumlah dilanggar; filter per fase (pre-schedule/post-draft)

### 7.7 Halaman Ketua Jurusan

- [ ] **T7.7.0** — Halaman Review Jadwal (`/sesi/:id/review`): tampilan read-only jadwal lengkap; ringkasan konflik (jumlah ERROR/WARNING); tombol "Setujui" dan "Minta Revisi"; tombol "Sahkan" (hanya aktif jika status Disetujui)

### 7.8 Halaman Dosen (Role: Dosen)

- [ ] **T7.8.1** — Halaman Jadwal Saya (`/jadwal-saya`): tampilan tabel mingguan jadwal mengajar dosen aktif
- [ ] **T7.8.2** — Halaman Unavailability (`/preferensi`): grid timeslot per hari; toggle slot tidak tersedia; simpan ke `POST /dosen/{id}/unavailability`
- [ ] **T7.8.3** — Halaman Preferensi Hari (`/preferensi/hari`): form pengajuan preferensi hari mengajar; pilih fase (pre-schedule/post-draft), pilih timeslot yang diinginkan, isi catatan; tampilkan status preferensi yang sudah diajukan (dipenuhi/dilanggar)
- [ ] **T7.8.4** — Halaman Team Teaching Dosen (`/team-teaching`): tampilkan daftar MK yang diampu sebagai team teaching; form set urutan masuk kelas pra-UTS per assignment; tombol "Swap Pasca-UTS"; hanya tampil jika dosen memiliki assignment dengan `dosen2_id` tidak NULL

### 7.9 Halaman Import/Export (Admin)

- [ ] **T7.9.1** — Halaman Import (`/import`): upload file Excel untuk data master dan jadwal; tampilkan hasil (berhasil/gagal/dilewati)
- [ ] **T7.9.2** — Tombol Export di halaman Detail Sesi: panggil `GET /sesi/{id}/export`, trigger download file

---

## Fase 8 — Testing & QA

**Tujuan:** Memastikan semua fitur bekerja sesuai acceptance criteria di `requirements.md §5`.

### 8.1 Backend Testing

- [ ] **T8.1.1** — Setup `pytest` + `httpx` + test database (SQLite in-memory atau PostgreSQL test DB)
- [ ] **T8.1.2** — Test autentikasi: login, refresh, akses tanpa token, akses role tidak sesuai
- [ ] **T8.1.3** — Test CRUD data master: validasi input, unique constraint, soft delete
- [ ] **T8.1.4** — Test conflict engine dengan dataset fixture (5 kasus HC, 2 kasus SC)
- [ ] **T8.1.5** — Test import Excel dengan file `db.xlsx` dan jadwal historis nyata
- [ ] **T8.1.6** — Test export Excel dan verifikasi isi file

### 8.2 End-to-End Validation

- [ ] **T8.2.1** — Jalankan full workflow: import `db.xlsx` → import jadwal historis (Genap 2025-2026) → periksa konflik → verifikasi konflik yang dideteksi sesuai yang diketahui manual
- [ ] **T8.2.2** — Validasi seluruh 10 acceptance criteria dari `requirements.md §5`
- [ ] **T8.2.3** — Test role isolation: login sebagai `sekretaris_jurusan` → dapat edit jadwal semua prodi, tidak dapat akses manajemen user; login sebagai `tendik_jurusan` → dapat edit jadwal semua prodi; login sebagai `koordinator_prodi` → hanya dapat edit jadwal prodi sendiri; login sebagai `tendik_prodi` → hanya dapat edit jadwal prodi sendiri; login sebagai `ketua_jurusan` → hanya read + approve/publish; login sebagai `dosen` → hanya data diri sendiri, dapat mengajukan preferensi dan mengatur team teaching untuk MK yang ia ampu; verifikasi dosen tidak dapat mengatur team teaching untuk MK yang bukan miliknya

---

## Fase 9 — Deployment

**Tujuan:** Menyiapkan sistem untuk berjalan di server intranet kampus.

- [ ] **T9.1** — Finalisasi `docker-compose.yml` untuk produksi: volume persisten untuk PostgreSQL, restart policy, healthcheck
- [ ] **T9.2** — Konfigurasi Nginx sebagai reverse proxy untuk frontend dan backend API
- [ ] **T9.3** — Buat script `init.sh` untuk first-run: jalankan migrasi, seed data (timeslot, user admin default)
- [ ] **T9.4** — Buat `docker-compose.override.yml` untuk environment development (hot reload, exposed ports)
- [ ] **T9.5** — Test deployment di mesin bersih dengan `docker compose up --build`
- [ ] **T9.6** — Dokumentasi: cara instalasi, cara backup database PostgreSQL, cara update versi

---

## Ringkasan Fase dan Dependensi

```
Fase 0 (Setup)
    └── Fase 1 (Database)
            └── Fase 2 (API: Auth + Master)
                    └── Fase 3 (API: Jadwal)
                            ├── Fase 4 (Conflict Engine)
                            ├── Fase 5 (Import/Export)
                            └── Fase 6 (Laporan)
                                    └── Fase 7 (Frontend)  ← parallel ok dengan Fase 4–6
                                            └── Fase 8 (Testing)
                                                    └── Fase 9 (Deployment)
```

> **Catatan:** Frontend (Fase 7) dapat dimulai paralel sejak Fase 2 selesai dengan menggunakan mock data. Fase 4–6 tidak saling bergantung dan dapat dikerjakan paralel setelah Fase 3 selesai.

---

## Backlog Fase Berikutnya (Out of Scope Fase 1)

Fitur-fitur berikut dicatat di sini untuk perencanaan fase mendatang:

- **Optimisasi Otomatis:** Implementasi Genetic Algorithm dan CP-SAT solver (Google OR-Tools) untuk generate jadwal optimal secara otomatis
- **Auto-resolve Konflik:** Saran otomatis penyelesaian konflik (swap slot, ganti dosen) — saat ini hanya notifikasi manual
- **Notifikasi Email/Push:** Notifikasi ke dosen saat jadwal mereka berubah atau preferensi mereka dilanggar
- **Integrasi SIAKAD:** Sinkronisasi data mahasiswa dan mata kuliah dari sistem informasi akademik kampus
- **Multi-jurusan:** Perluasan sistem untuk mendukung lebih dari satu jurusan
- **Mobile view:** Optimasi tampilan untuk akses via smartphone
- **Audit trail:** Log lengkap semua perubahan data (siapa mengubah apa, kapan)
