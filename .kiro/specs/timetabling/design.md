# Design — Sistem Penjadwalan Kuliah
## Jurusan Matematika FMIPA Universitas Riau

**Versi:** 1.6.0  
**Tanggal:** April 2026  
**Status:** Draft  
**Changelog v1.6.0:** Tambah SC-05 ke enum conflict_log (`FLOOR_PRIORITY_VIOLATED`); tambah algoritma `check_floor_priority()` ke conflict engine; update kolom `dosen.tgl_lahir` sebagai basis perhitungan; tambah field `override_floor_priority` ke `jadwal_assignment`.  
**Changelog v1.5.0:** Restrukturisasi role — `kaprodi` diganti `ketua_jurusan`; tambah `tendik_prodi` dan `tendik_jurusan`; update tabel `user` (7 role); update semua endpoint dengan role baru.  
**Changelog v1.2.0:** Tambah role `sekretaris_jurusan` dan `koordinator_prodi` ke tabel `user`; tambah tabel `team_teaching_order` untuk pengaturan urutan masuk kelas dan swap setelah UTS; perluas tabel `dosen_preference` (ganti `dosen_unavailability` untuk preferensi hari) dengan kolom `fase`, `status`, dan `is_violated`; tambah endpoint preferensi dosen dan team teaching; update RBAC di seluruh endpoint; tambah SC-03 ke conflict engine.  
**Changelog v1.1.0:** Revisi timeslot menjadi 3 sesi tetap per hari (15 slot total); tambah algoritma HC-07/HC-08/HC-09; keputusan struktur dosen (dua kolom); ruang opsional dipertegas; catatan ETL data tidak rapi; update enum `conflict_log.jenis`.

---

## 1. Arsitektur Sistem

### 1.1 Gambaran Umum

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (Intranet)                       │
│                   React + TypeScript + Tailwind                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP/JSON (REST)
                               │ Port 80 (Nginx reverse proxy)
┌──────────────────────────────▼──────────────────────────────────┐
│                        Backend API                              │
│                    FastAPI (Python 3.11)                        │
│                                                                 │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────────────┐  │
│  │ Auth Module  │  │  Data Module    │  │  Schedule Module  │  │
│  │ (JWT/bcrypt) │  │  (CRUD master)  │  │  (jadwal, assign) │  │
│  └──────────────┘  └─────────────────┘  └───────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────────────┐  │
│  │ Conflict     │  │  Import/Export  │  │  Report Module    │  │
│  │ Engine       │  │  (Excel ETL)    │  │  (SKS, room map)  │  │
│  └──────────────┘  └─────────────────┘  └───────────────────┘  │
│                                                                 │
│                       SQLAlchemy ORM                           │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                       PostgreSQL 15                             │
│                    (persistent volume)                          │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Deployment Stack (Docker Compose)

```yaml
services:
  db:         PostgreSQL 15  (port 5432, internal only)
  api:        FastAPI        (port 8000, internal only)
  frontend:   React (Nginx)  (port 3000, internal only)
  proxy:      Nginx          (port 80, exposed to intranet)
```

Semua service berjalan dalam satu Docker network. Hanya port 80 yang di-expose ke jaringan intranet kampus.

---

## 2. Database Schema

### 2.1 Entity Relationship Diagram (Konseptual)

```
prodi ──< kurikulum ──< mata_kuliah ──< mata_kuliah_kelas
                                              │
                              ┌───────────────┤
                              │               │
                           dosen           jadwal_assignment
                              │          /         │         \
                       dosen_unavail   kelas    timeslot    ruang
                                               
sesi_jadwal ──────────────────────────< jadwal_assignment
```

### 2.2 Tabel Detail

---

#### `prodi`
Program studi yang terdaftar di sistem.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `kode` | VARCHAR(10) | UNIQUE, NOT NULL | Misal: `MAT1`, `STK1` |
| `strata` | VARCHAR(5) | NOT NULL | `S-1`, `S-2`, `D-3` |
| `nama` | VARCHAR(100) | NOT NULL | Nama lengkap prodi |
| `singkat` | VARCHAR(20) | NOT NULL | Misal: `S1 MTK` |
| `kategori` | VARCHAR(20) | NOT NULL | `Internal` / `Layanan` |
| `is_active` | BOOLEAN | DEFAULT TRUE | |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |

---

#### `kurikulum`
Kurikulum yang berlaku per program studi.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `kode` | VARCHAR(20) | UNIQUE, NOT NULL | Misal: `21S1MATH`, `25S1MATH` |
| `tahun` | VARCHAR(4) | NOT NULL | `2021`, `2025` |
| `prodi_id` | UUID | FK → prodi, NOT NULL | |
| `is_active` | BOOLEAN | DEFAULT TRUE | |

---

