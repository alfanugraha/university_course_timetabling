# Requirements — Sistem Penjadwalan Kuliah
## Jurusan Matematika FMIPA Universitas Riau

**Versi:** 1.6.0  
**Tanggal:** April 2026  
**Status:** Draft  
**Changelog v1.6.0:** Tambah SC-05 — prioritas lantai berdasarkan usia dosen (rule-based dengan opsi override, aktif Fase 1 sebagai WARNING); tambah kolom `tgl_lahir` ke data dosen sebagai basis perhitungan; tambah user story untuk pengelola terkait rekomendasi penempatan ruang.  
**Changelog v1.5.0:** Restrukturisasi role — `kaprodi` diganti `ketua_jurusan`; tambah `tendik_prodi` dan `tendik_jurusan`; §2.6 Team Teaching digabung ke §2.4 Dosen.  
**Changelog v1.4.0:** Revisi §3.4 BKD — HC-04 dikembalikan ke status DEFERRED; ketentuan BKD fase berikutnya diperbarui: minimum 9 SKS, distribusi bertingkat berdasarkan masa kerja.  
**Changelog v1.3.0:** Revisi §2.6 — kewenangan pengaturan urutan team teaching dipindahkan ke Dosen pengampu; revisi HC-04 menjadi guideline minimum 9 SKS; tambah kapasitas ruang default 45 orang.  
**Changelog v1.2.0:** Tambah role `sekretaris_jurusan` dan `koordinator_prodi`; tambah fitur team teaching scheduling; perluas SC-03 preferensi dosen dua fase.

---

## 1. Deskripsi Sistem

Sistem Penjadwalan Kuliah (Course Timetabling System / CTS) adalah aplikasi web berbasis intranet yang menggantikan proses penyusunan jadwal perkuliahan manual berbasis Microsoft Excel di Jurusan Matematika FMIPA Universitas Riau. Sistem mengelola data master (dosen, mata kuliah, ruang, timeslot), mendukung proses penyusunan jadwal secara terstruktur, dan mendeteksi konflik secara otomatis.

Sistem ini adalah **Fase 1** dari kerangka optimisasi yang lebih besar. Pada fase ini, fokus utama adalah **manajemen data dan deteksi konflik**. Fitur optimisasi otomatis (Genetic Algorithm + Constraint Programming) akan diimplementasikan pada fase berikutnya.

---

## 2. Cerita Pengguna (User Stories)

### 2.1 Ketua Jurusan

> Pengguna dengan kewenangan persetujuan akhir terhadap jadwal perkuliahan. Peran utama mencakup evaluasi dan pengesahan jadwal tingkat jurusan. Ketua Jurusan bertindak sebagai otoritas final sebelum jadwal dirilis.

- Sebagai Ketua Jurusan, saya ingin meninjau draft jadwal yang telah disusun dan divalidasi agar saya dapat memastikan jadwal sesuai dengan kebijakan akademik jurusan.
- Sebagai Ketua Jurusan, saya ingin melihat ringkasan konflik dan hasil penyelesaiannya agar informasi ini menjadi dasar dalam pengambilan keputusan.
- Sebagai Ketua Jurusan, saya ingin memberikan persetujuan atau meminta revisi jadwal agar keputusan ini menentukan apakah jadwal siap ditetapkan atau perlu perbaikan.
- Sebagai Ketua Jurusan, saya ingin mengesahkan jadwal sebagai jadwal resmi semester berjalan agar pengesahan dilakukan sebelum jadwal didistribusikan ke seluruh pihak terkait.
- Sebagai Ketua Jurusan, saya ingin melihat rekap beban SKS dosen lintas semua program studi agar keseimbangan beban mengajar dapat dievaluasi sebelum jadwal ditetapkan.

---

### 2.2 Sekretaris Jurusan

> Pengguna dengan hak akses pada pengelolaan jadwal tingkat jurusan tanpa kewenangan akademik. Peran utama mencakup integrasi usulan jadwal dari seluruh program studi. Sekretaris Jurusan bertindak sebagai fasilitator dan validator teknis jadwal.

