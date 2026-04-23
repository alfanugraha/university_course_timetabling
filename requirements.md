# Requirements — Sistem Penjadwalan Kuliah
## Jurusan Matematika FMIPA Universitas Riau

**Versi:** 1.2.0  
**Tanggal:** April 2026  
**Status:** Draft  
**Changelog v1.2.0:** Tambah role `sekretaris_jurusan` dan `koordinator_prodi` ke RBAC; tambah fitur team teaching scheduling (urutan masuk kelas A/B, pertukaran setelah UTS); perluas SC-03 (preferensi dosen) menjadi dua fase (pre-schedule dan post-draft) dengan sifat soft dan pencatatan pelanggaran; tambah notifikasi konflik (in-app, tanpa auto-resolve).  
**Changelog v1.1.0:** Tambah HC-07 (paralel kelas), HC-08 (beban harian mahasiswa), HC-09 (beban harian dosen); HC-03 & HC-04 defer ke Fase berikutnya; ruang dijadikan opsional; timeslot direvisi menjadi 3 sesi tetap per hari; keputusan struktur dosen (dua kolom); SC-05 dipromosikan ke HC-07.

---

## 1. Deskripsi Sistem

Sistem Penjadwalan Kuliah (Course Timetabling System / CTS) adalah aplikasi web berbasis intranet yang menggantikan proses penyusunan jadwal perkuliahan manual berbasis Microsoft Excel di Jurusan Matematika FMIPA Universitas Riau. Sistem mengelola data master (dosen, mata kuliah, ruang, timeslot), mendukung proses penyusunan jadwal secara terstruktur, dan mendeteksi konflik secara otomatis.

Sistem ini adalah **Fase 1** dari kerangka optimisasi yang lebih besar. Pada fase ini, fokus utama adalah **manajemen data dan deteksi konflik**. Fitur optimisasi otomatis (Genetic Algorithm + Constraint Programming) akan diimplementasikan pada fase berikutnya.

---

## 2. Cerita Pengguna (User Stories)

### 2.1 Admin Jurusan

> Pengguna dengan akses penuh terhadap seluruh data dan fungsionalitas sistem. Termasuk dalam kelompok ini: **Admin Jurusan**, **Sekretaris Jurusan**, dan **Koordinator Prodi** — ketiganya memiliki hak input/edit semua data jadwal.

**Manajemen Data Master**

- Sebagai Admin Jurusan, saya ingin menambahkan, mengubah, dan menonaktifkan data dosen agar sistem selalu mencerminkan daftar pengajar aktif.
- Sebagai Admin Jurusan, saya ingin mengelola daftar program studi dan kurikulum (K2021, K2025) agar mata kuliah dapat dikaitkan dengan program yang tepat.
- Sebagai Admin Jurusan, saya ingin mengelola daftar mata kuliah beserta atributnya (kode, SKS, semester, jenis, prasyarat, kelas paralel A/B/C) agar data kurikulum tersedia lengkap.
- Sebagai Admin Jurusan, saya ingin mengelola daftar ruang kuliah beserta kapasitasnya agar penugasan ruang dapat dikontrol *(opsional — data ruang dikelola oleh pihak Fakultas; fitur ini tersedia di sistem tetapi tidak diwajibkan pada Fase 1)*.
- Sebagai Admin Jurusan, saya ingin mengelola slot waktu standar (timeslot) agar semua jadwal menggunakan slot yang konsisten.

**Pengelolaan Jadwal**

- Sebagai Admin Jurusan, saya ingin membuat sesi jadwal baru per semester/tahun akademik (misalnya: Genap 2025–2026) agar setiap siklus semester tersimpan terpisah.
- Sebagai Admin Jurusan, saya ingin mengimpor data jadwal dari file Excel semester sebelumnya sebagai titik awal penyusunan agar tidak perlu input ulang dari nol.
- Sebagai Admin Jurusan, saya ingin menugaskan kombinasi (kelas mata kuliah, dosen, timeslot) pada satu baris jadwal secara manual; penugasan ruang bersifat opsional dan dapat diisi belakangan.
- Sebagai Admin Jurusan, saya ingin mengubah atau menghapus baris jadwal yang sudah ada.
- Sebagai Admin Jurusan, saya ingin mengekspor jadwal aktif ke format Excel (.xlsx) dengan format yang sesuai standar jurusan.