#### `mata_kuliah`
Mata kuliah dalam suatu kurikulum.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `kode` | VARCHAR(20) | NOT NULL | Kode MK |
| `kurikulum_id` | UUID | FK → kurikulum, NOT NULL | |
| `nama` | VARCHAR(200) | NOT NULL | |
| `sks` | SMALLINT | NOT NULL | Jumlah SKS |
| `semester` | SMALLINT | NOT NULL | Semester ke- (1–8) |
| `jenis` | VARCHAR(10) | NOT NULL | `Wajib` / `Pilihan` |
| `prasyarat` | VARCHAR(200) | NULLABLE | Kode MK prasyarat (teks) |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |
| UNIQUE | (`kode`, `kurikulum_id`) | | |

---

#### `mata_kuliah_kelas`
Kelas paralel dari setiap mata kuliah yang akan dijadwalkan.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `mata_kuliah_id` | UUID | FK → mata_kuliah, NOT NULL | |
| `kelas` | VARCHAR(5) | NULLABLE | `A`, `B`, `C`, atau NULL jika tunggal |
| `label` | VARCHAR(200) | NOT NULL | Misal: `Fisika Dasar (MTK25) - A` |
| `ket` | TEXT | NULLABLE | Keterangan tambahan |
| UNIQUE | (`mata_kuliah_id`, `kelas`) | | |

---

#### `ruang`
Ruang kuliah yang tersedia.

> **Fase 1:** Data ruang dikelola oleh pihak Fakultas, bukan Jurusan. Tabel ini tersedia di skema dan dapat diisi kapan saja, tetapi **tidak diwajibkan**. Kolom `ruang_id` pada `jadwal_assignment` bersifat NULLABLE; HC-02 hanya aktif jika kolom tersebut terisi. Kapasitas default ruang adalah **45 orang** jika kolom `kapasitas` belum diisi.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `nama` | VARCHAR(20) | UNIQUE, NOT NULL | Misal: `R.101`, `LAB I` |
| `kapasitas` | SMALLINT | DEFAULT 45 | Kapasitas tempat duduk; default 45 jika belum diisi |
| `lantai` | SMALLINT | NULLABLE | |
| `gedung` | VARCHAR(100) | NULLABLE | |
| `jenis` | VARCHAR(20) | DEFAULT `Kelas` | `Kelas` / `Lab` / `Seminar` |
| `is_active` | BOOLEAN | DEFAULT TRUE | |

---

#### `timeslot`
Slot waktu standar yang tersedia untuk perkuliahan.

Terdapat **3 sesi tetap per hari** × 5 hari kerja = **15 timeslot** total. Tidak ada slot ad-hoc di luar daftar ini.

| Sesi | Jam Mulai | Jam Selesai | SKS |
|------|-----------|-------------|-----|
| Sesi 1 | 07:30 | 10:00 | 3 |
| Sesi 2 | 10:00 | 12:30 | 3 |
| Sesi 3 | 13:00 | 15:30 | 3 |

Dengan 5 hari (Senin–Jumat), total timeslot = 15 baris seed data (kode: `mon_s1`, `mon_s2`, `mon_s3`, `tue_s1`, dst.).

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `kode` | VARCHAR(20) | UNIQUE, NOT NULL | Misal: `mon_s1`, `fri_s3` |
| `hari` | VARCHAR(10) | NOT NULL | `Senin`, `Selasa`, `Rabu`, `Kamis`, `Jumat` |
| `sesi` | SMALLINT | NOT NULL | `1`, `2`, atau `3` |
| `jam_mulai` | TIME | NOT NULL | |
| `jam_selesai` | TIME | NOT NULL | |
| `label` | VARCHAR(30) | NOT NULL | Misal: `Senin 07:30–10:00` |
| `sks` | SMALLINT | NOT NULL | `3` (tetap untuk semua slot) |

---

#### `dosen`
Data dosen pengampu.

> **Fase 1 — Status Data:** Data dosen belum diinput penuh. ETL importer harus toleran terhadap baris dosen yang kosong, duplikat, atau referensi tidak konsisten; baris bermasalah dicatat sebagai `import_warning` dan dilewati (tidak menyebabkan import gagal total). Kolom `bkd_limit_sks` tersedia sebagai placeholder untuk fase berikutnya; validasinya tidak aktif di Fase 1.
>
> **Keputusan Struktur Dosen:** Satu mata kuliah diampu oleh maksimal **dua dosen**. Pilihannya adalah dua kolom (`dosen1_id`, `dosen2_id`) pada `jadwal_assignment`, atau dua baris terpisah. Keputusan: **dua kolom**. Alasan: jumlah dosen per kelas bersifat tetap (maks 2), dua kolom lebih efisien untuk query conflict detection (tidak perlu self-join), dan sesuai dengan format Excel existing (kolom `Dosen I` dan `Dosen II`). Jika di kemudian hari ada kebutuhan lebih dari 2 dosen, tambahkan tabel `jadwal_assignment_dosen` sebagai many-to-many.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `nidn` | VARCHAR(20) | UNIQUE, NULLABLE | NIDN/NUPTK |
| `nip` | VARCHAR(25) | UNIQUE, NULLABLE | NIP |
| `kode` | VARCHAR(10) | UNIQUE, NOT NULL | Misal: `MAS`, `AAD` |
| `nama` | VARCHAR(200) | NOT NULL | Nama lengkap + gelar |
| `jabfung` | VARCHAR(50) | NULLABLE | Jabatan fungsional |
| `kjfd` | VARCHAR(100) | NULLABLE | Kelompok bidang keilmuan |
| `homebase_prodi_id` | UUID | FK → prodi, NULLABLE | |
| `bkd_limit_sks` | SMALLINT | NULLABLE | Placeholder untuk batas BKD fase berikutnya; tidak divalidasi di Fase 1 |
| `tgl_lahir` | DATE | NULLABLE | |
| `status` | VARCHAR(20) | DEFAULT `Aktif` | `Aktif` / `Non-Aktif` / `Pensiun` |
| `user_id` | UUID | FK → user, NULLABLE | Link ke akun login |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |

