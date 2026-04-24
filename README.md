# Course Timetabling System (CTS)

Sistem Penjadwalan Kuliah berbasis web untuk Jurusan Matematika FMIPA Universitas Riau. Sistem ini menggantikan proses penyusunan jadwal perkuliahan manual berbasis Microsoft Excel dengan aplikasi intranet yang mendukung manajemen data, penyusunan jadwal secara terstruktur, dan deteksi konflik secara otomatis.

---

## Fitur Utama

### Manajemen Data Master
- CRUD lengkap untuk Program Studi, Kurikulum, Mata Kuliah, Kelas Paralel, Dosen, Ruang, dan Timeslot
- 15 timeslot tetap (3 sesi per hari, Senin–Jumat): 07:30–10:00, 10:00–12:30, 13:00–15:30
- Soft delete untuk entitas master agar integritas data historis terjaga

### Penjadwalan Manual
- Sesi jadwal per semester dan tahun akademik dengan alur status: Draft, Aktif, Arsip
- Penugasan (assignment) kombinasi kelas mata kuliah, dosen, timeslot, dan ruang (opsional)
- Dukungan team teaching: dua dosen per kelas dengan pengaturan urutan masuk dan pertukaran pasca-UTS
- Import jadwal dari file Excel historis sebagai titik awal penyusunan
- Export jadwal ke format Excel standar jurusan

### Deteksi Konflik Otomatis
Engine berbasis aturan (rule-based) yang mendeteksi konflik secara otomatis:

**Hard Constraints (ERROR):**
- HC-01: Dosen double-booking di timeslot yang sama
- HC-02: Ruang double-booking di timeslot yang sama (kondisional, hanya jika ruang terisi)
- HC-05: Satu kelas mata kuliah hanya boleh memiliki satu penugasan per sesi
- HC-06: Dosen dijadwalkan di slot yang ia tandai tidak tersedia
- HC-07: Kelas paralel dari mata kuliah yang sama wajib di timeslot yang sama
- HC-08: Beban harian mahasiswa melebihi 2 mata kuliah atau 6 SKS per hari
- HC-09: Beban harian dosen melebihi 2 mata kuliah atau 6 SKS per hari

**Soft Constraints (WARNING):**
- SC-01: Mata kuliah satu semester satu prodi dijadwalkan bersamaan
- SC-02: Distribusi beban SKS antar dosen tidak merata
- SC-03: Preferensi hari mengajar dosen dilanggar
- SC-05: Penempatan ruang tidak mengikuti prioritas lantai berdasarkan usia dosen

### Preferensi Dosen
- Dosen dapat mengajukan preferensi hari mengajar dalam dua fase: sebelum jadwal disusun (pre-schedule) dan setelah draft jadwal dirilis (post-draft)
- Sistem mencatat preferensi yang dilanggar dan menampilkan ringkasan pelanggaran per sesi

### Laporan
- Rekap beban SKS per dosen dengan breakdown per program studi
- Peta penggunaan ruang dalam format matriks hari x timeslot x ruang
- Ringkasan pelanggaran preferensi dosen per sesi

### Kontrol Akses Berbasis Peran (RBAC)
Tujuh peran pengguna dengan hak akses yang berbeda:

| Peran | Kode | Kewenangan |
|-------|------|------------|
| Admin Sistem | `admin` | Akses penuh termasuk manajemen user |
| Ketua Jurusan | `ketua_jurusan` | Persetujuan dan pengesahan jadwal |
| Sekretaris Jurusan | `sekretaris_jurusan` | Edit jadwal tingkat jurusan |
| Koordinator Prodi | `koordinator_prodi` | Edit jadwal prodi sendiri |
| Tendik Jurusan | `tendik_jurusan` | Edit jadwal tingkat jurusan |
| Tendik Prodi | `tendik_prodi` | Edit jadwal prodi sendiri |
| Dosen | `dosen` | Lihat jadwal diri, preferensi, team teaching |

---

## Teknologi yang Digunakan

### Backend
| Komponen | Teknologi | Versi |
|----------|-----------|-------|
| Framework API | FastAPI | 0.110.0 |
| Runtime | Python | 3.11 |
| ORM | SQLAlchemy | 2.0.29 |
| Migrasi Database | Alembic | 1.13.1 |
| Database | PostgreSQL | 15 |
| Autentikasi | JWT (python-jose) + bcrypt (passlib) | — |
| Excel I/O | openpyxl + pandas | 3.1.2 / 2.2.1 |
| Testing | pytest + httpx | 8.1.1 / 0.27.0 |

### Frontend
| Komponen | Teknologi | Versi |
|----------|-----------|-------|
| Framework | React + TypeScript | 18.3 / 5.6 |
| Build Tool | Vite | 6.0 |
| UI Components | Tailwind CSS + shadcn/ui (Radix UI) | 3.4 |
| State Management | Zustand | 5.0 |
| Data Fetching | TanStack Query | 5.x |
| HTTP Client | Axios | 1.7 |
| Routing | React Router DOM | 6.x |