**Deteksi Konflik**

- Sebagai Admin Jurusan, saya ingin menjalankan pemeriksaan konflik terhadap jadwal aktif dan melihat daftar konflik yang ditemukan secara detail.
- Sebagai Admin Jurusan, saya ingin melihat konflik yang dikelompokkan berdasarkan jenisnya (dosen bentrok, ruang bentrok, konflik prodi) agar prioritas perbaikan jelas.
- Sebagai Admin Jurusan, saya ingin melihat ringkasan beban SKS per dosen agar distribusi beban mengajar dapat dipantau sebelum jadwal ditetapkan.

**Laporan**

- Sebagai Admin Jurusan, saya ingin melihat rekap beban SKS per dosen lintas semua program studi (S1 MTK, S1 STK, S2 MTK, Layanan) agar keseimbangan beban dapat dievaluasi.
- Sebagai Admin Jurusan, saya ingin melihat peta penggunaan ruang per hari/slot agar ruang yang kosong dan yang bentrok dapat diidentifikasi dengan cepat.

---

### 2.2 Sekretaris Jurusan

> Pengguna dengan hak akses setara Admin Jurusan untuk input dan edit data jadwal, namun tanpa akses ke manajemen user dan konfigurasi sistem.

- Sebagai Sekretaris Jurusan, saya ingin mengelola data master (dosen, mata kuliah, ruang, timeslot) agar data selalu mutakhir.
- Sebagai Sekretaris Jurusan, saya ingin membuat dan mengedit penugasan jadwal (assignment) pada sesi aktif agar proses penyusunan jadwal dapat dilakukan tanpa bergantung pada Admin.
- Sebagai Sekretaris Jurusan, saya ingin menjalankan deteksi konflik dan melihat hasilnya agar konflik dapat diidentifikasi dan dilaporkan ke Admin.
- Sebagai Sekretaris Jurusan, saya ingin mengekspor jadwal ke Excel agar dokumen jadwal dapat didistribusikan ke pihak terkait.

---

### 2.3 Koordinator Prodi

> Pengguna dengan hak akses setara Admin Jurusan untuk input dan edit data jadwal, namun fokus pada program studi yang dikoordinasikannya.

- Sebagai Koordinator Prodi, saya ingin mengelola penugasan jadwal untuk semua program studi agar koordinasi lintas prodi dapat dilakukan.
- Sebagai Koordinator Prodi, saya ingin melihat dan mengedit data dosen, mata kuliah, dan timeslot agar penyusunan jadwal dapat dilakukan secara mandiri.
- Sebagai Koordinator Prodi, saya ingin menjalankan deteksi konflik dan melihat hasilnya agar jadwal yang disusun bebas dari konflik sebelum ditetapkan.
- Sebagai Koordinator Prodi, saya ingin mengekspor jadwal ke Excel agar dokumen jadwal dapat didistribusikan.

---

### 2.4 Kaprodi

> Pengguna dengan akses terbatas pada data program studinya sendiri.

**Input Kebutuhan Jadwal**

- Sebagai Kaprodi, saya ingin melihat daftar mata kuliah aktif di program studi saya pada semester berjalan agar saya tahu apa yang perlu dijadwalkan.
- Sebagai Kaprodi, saya ingin mengusulkan penugasan dosen pengampu untuk setiap kelas mata kuliah di program studi saya agar jurusan dapat menyetujui atau merevisi.
- Sebagai Kaprodi, saya ingin menandai mata kuliah yang memiliki kelas paralel (A, B, C) dengan dosen yang berbeda agar penugasan tiap kelas tercatat terpisah.

**Verifikasi Jadwal**