---

#### `dosen_unavailability`
Slot waktu yang dinyatakan dosen tidak tersedia.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `dosen_id` | UUID | FK → dosen, NOT NULL | |
| `timeslot_id` | UUID | FK → timeslot, NOT NULL | |
| `sesi_id` | UUID | FK → sesi_jadwal, NULLABLE | NULL = berlaku semua semester |
| `catatan` | TEXT | NULLABLE | Alasan tidak tersedia |
| UNIQUE | (`dosen_id`, `timeslot_id`, `sesi_id`) | | |

---

#### `dosen_preference`
Preferensi hari mengajar yang diajukan dosen. Bersifat **soft** — tidak wajib dipenuhi oleh sistem.

> **Catatan:** Preferensi dapat diajukan dalam dua fase: **(a) pre-schedule** — sebelum jadwal disusun, dan **(b) post-draft** — setelah draft jadwal dirilis. Sistem mencatat apakah preferensi dilanggar (`is_violated`) dan Admin dapat melihat ringkasan jumlah pelanggaran per sesi.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `dosen_id` | UUID | FK → dosen, NOT NULL | |
| `sesi_id` | UUID | FK → sesi_jadwal, NOT NULL | |
| `timeslot_id` | UUID | FK → timeslot, NOT NULL | Slot yang diinginkan |
| `fase` | VARCHAR(15) | NOT NULL | `pre_schedule` / `post_draft` |
| `catatan` | TEXT | NULLABLE | Alasan atau keterangan tambahan |
| `is_violated` | BOOLEAN | DEFAULT FALSE | TRUE jika assignment dosen tidak sesuai preferensi ini |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |
| UNIQUE | (`dosen_id`, `sesi_id`, `timeslot_id`, `fase`) | | |

---

#### `team_teaching_order`
Pengaturan urutan masuk kelas untuk mata kuliah team teaching. Satu baris per dosen per kelas paralel per sesi.

> **Catatan:** Untuk mata kuliah yang diampu dua dosen (team teaching), tabel ini mencatat siapa yang masuk duluan di kelas mana pada paruh pertama semester (pra-UTS), dan siapa yang masuk setelah pertukaran (pasca-UTS). **Pengaturan dilakukan oleh dosen pengampu yang bersangkutan** — bukan oleh Admin. Admin dan pengelola jurusan hanya dapat melihat ringkasan konfigurasi.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `assignment_id` | UUID | FK → jadwal_assignment, NOT NULL | Assignment kelas yang bersangkutan |
| `dosen_id` | UUID | FK → dosen, NOT NULL | Dosen yang diatur urutannya |
| `urutan_pra_uts` | SMALLINT | NOT NULL | `1` = masuk duluan, `2` = masuk kedua |
| `urutan_pasca_uts` | SMALLINT | NULLABLE | `1` / `2`; NULL = tidak ada pertukaran |
| `catatan` | TEXT | NULLABLE | |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | |
| UNIQUE | (`assignment_id`, `dosen_id`) | | |

---

#### `sesi_jadwal`
Satu sesi penjadwalan mewakili satu semester/tahun akademik.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `nama` | VARCHAR(100) | NOT NULL | Misal: `Genap 2025-2026` |
| `semester` | VARCHAR(10) | NOT NULL | `Ganjil` / `Genap` |
| `tahun_akademik` | VARCHAR(10) | NOT NULL | Misal: `2025-2026` |
| `status` | VARCHAR(20) | DEFAULT `Draft` | `Draft` / `Aktif` / `Arsip` |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |
| UNIQUE | (`semester`, `tahun_akademik`) | | |

---

#### `jadwal_assignment`
Tabel inti — setiap baris adalah satu penugasan jadwal.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `sesi_id` | UUID | FK → sesi_jadwal, NOT NULL | |
| `mk_kelas_id` | UUID | FK → mata_kuliah_kelas, NOT NULL | |
| `dosen1_id` | UUID | FK → dosen, NOT NULL | Dosen pengampu utama |
| `dosen2_id` | UUID | FK → dosen, NULLABLE | Dosen pengampu kedua |
| `timeslot_id` | UUID | FK → timeslot, NOT NULL | |
| `ruang_id` | UUID | FK → ruang, NULLABLE | NULL = belum ditentukan |
| `override_floor_priority` | BOOLEAN | DEFAULT FALSE | TRUE jika penugasan ruang sengaja mengabaikan prioritas lantai (override manual) |
| `catatan` | TEXT | NULLABLE | |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | |
| UNIQUE | (`sesi_id`, `mk_kelas_id`) | | Satu kelas MK satu slot per sesi |