- Sebagai Sekretaris Jurusan, saya ingin menerima dan menggabungkan usulan jadwal dari setiap program studi agar dihasilkan draft jadwal terintegrasi tingkat jurusan.
- Sebagai Sekretaris Jurusan, saya ingin menyesuaikan jadwal untuk menghindari konflik dosen, ruang, dan waktu tanpa mengubah penetapan dosen pengampu dari Koordinator Prodi.
- Sebagai Sekretaris Jurusan, saya ingin menjalankan deteksi konflik dan meninjau hasilnya agar hasil ini menjadi dasar koordinasi perbaikan dengan program studi terkait.
- Sebagai Sekretaris Jurusan, saya ingin menyiapkan draft final jadwal untuk diajukan ke Ketua Jurusan setelah melalui proses validasi teknis.
- Sebagai Sekretaris Jurusan, saya ingin mengekspor jadwal ke Excel untuk distribusi sebagai acuan resmi setelah disahkan.

---

### 2.3 Koordinator Prodi

> Pengguna dengan akses pada data program studi masing-masing. Peran utama mencakup penetapan dosen pengampu dan penyusunan usulan jadwal. Koordinator Prodi menjadi pengambil keputusan akademik pada tingkat prodi.

**Input Kebutuhan Jadwal**

- Sebagai Koordinator Prodi, saya ingin melihat daftar mata kuliah aktif pada semester berjalan agar informasi ini menjadi dasar penyusunan jadwal perkuliahan.
- Sebagai Koordinator Prodi, saya ingin menetapkan dosen pengampu pada setiap kelas mata kuliah agar penetapan ini menjadi acuan utama dalam proses penjadwalan.
- Sebagai Koordinator Prodi, saya ingin menyusun usulan jadwal mengajar mencakup timeslot, ruang, serta pembagian kelas agar usulan dapat diintegrasikan oleh Sekretaris Jurusan.
- Sebagai Koordinator Prodi, saya ingin mengatur kelas paralel dengan dosen berbeda agar pembagian tugas mengajar jelas.

**Verifikasi Awal**

- Sebagai Koordinator Prodi, saya ingin melakukan pengecekan awal terhadap potensi konflik agar validasi awal membantu mengurangi revisi pada tingkat jurusan.
- Sebagai Koordinator Prodi, saya ingin meninjau beban SKS dosen di program studi saya agar distribusi beban tetap seimbang.

---

### 2.4 Dosen

> Pengguna dengan akses pada data yang berkaitan dengan dirinya sendiri. Termasuk di dalamnya: dosen pengampu tunggal maupun dosen dalam skema team teaching.

**Jadwal dan Informasi Pribadi**

- Sebagai Dosen, saya ingin melihat jadwal mengajar saya untuk semester aktif dalam format yang mudah dibaca (per hari/minggu).
- Sebagai Dosen, saya ingin menginputkan slot waktu yang saya **tidak tersedia** agar jadwal tidak menempatkan saya pada slot tersebut.
- Sebagai Dosen, saya ingin melihat total beban SKS saya pada semester berjalan agar saya dapat memantau kesesuaiannya dengan ketentuan BKD.

**Preferensi Hari Mengajar**

- Sebagai Dosen, saya ingin mengajukan **preferensi hari mengajar** sebelum jadwal disusun (*pre-schedule request*) agar preferensi saya dapat dipertimbangkan saat menyusun jadwal.
- Sebagai Dosen, saya ingin mengajukan **perubahan preferensi hari mengajar** setelah draft jadwal dirilis (*post-draft request*) agar Admin dapat mempertimbangkan penyesuaian jika memungkinkan.
- Sebagai Dosen, saya ingin mengetahui apakah preferensi hari mengajar saya dipenuhi atau tidak agar saya memiliki ekspektasi yang realistis.

**Team Teaching**

> Fitur ini berlaku bagi dosen yang mengampu mata kuliah bersama dosen lain (team teaching). Penentuan urutan masuk kelas menjadi kewenangan dosen pengampu — bukan Admin atau pengelola jurusan. Admin dan pengelola berperan sebagai fasilitator dan viewer.