- Sebagai Kaprodi, saya ingin melihat draft jadwal untuk program studi saya agar saya dapat memverifikasi kesesuaiannya sebelum jadwal ditetapkan.
- Sebagai Kaprodi, saya ingin melihat konflik yang melibatkan mata kuliah di program studi saya (khususnya konflik antar mata kuliah satu semester) agar saya dapat meminta perbaikan.
- Sebagai Kaprodi, saya ingin melihat rekap beban SKS dosen homebase program studi saya agar keseimbangan beban mengajar terpantau.

---

### 2.5 Dosen

> Pengguna dengan akses hanya pada data yang berkaitan dengan dirinya sendiri.

**Preferensi dan Informasi Pribadi**

- Sebagai Dosen, saya ingin melihat jadwal mengajar saya untuk semester aktif dalam format yang mudah dibaca (per hari/minggu).
- Sebagai Dosen, saya ingin menginputkan slot waktu yang saya **tidak tersedia** (misalnya: ada kegiatan tetap di luar kampus) agar jadwal tidak menempatkan saya pada slot tersebut.
- Sebagai Dosen, saya ingin melihat total beban SKS saya pada semester berjalan agar saya dapat memantau kesesuaiannya dengan batas BKD.
- Sebagai Dosen, saya ingin mengajukan **preferensi hari mengajar** sebelum jadwal disusun (*pre-schedule request*) agar preferensi saya dapat dipertimbangkan oleh Admin saat menyusun jadwal.
- Sebagai Dosen, saya ingin mengajukan **perubahan preferensi hari mengajar** setelah draft jadwal dirilis (*post-draft request*) agar Admin dapat mempertimbangkan penyesuaian jika memungkinkan.
- Sebagai Dosen, saya ingin mengetahui apakah preferensi hari mengajar saya dipenuhi atau tidak dalam jadwal yang ditetapkan, agar saya memiliki ekspektasi yang realistis.

---

### 2.6 Team Teaching Scheduling

> Fitur khusus untuk mata kuliah yang diampu oleh dua dosen (team teaching). Admin/Sekretaris/Koordinator dapat mengatur urutan masuk kelas dan pertukaran jadwal setelah UTS.

- Sebagai Admin Jurusan, saya ingin menentukan urutan masuk kelas untuk setiap dosen pada mata kuliah team teaching (misalnya: Dosen A masuk duluan di Kelas A, Dosen B masuk duluan di Kelas B) agar pembagian tugas mengajar awal semester jelas.
- Sebagai Admin Jurusan, saya ingin menjadwalkan pertukaran urutan masuk kelas setelah UTS (misalnya: Dosen A pindah ke Kelas B, Dosen B pindah ke Kelas A) agar beban mengajar terdistribusi merata sepanjang semester.
- Sebagai Admin Jurusan, saya ingin melihat ringkasan pengaturan team teaching per sesi jadwal agar saya dapat memverifikasi pembagian tugas sebelum jadwal ditetapkan.

---

## 3. Aturan Bisnis (Business Rules)

### 3.1 Hard Constraints — Wajib Dipenuhi

Jadwal dinyatakan **tidak valid** jika melanggar salah satu aturan berikut:

| Kode | Aturan | Keterangan | Status Fase 1 |
|------|--------|------------|---------------|
| HC-01 | **No lecturer double-booking** | Satu dosen tidak boleh ditugaskan pada dua atau lebih mata kuliah di timeslot yang sama dalam satu semester. | ✅ Aktif |
| HC-02 | **No room double-booking** | Satu ruang tidak boleh digunakan oleh dua atau lebih mata kuliah di timeslot yang sama. Hanya diperiksa jika `ruang_id` terisi; jika NULL (belum ditentukan), rule ini dilewati. | ✅ Aktif (kondisional) |
| HC-03 | **Room capacity** | Kapasitas ruang harus ≥ jumlah mahasiswa terdaftar pada kelas tersebut. | ⏸ Defer — menunggu data kapasitas ruang dari Fakultas |
| HC-04 | **BKD workload ceiling** | Total SKS yang diampu seorang dosen dalam satu semester tidak boleh melebihi batas BKD (default: 16 SKS). | ⏸ Defer — menunggu normalisasi data dosen |
| HC-05 | **Single assignment per class** | Setiap kelas mata kuliah hanya boleh memiliki satu penugasan aktif per sesi jadwal. | ✅ Aktif |
| HC-06 | **Lecturer availability** | Dosen tidak boleh dijadwalkan pada slot waktu yang ia tandai sebagai tidak tersedia. | ✅ Aktif |
| HC-07 | **Parallel class same slot** | Kelas-kelas paralel dari mata kuliah yang sama (misal: Kalkulus I A, B, C) **wajib** dijadwalkan pada hari dan timeslot yang **sama**. Jika salah satu kelas berbeda slot dari lainnya, seluruh kelompok paralel dinyatakan konflik. | ✅ Aktif |
| HC-08 | **Student daily load** | Mahasiswa pada satu program studi dan semester yang sama tidak boleh memiliki lebih dari **2 mata kuliah** atau lebih dari **6 SKS** yang dijadwalkan dalam satu hari. | ✅ Aktif |
| HC-09 | **Lecturer daily load** | Seorang dosen tidak boleh dijadwalkan mengajar lebih dari **2 mata kuliah** atau lebih dari **6 SKS** dalam satu hari. | ✅ Aktif |