**Indeks tambahan:**
```sql
-- Untuk query deteksi konflik dosen
CREATE INDEX idx_assignment_dosen1 ON jadwal_assignment(sesi_id, dosen1_id, timeslot_id);
CREATE INDEX idx_assignment_dosen2 ON jadwal_assignment(sesi_id, dosen2_id, timeslot_id);
-- Untuk query deteksi konflik ruang
CREATE INDEX idx_assignment_ruang  ON jadwal_assignment(sesi_id, ruang_id, timeslot_id);
```

---

#### `conflict_log`
Hasil deteksi konflik per run pemeriksaan.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `sesi_id` | UUID | FK → sesi_jadwal, NOT NULL | |
| `jenis` | VARCHAR(30) | NOT NULL | Lihat enum di bawah |

**Enum `jenis` yang valid:**

| Nilai | Rule | Aktif Fase 1 |
|-------|------|--------------|
| `LECTURER_DOUBLE` | HC-01 | ✅ |
| `ROOM_DOUBLE` | HC-02 | ✅ (kondisional) |
| `ROOM_CAPACITY` | HC-03 | ⏸ Defer |
| `BKD_WORKLOAD` | HC-04 | ⏸ Defer |
| `SINGLE_ASSIGNMENT` | HC-05 | ✅ |
| `LECTURER_UNAVAILABLE` | HC-06 | ✅ |
| `PARALLEL_MISMATCH` | HC-07 | ✅ |
| `STUDENT_DAILY_OVERLOAD` | HC-08 | ✅ |
| `LECTURER_DAILY_OVERLOAD` | HC-09 | ✅ |
| `STUDENT_CONFLICT` | SC-01 | ✅ (WARNING) |
| `WORKLOAD_INEQUITY` | SC-02 | ✅ (WARNING) |
| `LECTURER_PREFERENCE_VIOLATED` | SC-03 | ✅ (WARNING) |
| `FLOOR_PRIORITY_VIOLATED` | SC-05 | ✅ (WARNING, kondisional) |
| `severity` | VARCHAR(10) | NOT NULL | `ERROR` (HC) / `WARNING` (SC) |
| `assignment_ids` | UUID[] | NOT NULL | Array assignment yang terlibat |
| `pesan` | TEXT | NOT NULL | Deskripsi konflik yang dapat dibaca manusia |
| `detail` | JSONB | NULLABLE | Data tambahan (nama dosen, slot, dll) |
| `checked_at` | TIMESTAMP | DEFAULT NOW() | |
| `is_resolved` | BOOLEAN | DEFAULT FALSE | Ditandai manual oleh admin |

---

#### `user`
Akun pengguna sistem.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|------------|------------|
| `id` | UUID | PK | |
| `username` | VARCHAR(50) | UNIQUE, NOT NULL | |
| `email` | VARCHAR(100) | UNIQUE, NULLABLE | |
| `password_hash` | VARCHAR(200) | NOT NULL | bcrypt hash |
| `role` | VARCHAR(30) | NOT NULL | `admin` / `ketua_jurusan` / `sekretaris_jurusan` / `koordinator_prodi` / `dosen` / `tendik_prodi` / `tendik_jurusan` |
| `prodi_id` | UUID | FK → prodi, NULLABLE | Untuk role `koordinator_prodi` dan `tendik_prodi` |
| `is_active` | BOOLEAN | DEFAULT TRUE | |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |
| `last_login` | TIMESTAMP | NULLABLE | |

**Hak akses per role:**

| Role | Edit Jadwal | Approve/Sahkan | Manajemen User | Lihat Semua Prodi | Lihat Prodi Sendiri | Lihat Jadwal Diri | Atur Team Teaching |
|------|:-----------:|:--------------:|:--------------:|:-----------------:|:-------------------:|:-----------------:|:-----------------:|
| `admin` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | View only |
| `ketua_jurusan` | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | View only |
| `sekretaris_jurusan` | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | View only |
| `koordinator_prodi` | ✅ (prodi sendiri) | ❌ | ❌ | ❌ | ✅ | ✅ | View only |
| `tendik_jurusan` | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | View only |
| `tendik_prodi` | ✅ (prodi sendiri) | ❌ | ❌ | ❌ | ✅ | ✅ | View only |
| `dosen` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ (own) |

**Konstanta RBAC:**
```python
EDITOR_ROLES_JURUSAN = ["admin", "sekretaris_jurusan", "tendik_jurusan"]
EDITOR_ROLES_PRODI   = ["admin", "sekretaris_jurusan", "tendik_jurusan",
                         "koordinator_prodi", "tendik_prodi"]
VIEWER_ROLES         = ["ketua_jurusan"]
```

---

## 3. Conflict Detection Engine

### 3.1 Arsitektur Engine

Engine diimplementasikan sebagai modul Python murni (rule-based, tanpa ML). Setiap rule adalah fungsi yang menerima snapshot jadwal dari database dan mengembalikan daftar `ConflictResult`.