### Infrastruktur
| Komponen | Teknologi |
|----------|-----------|
| Containerization | Docker + Docker Compose |
| Reverse Proxy | Nginx |

---

## Instalasi dan Menjalankan Proyek

### Prasyarat
- Docker dan Docker Compose (dijalankan di Linux atau WSL)
- Git

### Langkah Instalasi

**1. Clone repository**

```bash
git clone https://github.com/<username>/university_course_timetabling.git
cd university_course_timetabling
```

**2. Salin file konfigurasi environment**

```bash
cp backend/.env.example .env
```

Edit `.env` dan ganti nilai `SECRET_KEY` dengan string acak yang aman:

```env
DATABASE_URL=postgresql://cts_user:cts_password@db:5432/cts
SECRET_KEY=ganti-dengan-string-acak-yang-aman
CORS_ORIGINS=http://localhost,http://proxy
```

**3. Jalankan stack**

```bash
docker compose up --build
```

Tunggu hingga semua service berstatus healthy. Proses build pertama kali membutuhkan waktu lebih lama.

**4. Jalankan migrasi database**

```bash
docker compose exec api alembic upgrade head
```

**5. Seed data awal**

Perintah ini membuat 15 timeslot tetap dan akun admin default:

```bash
docker compose exec api python -m scripts.seed
```

Kredensial admin default: username `admin`, password `admin123`. Ganti password setelah login pertama.

**6. Akses aplikasi**

| Layanan | URL |
|---------|-----|
| Aplikasi web | http://localhost |
| API documentation (Swagger) | http://localhost/api/docs |
| API documentation (ReDoc) | http://localhost/api/redoc |

---

## Penggunaan Sehari-hari

**Menjalankan ulang tanpa rebuild:**

```bash
docker compose up
```

**Menghentikan semua service:**

```bash
docker compose down
```

**Menghentikan dan menghapus data database:**

```bash
docker compose down -v
```

**Melihat log:**

```bash
docker compose logs api        # log backend
docker compose logs frontend   # log frontend
docker compose logs db         # log database
```

**Menjalankan test backend:**

```bash
docker compose exec api pytest tests/ -v
```

---

## Struktur Folder

```
university_course_timetabling/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── config.py                # Konfigurasi aplikasi
│   │   ├── database.py              # SQLAlchemy engine dan session
│   │   ├── models/                  # ORM models (satu file per entitas)
│   │   ├── schemas/                 # Pydantic schemas (request/response)
│   │   ├── routers/                 # FastAPI route handlers (satu file per domain)
│   │   ├── services/
│   │   │   ├── conflict_engine.py   # Rule-based conflict detection engine
│   │   │   ├── excel_importer.py    # ETL dari file Excel
│   │   │   └── excel_exporter.py    # Export ke file Excel
│   │   └── core/
│   │       ├── auth.py              # JWT utilities
│   │       ├── security.py          # bcrypt hashing
│   │       └── permissions.py       # RBAC helpers dan konstanta role
│   ├── alembic/                     # Migrasi database
│   ├── scripts/
│   │   └── seed.py                  # Seed data awal (timeslot + admin)
│   ├── tests/                       # Unit dan integration tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/                   # Halaman per route
│   │   ├── components/              # Shared components
│   │   ├── api/                     # Axios instance dan API functions
│   │   ├── store/                   # Zustand stores
│   │   └── hooks/                   # Custom React hooks
│   ├── package.json
│   └── Dockerfile
├── nginx/
│   └── nginx.conf                   # Konfigurasi reverse proxy
├── data_dukung_aktualisasi/         # Data Excel sumber (read-only)
├── docker-compose.yml               # Konfigurasi produksi
├── docker-compose.override.yml      # Override untuk development (hot reload)
└── .env.example                     # Template environment variables
```

---

## Konfigurasi Development

File `docker-compose.override.yml` aktif secara otomatis saat menjalankan `docker compose up` di lingkungan development. Konfigurasi ini mengaktifkan:

- Hot reload backend (uvicorn `--reload`)
- Hot reload frontend (Vite HMR)
- Port database di-expose ke host pada port `5433` untuk akses via GUI (DBeaver, pgAdmin)
- Port API di-expose langsung pada port `8000`

---

## Catatan Implementasi

Proyek ini dikembangkan secara bertahap menggunakan metodologi Spec-Driven Development. Dokumentasi spesifikasi lengkap tersedia di:

- `.kiro/specs/timetabling/requirements.md` — user stories dan aturan bisnis
- `.kiro/specs/timetabling/design.md` — arsitektur, skema database, dan desain API
- `.kiro/specs/timetabling/tasks.md` — rencana implementasi per fase

Fitur yang masih dalam pengembangan (Fase 2 dan seterusnya): optimisasi jadwal otomatis (Genetic Algorithm / CP-SAT), notifikasi email, integrasi SIAKAD, dan dukungan multi-jurusan.