### 3.2 Soft Constraints — Dianjurkan Dipenuhi

Jadwal yang melanggar soft constraints tetap valid namun dianggap **suboptimal**. Sistem mencatat dan melaporkan pelanggaran ini tanpa memblokir penyimpanan.

| Kode | Aturan | Keterangan |
|------|--------|------------|
| SC-01 | **Student program conflict** | Mata kuliah pada semester yang sama dalam satu program studi sebaiknya tidak dijadwalkan pada timeslot yang sama, agar mahasiswa dapat mengikuti semua mata kuliah wajib. |
| SC-02 | **Workload equity** | Beban SKS antar dosen dalam satu program studi sebaiknya terdistribusi merata (simpangan baku beban diminimalkan). |
| SC-03 | **Lecturer preference** | Preferensi hari mengajar yang diajukan dosen sebaiknya diprioritaskan saat menyusun jadwal. Preferensi bersifat **soft** — tidak wajib dipenuhi. Sistem mencatat setiap preferensi yang dilanggar dan Admin dapat melihat ringkasan jumlah pelanggaran preferensi per sesi. Terdapat dua fase pengajuan: **(a) Pre-schedule request** — dosen mengajukan preferensi sebelum jadwal disusun; Admin melihat semua preferensi aktif saat membuat assignment. **(b) Post-draft request** — dosen mengajukan perubahan preferensi setelah draft jadwal dirilis; Admin mempertimbangkan penyesuaian secara manual. Sistem menandai preferensi yang dilanggar pada kedua fase. |
| SC-04 | **Room utilization** | Jumlah ruang yang digunakan dalam satu timeslot sebaiknya tidak terlalu jarang agar penggunaan ruang efisien. |
| SC-05 | ~~**Parallel class consistency**~~ | *Dipromosikan menjadi HC-07. Tidak berlaku lagi sebagai soft constraint.* |

### 3.3 Aturan Data Master

| Kode | Aturan |
|------|--------|
| DM-01 | Kode mata kuliah bersifat unik per kurikulum. |
| DM-02 | Satu mata kuliah dapat memiliki beberapa kelas paralel; setiap kelas diperlakukan sebagai entitas jadwal yang terpisah. |
| DM-03 | Setiap kelas mata kuliah dapat diampu oleh maksimal **dua dosen** (Dosen I dan Dosen II). Keduanya disimpan sebagai dua kolom terpisah (`dosen1_id`, `dosen2_id`) dalam tabel assignment — bukan dua baris. Dosen I wajib; Dosen II opsional. Keduanya dihitung beban hariannya masing-masing. |
| DM-04 | Dosen yang berstatus non-aktif tidak dapat ditugaskan pada jadwal baru. |
| DM-05 | Timeslot yang digunakan dalam jadwal mengacu pada `db_timeslot`; timeslot ad-hoc di luar daftar tidak diperbolehkan. |
| DM-06 | Setiap sesi jadwal terikat pada satu kombinasi `semester` (Ganjil/Genap) dan `tahun_akademik` (misal: 2025-2026). |
| DM-07 | Mata kuliah layanan (kategori `Layanan`) dicatat dengan program studi penerima, bukan homebase pengampu. |
| DM-08 | Pada mata kuliah team teaching, sistem mencatat **urutan masuk kelas** per dosen per kelas paralel: siapa yang masuk duluan di Kelas A dan siapa yang masuk duluan di Kelas B. Urutan ini dapat dipertukarkan setelah UTS melalui fitur *team teaching schedule swap*. |
| DM-09 | Preferensi hari mengajar dosen bersifat **soft** — sistem mencatat preferensi tetapi tidak memblokir assignment yang melanggarnya. Sistem menghitung dan menampilkan jumlah preferensi yang dilanggar per sesi jadwal. |