```python
# Pseudocode struktur engine (Fase 1)
class ConflictEngine:
    def run(self, sesi_id: UUID) -> list[ConflictResult]:
        assignments = self.fetch_assignments(sesi_id)
        results = []
        # Hard Constraints — Aktif
        results += self.check_lecturer_double(assignments)      # HC-01
        results += self.check_room_double(assignments)          # HC-02 (kondisional)
        # HC-03 Room Capacity   → DEFERRED
        # HC-04 BKD Workload    → DEFERRED
        results += self.check_lecturer_unavail(assignments)     # HC-06
        results += self.check_parallel_mismatch(assignments)    # HC-07
        results += self.check_student_daily_load(assignments)   # HC-08
        results += self.check_lecturer_daily_load(assignments)  # HC-09
        # Soft Constraints
        results += self.check_student_conflict(assignments)     # SC-01
        results += self.check_workload_equity(assignments)      # SC-02
        results += self.check_lecturer_preference(assignments)  # SC-03
        results += self.check_floor_priority(assignments)       # SC-05
        return results
```

### 3.2 Algoritma Per Rule

**HC-01 — Lecturer Double Booking**
```
Untuk setiap (sesi_id, timeslot_id):
  Kumpulkan semua assignment dengan dosen1 atau dosen2 = X
  Jika COUNT > 1 → konflik ERROR untuk dosen X
```

**HC-02 — Room Double Booking**
```
Untuk setiap (sesi_id, timeslot_id, ruang_id != NULL):
  Jika COUNT > 1 → konflik ERROR untuk ruang tersebut
```

**HC-04 — BKD Workload (DEFERRED)**
```
→ DEFERRED ke Fase 2. Ketentuan yang direncanakan:
  Minimum 9 SKS per dosen per semester.
  Distribusi bertingkat: dosen junior tidak boleh melebihi beban dosen senior
    dalam satu program studi (berdasarkan masa kerja).
  Pengecualian dapat diberikan oleh tim pengelola jurusan.
  Sistem memberikan WARNING jika urutan beban tidak sesuai pola umum.
  Kolom bkd_limit_sks tersedia di tabel dosen sebagai placeholder.
```

**HC-07 — Parallel Class Same Slot**
```
Kelompokkan assignment berdasarkan mata_kuliah_id (induk kelas paralel)
Untuk setiap kelompok dengan COUNT(kelas) > 1:
  Ambil set timeslot_id yang unik dalam kelompok
  Jika len(set timeslot_id) > 1:
    → ERROR PARALLEL_MISMATCH
    → Pesan: "Kelas paralel [MK] memiliki slot berbeda: A di [slot1], B di [slot2]"
  Jika timeslot sama tetapi ruang_id sama (dan bukan NULL):
    → ERROR ROOM_DOUBLE (sudah ditangani HC-02)
```

**HC-08 — Student Daily Load**
```
Untuk setiap (prodi, semester, sesi, hari):
  Kumpulkan semua assignment MK yang termasuk prodi+semester tersebut di hari itu
  Hitung: jumlah_mk = COUNT(assignment), total_sks = SUM(sks)
  Jika jumlah_mk > 2 ATAU total_sks > 6:
    → ERROR STUDENT_DAILY_OVERLOAD
    → Pesan: "Prodi [X] Smt [N] pada hari [Y]: [Z] MK / [W] SKS melebihi batas harian"
```

**HC-09 — Lecturer Daily Load**
```
Untuk setiap (dosen_id, sesi, hari):
  Kumpulkan semua assignment di mana dosen1_id=X ATAU dosen2_id=X, pada hari itu
  Hitung: jumlah_mk = COUNT(assignment), total_sks = SUM(sks)
  Jika jumlah_mk > 2 ATAU total_sks > 6:
    → ERROR LECTURER_DAILY_OVERLOAD
    → Pesan: "Dosen [nama] pada hari [Y]: [Z] MK / [W] SKS melebihi batas harian"
```

**SC-03 — Lecturer Preference Violation**
```
Untuk setiap dosen dalam sesi:
  Ambil semua dosen_preference dengan sesi_id = sesi_id dan dosen_id = X
  Untuk setiap preferensi:
    Cek apakah ada assignment dosen X di timeslot yang dipreferensikan
    Jika tidak ada assignment di timeslot tersebut:
      → WARNING LECTURER_PREFERENCE_VIOLATED
      → Update dosen_preference.is_violated = TRUE
      → Pesan: "Preferensi dosen [nama] untuk slot [label] tidak dipenuhi ([fase])"
  Setelah semua preferensi diperiksa:
    Hitung total_violated = COUNT(is_violated = TRUE) untuk sesi ini
    Simpan ringkasan ke conflict_log.detail sebagai {"total_violated": N}
```

