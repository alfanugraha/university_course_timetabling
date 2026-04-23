---
inclusion: always
---

# Product Overview — Sistem Penjadwalan Kuliah (CTS)
## Jurusan Matematika FMIPA Universitas Riau

## Apa Sistem Ini

Course Timetabling System (CTS) adalah aplikasi web intranet yang menggantikan proses penyusunan jadwal perkuliahan manual berbasis Excel di Jurusan Matematika FMIPA UNRI. Sistem ini adalah **Fase 1** dari kerangka yang lebih besar — fokusnya adalah manajemen data dan deteksi konflik, bukan optimisasi otomatis.

## Pengguna dan Hak Akses

| Role | Kode | Kemampuan |
|------|------|-----------|
| Admin Sistem | `admin` | Akses penuh: semua data, jadwal, manajemen user, konfigurasi sistem |
| Ketua Jurusan | `ketua_jurusan` | Read-only + approve/sahkan jadwal; otoritas final sebelum jadwal dirilis |
| Sekretaris Jurusan | `sekretaris_jurusan` | Edit jadwal tingkat jurusan; tanpa manajemen user |
| Koordinator Prodi | `koordinator_prodi` | Edit jadwal prodi sendiri; penetapan dosen pengampu |
| Tendik Jurusan | `tendik_jurusan` | Edit jadwal tingkat jurusan; tanpa kewenangan akademik |
| Tendik Prodi | `tendik_prodi` | Edit jadwal prodi sendiri; tanpa kewenangan akademik |
| Dosen | `dosen` | Lihat jadwal diri, unavailability, preferensi, team teaching (own) |

Konstanta RBAC:
```python
EDITOR_ROLES_JURUSAN = ["admin", "sekretaris_jurusan", "tendik_jurusan"]
EDITOR_ROLES_PRODI   = ["admin", "sekretaris_jurusan", "tendik_jurusan",
                         "koordinator_prodi", "tendik_prodi"]
VIEWER_ROLES         = ["ketua_jurusan"]
```

## Fitur Utama Fase 1

### 1. Manajemen Data Master
CRUD untuk: Prodi, Kurikulum, Mata Kuliah, Kelas Paralel, Dosen, Ruang (opsional), Timeslot (15 slot tetap).

### 2. Penjadwalan Manual
- Sesi jadwal per semester/tahun akademik (status: Draft → Aktif → Arsip)
- Assignment: kombinasi (kelas MK, dosen1, dosen2 opsional, timeslot, ruang opsional)
- Import dari Excel historis sebagai titik awal
- Export ke Excel format standar jurusan

### 3. Deteksi Konflik (Rule-Based Engine)

**Hard Constraints (ERROR — memblokir validasi):**
- HC-01: Dosen double-booking di timeslot yang sama
- HC-02: Ruang double-booking (hanya jika ruang_id terisi)
- HC-05: Satu kelas MK hanya boleh satu assignment per sesi
- HC-06: Dosen dijadwalkan di slot yang ia tandai tidak tersedia
- HC-07: Kelas paralel (A/B/C) dari MK yang sama wajib di timeslot yang sama
- HC-08: Mahasiswa satu prodi+semester maks 2 MK atau 6 SKS per hari
- HC-09: Dosen maks 2 MK atau 6 SKS per hari

**Soft Constraints (WARNING — informatif, tidak memblokir):**
- SC-01: MK satu semester satu prodi dijadwalkan bersamaan
- SC-02: Distribusi beban SKS antar dosen tidak merata
- SC-03: Preferensi hari mengajar dosen dilanggar

**Deferred ke Fase 2:** HC-03 (kapasitas ruang), HC-04 (BKD ceiling semester)

### 4. Team Teaching
Untuk MK yang diampu dua dosen: atur urutan masuk kelas (siapa duluan di Kelas A, siapa di Kelas B), dan jadwalkan pertukaran setelah UTS.

### 5. Preferensi Dosen
Dosen dapat mengajukan preferensi hari mengajar dalam dua fase:
- **Pre-schedule**: sebelum jadwal disusun
- **Post-draft**: setelah draft jadwal dirilis

Preferensi bersifat **soft** — tidak wajib dipenuhi. Sistem mencatat `is_violated` dan Admin dapat melihat ringkasan pelanggaran per sesi.

### 6. Laporan
- Rekap beban SKS per dosen (breakdown per prodi)
- Peta penggunaan ruang (matrix hari × slot × ruang)
- Ringkasan pelanggaran preferensi dosen

## Batasan Fase 1

- Tidak ada optimisasi otomatis (GA/CP-SAT) — jadwal disusun manual
- Tidak ada notifikasi email/push — konflik hanya ditampilkan in-app
- Tidak terhubung ke SIAKAD/PDDIKTI — sinkronisasi via import Excel
- Hanya satu jurusan aktif (Jurusan Matematika)
- Data ruang belum diwajibkan (dikelola Fakultas)
- BKD semester penuh belum aktif (data dosen belum dinormalisasi)

## Data yang Dikelola

- ~600 kelas mata kuliah, ~50 dosen, 15 timeslot tetap, 9 ruang per semester
- 3 sesi tetap per hari: 07:30–10:00, 10:00–12:30, 13:00–15:30 (masing-masing 3 SKS)
- 5 semester historis tersedia sebagai arsip read-only
- Sumber data awal: `db.xlsx` (master) dan `db_mata_kuliah.xlsx` (kelas)

## Spec Files

Spec lengkap tersedia di `.kiro/specs/timetabling/`:
- `requirements.md` — user stories, business rules, acceptance criteria
- `design.md` — arsitektur, skema DB, API endpoints, UI flow
- `tasks.md` — implementation tasks per fase (Fase 0–9)