### 3.4 Aturan Beban Kerja Dosen (BKD)

> **Status Fase 1: DEFERRED.** Perhitungan beban kerja semester (BKD) belum diimplementasikan pada fase ini karena struktur data dosen masih dalam proses normalisasi. Kolom `bkd_limit_sks` tersedia di skema tetapi validasinya tidak aktif.

Ketentuan BKD yang akan diberlakukan pada fase berikutnya:
- Batas default BKD adalah **maksimum 16 SKS per semester** untuk dosen tetap penuh waktu.
- Dosen dengan jabatan fungsional Guru Besar dapat dikonfigurasi dengan batas berbeda per dosen.
- SKS dari mata kuliah layanan (untuk prodi lain) dihitung ke dalam total beban dosen pengampu.
- Sistem akan memperingatkan (warning) jika total SKS dosen melebihi **12 SKS** dan memblokir (error) jika melebihi **16 SKS** (HC-04).

**Catatan Fase 1:** Batasan beban *harian* (HC-09: maks 2 MK atau 6 SKS per hari) tetap aktif dan tidak bergantung pada normalisasi data BKD.

---

## 4. Teknologi dan Batasan Sistem

### 4.1 Stack Teknologi

| Komponen | Teknologi | Versi Minimum |
|----------|-----------|---------------|
| Backend API | Python / FastAPI | Python 3.11, FastAPI 0.110 |
| ORM | SQLAlchemy | 2.0 |
| Database Migration | Alembic | 1.13 |
| Database | PostgreSQL | 15 |
| Frontend | React + TypeScript | React 18, Node 20 |
| UI Component | Tailwind CSS + shadcn/ui | Tailwind 3 |
| Excel Import/Export | openpyxl + pandas | openpyxl 3.1 |
| Conflict Engine | Python murni (rule-based) | — |
| Containerization | Docker + Docker Compose | Docker 24 |
| Authentication | JWT (stateless) + bcrypt | — |

### 4.2 Batasan Sistem (Constraints)

**Infrastruktur**
- Sistem di-deploy pada server intranet kampus FMIPA UNRI.
- Akses hanya melalui jaringan lokal kampus (atau VPN jika diakses dari luar).
- Server minimal: 2 vCPU, 2 GB RAM, 20 GB storage.

**Fungsional**
- Fase 1 **tidak** mengimplementasikan optimisasi jadwal otomatis (GA/CP). Jadwal disusun secara manual oleh Admin/Kaprodi; sistem hanya mendeteksi konflik.
- Sistem mendukung **satu jurusan aktif** (Jurusan Matematika). Multi-jurusan adalah scope fase berikutnya.
- Notifikasi email/push belum dicakup pada fase ini.
- Sistem tidak terhubung ke PDDIKTI, SIAKAD, atau sistem informasi akademik lainnya pada fase ini. Sinkronisasi data dilakukan melalui import Excel.

**Keamanan**
- Autentikasi berbasis username/password dengan JWT.
- Role-based access control (RBAC) dengan lima role: `admin`, `sekretaris_jurusan`, `koordinator_prodi`, `kaprodi`, `dosen`.
  - `admin`, `sekretaris_jurusan`, `koordinator_prodi`: dapat input/edit semua data jadwal dan data master.
  - `admin`: tambahan akses ke manajemen user dan konfigurasi sistem.
  - `kaprodi`: akses terbatas hanya pada data program studinya sendiri (read + usulan assignment).
  - `dosen`: hanya dapat melihat jadwal dirinya sendiri, input unavailability, dan mengajukan preferensi hari.