**SC-05 — Floor Priority by Lecturer Age**
```
Lewati jika ruang_id NULL atau tgl_lahir dosen NULL.
Lewati jika assignment.override_floor_priority = TRUE.

Untuk setiap timeslot dalam sesi:
  Ambil semua assignment di timeslot tersebut yang memiliki ruang_id terisi
  Untuk setiap assignment:
    Ambil lantai ruang (ruang.lantai)
    Ambil usia dosen1 dari tgl_lahir (usia = tahun_sekarang - tahun_lahir)
  Urutkan assignment berdasarkan usia dosen (descending = senior lebih tua)
  Urutkan ruang berdasarkan lantai (ascending = lantai rendah lebih dulu)
  Bandingkan urutan: dosen paling senior seharusnya di lantai paling rendah
  Jika urutan tidak sesuai:
    → WARNING FLOOR_PRIORITY_VIOLATED
    → Pesan: "Dosen [nama] (lahir [tgl]) ditempatkan di lantai [N],
              lebih tinggi dari dosen yang lebih muda [nama2] di lantai [M]"
    → detail: {"dosen_senior": nama, "lantai_senior": N,
               "dosen_junior": nama2, "lantai_junior": M}
```
```
Untuk setiap (prodi, semester, sesi):
  Ambil semua kelas MK yang termasuk semester tersebut
  Untuk setiap pasangan (mk_a, mk_b) dengan timeslot sama:
    Catat sebagai WARNING
  (Catatan: SC-01 bersifat informatif — HC-08 sudah menangkap kelebihan beban harian
   sebagai ERROR; SC-01 menangkap duplikasi slot yang mungkin tidak melanggar HC-08)
```

---

## 4. API Endpoint Design

### 4.1 Autentikasi

| Method | Path | Deskripsi | Role |
|--------|------|-----------|------|
| POST | `/auth/login` | Login, kembalikan JWT | Public |
| POST | `/auth/refresh` | Refresh token | All |
| POST | `/auth/logout` | Invalidate token | All |
| GET | `/auth/me` | Profil user aktif | All |

### 4.2 Data Master

| Method | Path | Deskripsi | Role |
|--------|------|-----------|------|
| GET | `/prodi` | List semua prodi | All |
| POST | `/prodi` | Tambah prodi | Admin |
| PUT | `/prodi/{id}` | Update prodi | Admin |
| GET | `/kurikulum` | List kurikulum | All |
| POST | `/kurikulum` | Tambah kurikulum | Admin |
| GET | `/mata-kuliah` | List MK (filter: prodi, kurikulum, semester) | All |
| POST | `/mata-kuliah` | Tambah MK | Admin |
| PUT | `/mata-kuliah/{id}` | Update MK | Admin |
| DELETE | `/mata-kuliah/{id}` | Hapus MK (soft delete) | Admin |
| GET | `/mata-kuliah/{id}/kelas` | List kelas paralel MK | All |
| POST | `/mata-kuliah/{id}/kelas` | Tambah kelas paralel | Admin |
| GET | `/dosen` | List dosen | Admin, Sekretaris, Koordinator, Tendik Jurusan, Tendik Prodi, Ketua Jurusan |
| POST | `/dosen` | Tambah dosen | Admin |
| PUT | `/dosen/{id}` | Update dosen | Admin |
| GET | `/dosen/{id}/jadwal` | Jadwal dosen (per sesi) | Admin, Sekretaris, Koordinator, Tendik Jurusan, Tendik Prodi, Ketua Jurusan, Dosen (own) |
| POST | `/dosen/{id}/unavailability` | Input ketidaktersediaan | Admin, Sekretaris, Tendik Jurusan, Dosen (own) |
| GET | `/dosen/{id}/preferences` | List preferensi hari dosen | Admin, Sekretaris, Tendik Jurusan, Dosen (own) |
| POST | `/dosen/{id}/preferences` | Ajukan preferensi hari (pre-schedule / post-draft) | Admin, Sekretaris, Tendik Jurusan, Dosen (own) |
| PUT | `/dosen/{id}/preferences/{pid}` | Update preferensi | Admin, Sekretaris, Tendik Jurusan, Dosen (own) |
| DELETE | `/dosen/{id}/preferences/{pid}` | Hapus preferensi | Admin, Sekretaris, Tendik Jurusan, Dosen (own) |
| GET | `/ruang` | List ruang | All |
| POST | `/ruang` | Tambah ruang | Admin, Sekretaris, Tendik Jurusan |
| PUT | `/ruang/{id}` | Update ruang | Admin, Sekretaris, Tendik Jurusan |
| GET | `/timeslot` | List timeslot | All |
| POST | `/timeslot` | Tambah timeslot | Admin |

### 4.3 Penjadwalan