- Sebagai Dosen pengampu team teaching, saya ingin menentukan urutan masuk kelas pada setiap sesi perkuliahan (misalnya: saya masuk duluan di Kelas A, rekan saya di Kelas B) agar pembagian tugas mengajar awal semester jelas sesuai kesepakatan tim.
- Sebagai Dosen pengampu team teaching, saya ingin mengatur perubahan urutan masuk kelas setelah UTS agar beban mengajar terdistribusi merata sepanjang semester.

---

### 2.5 Tenaga Kependidikan Prodi (Tendik Prodi)

> Pengguna yang berperan sebagai pelaksana teknis pada tingkat program studi. Peran utama mencakup penyusunan draft jadwal berdasarkan arahan Koordinator Prodi. Tendik Prodi bekerja dekat dengan kebutuhan akademik prodi.

**Penyusunan Jadwal**

- Sebagai Tendik Prodi, saya ingin menyusun draft jadwal berdasarkan arahan Koordinator Prodi mencakup penempatan dosen, timeslot, dan kelas.
- Sebagai Tendik Prodi, saya ingin menginput dan memperbarui data jadwal di sistem agar usulan jadwal terdokumentasi dengan baik.
- Sebagai Tendik Prodi, saya ingin melakukan pengecekan awal terhadap potensi konflik agar hasil pengecekan dapat digunakan sebelum jadwal dikirim ke tingkat jurusan.

**Dukungan Prodi**

- Sebagai Tendik Prodi, saya ingin menyiapkan draft jadwal yang siap diintegrasikan sebagai bahan bagi Sekretaris Jurusan.
- Sebagai Tendik Prodi, saya ingin berkoordinasi dengan Koordinator Prodi terkait penyesuaian jadwal agar jadwal tetap sesuai keputusan akademik.

---

### 2.6 Tenaga Kependidikan Jurusan (Tendik Jurusan)

> Pengguna yang berperan sebagai pelaksana teknis pada tingkat jurusan. Peran utama mencakup dukungan integrasi dan penyesuaian jadwal lintas prodi. Tendik Jurusan bekerja bersama Sekretaris Jurusan.

**Integrasi dan Penyesuaian**

- Sebagai Tendik Jurusan, saya ingin membantu proses penggabungan jadwal dari berbagai prodi bersama Sekretaris Jurusan.
- Sebagai Tendik Jurusan, saya ingin membantu penyesuaian jadwal untuk menghindari konflik berdasarkan arahan Sekretaris Jurusan.
- Sebagai Tendik Jurusan, saya ingin menjalankan pengecekan konflik lanjutan agar hasilnya dapat digunakan untuk finalisasi sebelum diajukan ke Ketua Jurusan.

**Dukungan Administratif**

- Sebagai Tendik Jurusan, saya ingin menyiapkan dokumen jadwal hasil integrasi untuk digunakan pada proses persetujuan dan distribusi.
- Sebagai Tendik Jurusan, saya ingin memastikan data jadwal selalu mutakhir sesuai hasil koordinasi lintas prodi.

---

### 2.7 Admin Sistem

> Pengguna dengan akses penuh terhadap seluruh data dan fungsionalitas sistem termasuk manajemen user dan konfigurasi sistem.

- Sebagai Admin Sistem, saya ingin mengelola akun pengguna (buat, ubah role, nonaktifkan) agar hak akses setiap pengguna sesuai dengan jabatannya.
- Sebagai Admin Sistem, saya ingin mengelola data master (dosen, mata kuliah, ruang, timeslot, prodi, kurikulum) agar data sistem selalu akurat.
- Sebagai Admin Sistem, saya ingin mengimpor data dari file Excel agar migrasi data awal dan pembaruan periodik dapat dilakukan dengan efisien.
- Sebagai Admin Sistem, saya ingin mengekspor jadwal ke Excel agar dokumen dapat didistribusikan.
- Sebagai Admin Sistem, saya ingin menjalankan deteksi konflik dan melihat hasilnya agar integritas jadwal dapat dipantau kapan saja.
- Sebagai Admin Sistem, saya ingin melihat rekomendasi penempatan ruang berdasarkan prioritas lantai agar penugasan ruang dapat mempertimbangkan usia dosen pengampu.
- Sebagai Admin Sistem, saya ingin melakukan override rekomendasi prioritas lantai pada kondisi tertentu (keterbatasan ruang, kebutuhan khusus) agar fleksibilitas tetap terjaga.