- Semua endpoint API dilindungi autentikasi kecuali `/auth/login`.
- Password disimpan sebagai hash bcrypt; tidak ada plain-text password di database.

**Data**
- Format import Excel mengacu pada template yang telah ada (`db.xlsx`, `db_mata_kuliah.xlsx`).
- Data historis (5 semester: Genap 2023–24 s.d. Genap 2025–26) diimpor sebagai **read-only archive** untuk referensi.
- Kapasitas data yang diperkirakan: ~600 kelas mata kuliah, ~50 dosen, ~600 mahasiswa, **15 timeslot** (3 sesi × 5 hari), 9 ruang per semester.
- Tiga sesi perkuliahan tetap per hari: **07:30–10:00**, **10:00–12:30**, **13:00–15:30** (masing-masing setara 3 SKS). Tidak ada slot waktu ad-hoc di luar ketiga sesi ini.
- Data dosen saat ini belum diinput secara lengkap; ETL importer harus toleran terhadap baris dosen yang kosong atau tidak konsisten dan mencatatnya sebagai warning (bukan error fatal).
- Data ruang **belum diwajibkan**; kolom ruang pada tabel assignment bernilai NULL hingga Fakultas menyerahkan data alokasi ruang.

### 4.3 Antarmuka Eksternal

| Antarmuka | Arah | Format | Keterangan |
|-----------|------|--------|------------|
| Import jadwal Excel | Masuk | `.xlsx` | Template sesuai format existing |
| Export jadwal | Keluar | `.xlsx` | Format standar jurusan |
| Import data master | Masuk | `.xlsx` | `db.xlsx`, `db_mata_kuliah.xlsx` |

---

## 5. Kriteria Penerimaan (Acceptance Criteria)

Sistem dinyatakan siap digunakan pada fase ini apabila:

1. Admin dapat melakukan CRUD lengkap untuk semua entitas data master (dosen, mata kuliah, ruang, timeslot, prodi, kurikulum).
2. Admin dapat membuat sesi jadwal baru dan menambahkan penugasan (assignment) secara manual.
3. Sistem mendeteksi dan melaporkan konflik HC-01, HC-02 (jika ruang terisi), HC-05, HC-06, HC-07, HC-08, HC-09 dengan informasi yang cukup untuk tindak lanjut (siapa, hari apa, jam berapa, kelas mana).
4. Sistem menampilkan rekapitulasi beban mengajar harian dan per-sesi untuk tiap dosen (BKD semester penuh akan aktif di fase berikutnya).
5. Import Excel dari file `db.xlsx` dan jadwal semester sebelumnya berhasil tanpa data corrupt.
6. Export jadwal ke Excel menghasilkan file yang dapat dibuka dan terbaca dengan benar.
7. Pengguna dengan role `admin`, `sekretaris_jurusan`, dan `koordinator_prodi` dapat input/edit semua data jadwal. Pengguna dengan role `kaprodi` hanya dapat melihat dan mengusulkan data yang relevan dengan program studinya. Pengguna dengan role `dosen` hanya dapat melihat jadwal dan data dirinya sendiri.
8. Dosen dapat menginput unavailability dan mengajukan preferensi hari mengajar (pre-schedule dan post-draft).
9. Sistem mencatat preferensi dosen yang dilanggar dan Admin dapat melihat ringkasan jumlah pelanggaran preferensi per sesi.
10. Admin dapat mengatur urutan masuk kelas untuk mata kuliah team teaching dan menjadwalkan pertukaran urutan setelah UTS.
11. Sistem menampilkan notifikasi konflik (in-app) saat konflik terdeteksi; tidak ada fitur auto-resolve pada fase ini.
12. Seluruh endpoint API mengembalikan respons error yang jelas (kode HTTP, pesan) untuk input tidak valid.
13. Sistem berjalan stabil di lingkungan Docker Compose dengan PostgreSQL.