| Method | Path | Deskripsi | Role |
|--------|------|-----------|------|
| GET | `/sesi` | List sesi jadwal | All |
| POST | `/sesi` | Buat sesi baru | Admin, Sekretaris, Tendik Jurusan |
| PUT | `/sesi/{id}` | Update status sesi | Admin, Sekretaris, Tendik Jurusan |
| PATCH | `/sesi/{id}/approve` | Setujui / minta revisi jadwal | Ketua Jurusan |
| PATCH | `/sesi/{id}/publish` | Sahkan jadwal sebagai jadwal resmi | Ketua Jurusan |
| GET | `/sesi/{id}/assignments` | List semua assignment (filter: prodi, hari) | All* |
| POST | `/sesi/{id}/assignments` | Tambah assignment | Admin, Sekretaris, Tendik Jurusan, Koordinator Prodi, Tendik Prodi |
| PUT | `/sesi/{id}/assignments/{aid}` | Update assignment | Admin, Sekretaris, Tendik Jurusan, Koordinator Prodi, Tendik Prodi |
| PATCH | `/sesi/{id}/assignments/{aid}/override-floor` | Toggle override prioritas lantai | Admin, Sekretaris, Tendik Jurusan |
| DELETE | `/sesi/{id}/assignments/{aid}` | Hapus assignment | Admin, Sekretaris, Tendik Jurusan |
| GET | `/sesi/{id}/assignments/{aid}/team-teaching` | Lihat pengaturan team teaching | All |
| PUT | `/sesi/{id}/assignments/{aid}/team-teaching` | Set/update urutan masuk kelas team teaching | Dosen (own) |
| POST | `/sesi/{id}/assignments/{aid}/team-teaching/swap` | Jadwalkan pertukaran urutan setelah UTS | Dosen (own) |
| GET | `/sesi/{id}/preferences-summary` | Ringkasan pelanggaran preferensi dosen per sesi | Admin, Sekretaris, Tendik Jurusan, Ketua Jurusan |

> *Koordinator Prodi dan Tendik Prodi hanya melihat assignment prodi-nya; Dosen hanya melihat assignment dirinya; Ketua Jurusan melihat semua.

### 4.4 Konflik dan Laporan

| Method | Path | Deskripsi | Role |
|--------|------|-----------|------|
| POST | `/sesi/{id}/check-conflicts` | Jalankan conflict detection | Admin, Sekretaris, Tendik Jurusan, Koordinator Prodi, Tendik Prodi |
| GET | `/sesi/{id}/conflicts` | List konflik (filter: jenis, severity) | Admin, Sekretaris, Tendik Jurusan, Koordinator Prodi, Tendik Prodi, Ketua Jurusan |
| PATCH | `/sesi/{id}/conflicts/{cid}/resolve` | Tandai konflik sebagai resolved | Admin, Sekretaris, Tendik Jurusan |
| GET | `/sesi/{id}/reports/sks-rekap` | Rekap beban SKS per dosen | Admin, Sekretaris, Tendik Jurusan, Koordinator Prodi, Ketua Jurusan |
| GET | `/sesi/{id}/reports/room-map` | Peta penggunaan ruang | Admin, Sekretaris, Tendik Jurusan, Ketua Jurusan |

### 4.5 Import / Export

| Method | Path | Deskripsi | Role |
|--------|------|-----------|------|
| POST | `/import/master` | Import data master dari Excel | Admin |
| POST | `/import/jadwal` | Import jadwal dari Excel | Admin, Sekretaris, Tendik Jurusan |
| GET | `/sesi/{id}/export` | Export jadwal ke Excel | Admin, Sekretaris, Tendik Jurusan, Koordinator Prodi, Tendik Prodi, Ketua Jurusan |

---

## 5. UI Flow dan Halaman

### 5.1 Struktur Navigasi

```
Login
└── Dashboard (ringkasan sesi aktif, konflik terbuka, beban SKS)
    ├── Data Master
    │   ├── Dosen
    │   ├── Mata Kuliah
    │   │   └── Kelas Paralel
    │   ├── Ruang
    │   ├── Timeslot
    │   ├── Program Studi
    │   └── Kurikulum
    ├── Penjadwalan
    │   ├── Daftar Sesi
    │   └── Sesi Detail
    │       ├── Tabel Assignment (tampilan grid / tabel)
    │       ├── Form Tambah/Edit Assignment
    │       ├── Team Teaching (urutan masuk kelas & swap UTS)
    │       └── Deteksi Konflik
    ├── Laporan
    │   ├── Rekap SKS per Dosen
    │   ├── Peta Penggunaan Ruang
    │   └── Ringkasan Preferensi Dosen (jumlah pelanggaran)
    └── Pengaturan (Admin only)
        ├── Manajemen User
        └── Import / Export
```

### 5.2 Halaman Utama per Role

**Admin Sistem** — akses penuh ke semua halaman termasuk manajemen user dan konfigurasi sistem.

**Ketua Jurusan** — melihat:
- Dashboard (ringkasan sesi aktif, konflik terbuka, beban SKS)
- Tabel Assignment (read-only, semua prodi)
- Deteksi Konflik (read-only, semua prodi)
- Rekap SKS per Dosen
- Tombol Approve / Sahkan jadwal

**Sekretaris Jurusan** — akses penuh ke semua halaman kecuali manajemen user, konfigurasi sistem, dan tombol approve/sahkan.

**Koordinator Prodi** — melihat:
- Dashboard (terbatas: hanya data prodi sendiri)
- Tabel Assignment (edit, filter prodi sendiri)
- Deteksi Konflik (hanya konflik yang melibatkan prodi sendiri)
- Rekap SKS (hanya dosen homebase prodi sendiri)