---

## 3. Aturan Bisnis (Business Rules)

### 3.1 Hard Constraints — Wajib Dipenuhi

Jadwal dinyatakan **tidak valid** jika melanggar salah satu aturan berikut:

| Kode | Aturan | Keterangan | Status Fase 1 |
|------|--------|------------|---------------|
| HC-01 | **No lecturer double-booking** | Satu dosen tidak boleh ditugaskan pada dua atau lebih mata kuliah di timeslot yang sama dalam satu semester. | ✅ Aktif |
| HC-02 | **No room double-booking** | Satu ruang tidak boleh digunakan oleh dua atau lebih mata kuliah di timeslot yang sama. Hanya diperiksa jika `ruang_id` terisi; jika NULL, rule ini dilewati. | ✅ Aktif (kondisional) |
| HC-03 | **Room capacity** | Kapasitas ruang harus ≥ jumlah mahasiswa terdaftar pada kelas tersebut. Kapasitas default ruang adalah **45 orang** jika data kapasitas belum tersedia. | ⏸ Defer — menunggu data jumlah mahasiswa per kelas dari Fakultas |
| HC-04 | **BKD workload** | Distribusi beban mengajar dosen mengikuti ketentuan BKD dengan pola bertingkat berdasarkan masa kerja. | ⏸ Defer — menunggu normalisasi data dosen |
| HC-05 | **Single assignment per class** | Setiap kelas mata kuliah hanya boleh memiliki satu penugasan aktif per sesi jadwal. | ✅ Aktif |
| HC-06 | **Lecturer availability** | Dosen tidak boleh dijadwalkan pada slot waktu yang ia tandai sebagai tidak tersedia. | ✅ Aktif |
| HC-07 | **Parallel class same slot** | Kelas-kelas paralel dari mata kuliah yang sama wajib dijadwalkan pada hari dan timeslot yang sama. | ✅ Aktif |
| HC-08 | **Student daily load** | Mahasiswa pada satu program studi dan semester yang sama tidak boleh memiliki lebih dari **2 mata kuliah** atau lebih dari **6 SKS** dalam satu hari. | ✅ Aktif |
| HC-09 | **Lecturer daily load** | Seorang dosen tidak boleh dijadwalkan mengajar lebih dari **2 mata kuliah** atau lebih dari **6 SKS** dalam satu hari. | ✅ Aktif |

### 3.2 Soft Constraints — Dianjurkan Dipenuhi

Jadwal yang melanggar soft constraints tetap valid namun dianggap **suboptimal**. Sistem mencatat dan melaporkan pelanggaran ini tanpa memblokir penyimpanan.

| Kode | Aturan | Keterangan |
|------|--------|------------|
| SC-01 | **Student program conflict** | Mata kuliah pada semester yang sama dalam satu program studi sebaiknya tidak dijadwalkan pada timeslot yang sama. |
| SC-02 | **Workload equity** | Beban SKS antar dosen dalam satu program studi sebaiknya terdistribusi merata (simpangan baku beban diminimalkan). |
| SC-03 | **Lecturer preference** | Preferensi hari mengajar yang diajukan dosen sebaiknya diprioritaskan. Preferensi bersifat **soft** — tidak wajib dipenuhi. Sistem mencatat setiap preferensi yang dilanggar dan pengelola dapat melihat ringkasan jumlah pelanggaran per sesi. Terdapat dua fase: **(a) Pre-schedule** — sebelum jadwal disusun; **(b) Post-draft** — setelah draft jadwal dirilis. |
| SC-04 | **Room utilization** | Jumlah ruang yang digunakan dalam satu timeslot sebaiknya tidak terlalu jarang agar penggunaan ruang efisien. |
| SC-05 | **Floor priority by lecturer age** | Penempatan ruang kuliah mengikuti prioritas lantai berdasarkan usia dosen. Dosen dengan usia lebih senior diprioritaskan pada lantai yang lebih rendah; dosen yang lebih muda dapat ditempatkan pada lantai yang lebih tinggi. Sistem mengurutkan rekomendasi penugasan ruang berdasarkan usia dosen (`tgl_lahir`) dan memberikan WARNING jika penugasan aktual tidak sesuai urutan prioritas. Override dapat dilakukan oleh pengelola pada kondisi tertentu (keterbatasan ruang, kebutuhan khusus). Hanya diperiksa jika `ruang_id` dan `tgl_lahir` dosen terisi. |
| ~~SC-05~~ | ~~**Parallel class consistency**~~ | *Dipromosikan menjadi HC-07. Tidak berlaku lagi — kode SC-05 kini digunakan untuk floor priority.* |

### 3.3 Aturan Data Master

| Kode | Aturan |
|------|--------|
| DM-01 | Kode mata kuliah bersifat unik per kurikulum. |
| DM-02 | Satu mata kuliah dapat memiliki beberapa kelas paralel; setiap kelas diperlakukan sebagai entitas jadwal yang terpisah. |
| DM-03 | Setiap kelas mata kuliah dapat diampu oleh maksimal **dua dosen** (Dosen I dan Dosen II). Keduanya disimpan sebagai dua kolom terpisah (`dosen1_id`, `dosen2_id`) dalam tabel assignment. Dosen I wajib; Dosen II opsional. Keduanya dihitung beban hariannya masing-masing. |
| DM-04 | Dosen yang berstatus non-aktif tidak dapat ditugaskan pada jadwal baru. |
| DM-05 | Timeslot yang digunakan dalam jadwal mengacu pada daftar timeslot tetap; timeslot ad-hoc di luar daftar tidak diperbolehkan. |
| DM-06 | Setiap sesi jadwal terikat pada satu kombinasi `semester` (Ganjil/Genap) dan `tahun_akademik` (misal: 2025-2026). |
| DM-07 | Mata kuliah layanan (kategori `Layanan`) dicatat dengan program studi penerima, bukan homebase pengampu. |
| DM-08 | Pada mata kuliah team teaching, sistem mencatat **urutan masuk kelas** per dosen per kelas paralel. Pengaturan dilakukan oleh **dosen pengampu** yang bersangkutan. Urutan dapat dipertukarkan setelah UTS. Admin dan pengelola jurusan hanya dapat melihat ringkasan konfigurasi. |
| DM-09 | Preferensi hari mengajar dosen bersifat **soft** — sistem mencatat preferensi tetapi tidak memblokir assignment yang melanggarnya. Sistem menghitung dan menampilkan jumlah preferensi yang dilanggar per sesi jadwal. |

### 3.4 Aturan Beban Kerja Dosen (BKD)

> **Status Fase 1: DEFERRED.** Perhitungan beban kerja semester (BKD) belum diimplementasikan pada fase ini karena struktur data dosen masih dalam proses normalisasi. Kolom `bkd_limit_sks` tersedia di skema tetapi validasinya tidak aktif.

Ketentuan BKD yang akan diberlakukan pada fase berikutnya:
- Beban mengajar mengikuti **ketentuan minimum BKD sebesar 9 SKS** per semester.
- Distribusi SKS bersifat **bertingkat berdasarkan masa kerja dosen**: dosen dengan masa kerja lebih singkat tidak boleh melebihi beban dosen yang lebih senior dalam satu program studi.
- Pengecualian dapat diberikan pada kondisi tertentu oleh tim pengelola jurusan.
- SKS dari mata kuliah layanan (untuk prodi lain) dihitung ke dalam total beban dosen pengampu.
- Sistem memberikan **peringatan** jika urutan beban tidak sesuai pola umum (dosen junior beban lebih besar dari dosen senior).

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
- Fase 1 **tidak** mengimplementasikan optimisasi jadwal otomatis (GA/CP). Jadwal disusun secara manual; sistem hanya mendeteksi konflik.
- Sistem mendukung **satu jurusan aktif** (Jurusan Matematika). Multi-jurusan adalah scope fase berikutnya.
- Notifikasi email/push belum dicakup pada fase ini.
- Sistem tidak terhubung ke PDDIKTI, SIAKAD, atau sistem informasi akademik lainnya pada fase ini.

**Keamanan**
- Autentikasi berbasis username/password dengan JWT.
- Role-based access control (RBAC) dengan tujuh role:

| Role | Kode | Deskripsi Singkat |
|------|------|-------------------|
| Admin Sistem | `admin` | Akses penuh termasuk manajemen user dan konfigurasi sistem |
| Ketua Jurusan | `ketua_jurusan` | Persetujuan dan pengesahan jadwal; akses read + approve |
| Sekretaris Jurusan | `sekretaris_jurusan` | Edit jadwal tingkat jurusan; tanpa manajemen user |
| Koordinator Prodi | `koordinator_prodi` | Edit jadwal tingkat prodi; penetapan dosen pengampu |
| Dosen | `dosen` | Lihat jadwal diri, unavailability, preferensi, team teaching (own) |
| Tendik Prodi | `tendik_prodi` | Edit jadwal tingkat prodi; tanpa kewenangan akademik |
| Tendik Jurusan | `tendik_jurusan` | Edit jadwal tingkat jurusan; tanpa kewenangan akademik |

- Semua endpoint API dilindungi autentikasi kecuali `/auth/login`.
- Password disimpan sebagai hash bcrypt; tidak ada plain-text password di database.

**Data**
- Format import Excel mengacu pada template yang telah ada (`db.xlsx`, `db_mata_kuliah.xlsx`).
- Data historis (5 semester: Genap 2023–24 s.d. Genap 2025–26) diimpor sebagai **read-only archive** untuk referensi.
- Kapasitas data yang diperkirakan: ~600 kelas mata kuliah, ~50 dosen, **15 timeslot** (3 sesi × 5 hari), 9 ruang per semester.
- Tiga sesi perkuliahan tetap per hari: **07:30–10:00**, **10:00–12:30**, **13:00–15:30** (masing-masing setara 3 SKS).
- Data dosen saat ini belum diinput secara lengkap; ETL importer harus toleran terhadap baris dosen yang kosong atau tidak konsisten.
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

1. Admin Sistem dapat melakukan CRUD lengkap untuk semua entitas data master (dosen, mata kuliah, ruang, timeslot, prodi, kurikulum) dan manajemen user.
2. Sekretaris Jurusan, Koordinator Prodi, Tendik Prodi, dan Tendik Jurusan dapat membuat dan mengedit penugasan (assignment) jadwal sesuai cakupan aksesnya.
3. Sistem mendeteksi dan melaporkan konflik HC-01, HC-02 (jika ruang terisi), HC-05, HC-06, HC-07, HC-08, HC-09 dengan informasi yang cukup untuk tindak lanjut (siapa, hari apa, jam berapa, kelas mana).
4. Sistem menampilkan rekapitulasi beban mengajar harian dan per-sesi untuk tiap dosen (validasi BKD semester penuh akan aktif di fase berikutnya).
5. Import Excel dari file `db.xlsx` dan jadwal semester sebelumnya berhasil tanpa data corrupt.
6. Export jadwal ke Excel menghasilkan file yang dapat dibuka dan terbaca dengan benar.
7. Ketua Jurusan dapat meninjau draft jadwal, melihat ringkasan konflik, dan mengesahkan jadwal sebagai jadwal resmi.
8. Koordinator Prodi dapat menetapkan dosen pengampu dan menyusun usulan jadwal untuk program studinya.
9. Dosen dapat melihat jadwal dirinya, menginput unavailability, mengajukan preferensi hari mengajar (pre-schedule dan post-draft), serta mengatur urutan masuk kelas untuk mata kuliah team teaching yang ia ampu.
10. Sistem mencatat preferensi dosen yang dilanggar dan pengelola dapat melihat ringkasan jumlah pelanggaran preferensi per sesi.
11. Sistem menampilkan notifikasi konflik (in-app) saat konflik terdeteksi; tidak ada fitur auto-resolve pada fase ini.
12. Sistem menampilkan WARNING SC-05 jika penugasan ruang tidak sesuai prioritas lantai berdasarkan usia dosen, dan pengelola dapat melakukan override.
13. Seluruh endpoint API mengembalikan respons error yang jelas (kode HTTP, pesan) untuk input tidak valid.
14. Sistem berjalan stabil di lingkungan Docker Compose dengan PostgreSQL.