**Tendik Jurusan** — akses setara Sekretaris Jurusan kecuali tanpa kewenangan akademik (tidak dapat menetapkan dosen pengampu).

**Tendik Prodi** — akses setara Koordinator Prodi kecuali tanpa kewenangan akademik.

**Dosen** — melihat:
- Jadwal Pribadi (kalender/tabel mingguan)
- Profil & Input Unavailability
- Form Preferensi Hari Mengajar (pre-schedule dan post-draft)
- Pengaturan Team Teaching (hanya untuk MK yang ia ampu sebagai team teaching)

### 5.3 Tampilan Tabel Assignment

Tabel assignment menampilkan kolom: Hari, Waktu, Ruang, Prodi, Kurikulum, Semester, Kode MK, Mata Kuliah (Kelas), Sifat, SKS, Dosen I, Dosen II, Status Konflik.

Baris yang memiliki konflik ERROR ditandai latar merah muda; konflik WARNING ditandai latar kuning. Ikon konflik dapat diklik untuk membuka detail.

---

## 6. Struktur Direktori Proyek

```
university_course_timetabling/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── config.py                # Settings (env vars)
│   │   ├── database.py              # SQLAlchemy engine & session
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── prodi.py
│   │   │   ├── kurikulum.py
│   │   │   ├── mata_kuliah.py
│   │   │   ├── dosen.py
│   │   │   ├── ruang.py
│   │   │   ├── timeslot.py
│   │   │   ├── sesi_jadwal.py
│   │   │   ├── jadwal_assignment.py
│   │   │   ├── conflict_log.py
│   │   │   └── user.py
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── routers/                 # FastAPI route handlers
│   │   │   ├── auth.py
│   │   │   ├── prodi.py
│   │   │   ├── dosen.py
│   │   │   ├── mata_kuliah.py
│   │   │   ├── ruang.py
│   │   │   ├── timeslot.py
│   │   │   ├── sesi.py
│   │   │   ├── assignment.py
│   │   │   ├── conflict.py
│   │   │   ├── report.py
│   │   │   └── import_export.py
│   │   ├── services/                # Business logic layer
│   │   │   ├── conflict_engine.py   # Rule-based conflict detector
│   │   │   ├── excel_importer.py    # ETL dari Excel
│   │   │   └── excel_exporter.py
│   │   └── core/
│   │       ├── auth.py              # JWT utilities
│   │       └── permissions.py      # RBAC helpers
│   ├── alembic/                     # Database migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── api/                     # API client (Axios/Fetch)
│   │   └── store/                   # State management (Zustand)
│   ├── package.json
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── requirements.md
├── design.md
└── tasks.md
```

---

## 7. Keputusan Desain Kunci

| Keputusan | Pilihan | Alasan |
|-----------|---------|--------|
| UUID sebagai PK | UUID v4 | Aman untuk import data dari berbagai sumber tanpa risiko collision integer |
| Soft delete | Kolom `is_active` | Mempertahankan referential integrity historis |
| Conflict log disimpan di DB | Tabel `conflict_log` | Memungkinkan tracking resolusi dan audit trail |
| `assignment_ids` sebagai array | PostgreSQL `UUID[]` | Satu konflik (misal HC-07) bisa melibatkan >2 assignment sekaligus |
| Timeslot sebagai entitas tetap | 15 slot (3 sesi × 5 hari) | Menyederhanakan conflict detection; konsisten dengan kebijakan jurusan |
| JSONB untuk `conflict_log.detail` | PostgreSQL JSONB | Detail konflik bervariasi per jenis; skema fleksibel |
| Frontend state management | Zustand | Ringan, cukup untuk skala ini; tidak perlu Redux |
| Struktur dosen per assignment | Dua kolom (`dosen1_id`, `dosen2_id`) | Jumlah dosen per kelas tetap (maks 2); lebih efisien dari two-row untuk query join; sesuai format Excel existing |
| Ruang opsional | `ruang_id` NULLABLE | Data ruang dikelola Fakultas; sistem tidak boleh bloking input jadwal hanya karena ruang belum tersedia |
| Strategi ETL data kotor | Tolerant import + warning log | Basis data Excel existing belum rapi (fokus XLOOKUP, bukan normalisasi); importer harus `try/except` per baris dan log baris gagal tanpa membatalkan seluruh import |
| RBAC 5 role | `admin`, `sekretaris_jurusan`, `koordinator_prodi`, `kaprodi`, `dosen` | Mencerminkan struktur organisasi jurusan; `sekretaris_jurusan` dan `koordinator_prodi` memiliki hak edit penuh seperti admin kecuali manajemen user |
| Team teaching order | Tabel terpisah `team_teaching_order` | Tidak semua assignment adalah team teaching; tabel terpisah menghindari kolom NULL di `jadwal_assignment` dan memudahkan query swap UTS |
| Preferensi dosen | Tabel `dosen_preference` dengan kolom `fase` dan `is_violated` | Memisahkan preferensi dari unavailability; mendukung dua fase pengajuan; `is_violated` memungkinkan ringkasan pelanggaran tanpa query kompleks |
