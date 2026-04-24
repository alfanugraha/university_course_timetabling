# Panduan Instalasi, Backup, dan Update
## Sistem Penjadwalan Kuliah (CTS) — Jurusan Matematika FMIPA Universitas Riau

---

## Daftar Isi

1. [Cara Instalasi](#1-cara-instalasi)
2. [Cara Backup Database PostgreSQL](#2-cara-backup-database-postgresql)
3. [Cara Update Versi](#3-cara-update-versi)

---

## 1. Cara Instalasi

### 1.1 Prasyarat

Pastikan server sudah terinstal perangkat lunak berikut sebelum memulai:

| Perangkat Lunak | Versi Minimum | Cara Cek |
|-----------------|---------------|----------|
| Docker | 24.0 | `docker --version` |
| Docker Compose | 2.20 (plugin) | `docker compose version` |
| Git | 2.x | `git --version` |

> **Catatan:** Docker Compose v2 sudah termasuk dalam instalasi Docker Desktop dan Docker Engine terbaru sebagai plugin (`docker compose`). Jika masih menggunakan versi lama (`docker-compose` dengan tanda hubung), perbarui Docker terlebih dahulu.

Untuk menginstal Docker di Ubuntu/Debian:

```bash
# Instal Docker Engine
curl -fsSL https://get.docker.com | sh

# Tambahkan user ke grup docker (agar tidak perlu sudo)
sudo usermod -aG docker $USER

# Logout dan login kembali, lalu verifikasi
docker --version
docker compose version
```

### 1.2 Clone Repository

```bash
# Clone repository ke server
git clone <URL_REPOSITORY> cts
cd cts
```

Ganti `<URL_REPOSITORY>` dengan URL repository Git yang diberikan oleh tim pengembang.

### 1.3 Konfigurasi Environment Variables

Salin file template environment dan sesuaikan nilainya:

```bash
cp backend/.env.example .env
```

Buka file `.env` dengan editor teks:

```bash
nano .env
```

Isi nilai-nilai berikut:

```dotenv
# URL koneksi ke database PostgreSQL (jangan ubah nama host "db")
DATABASE_URL=postgresql://cts_user:cts_password@db:5432/cts

# Kunci rahasia untuk JWT — WAJIB diganti dengan string acak yang panjang
SECRET_KEY=ganti-dengan-string-acak-yang-sangat-panjang-dan-aman

# Daftar origin yang diizinkan untuk CORS (pisahkan dengan koma)
# Ganti dengan IP atau hostname server intranet Anda
CORS_ORIGINS=http://localhost,http://192.168.1.100
```

> **Penting:** Nilai `SECRET_KEY` harus diganti dengan string acak yang kuat. Gunakan perintah berikut untuk membuat kunci acak:
> ```bash
> openssl rand -hex 32
> ```

### 1.4 Build dan Jalankan Aplikasi

```bash
# Build semua image dan jalankan semua service
docker compose up --build -d
```

Proses build pertama kali membutuhkan waktu beberapa menit karena mengunduh base image dan menginstal dependensi. Perintah `-d` menjalankan container di background.

Pantau proses startup:

```bash
docker compose logs -f
```

Tekan `Ctrl+C` untuk berhenti memantau log (container tetap berjalan).

### 1.5 Inisialisasi Pertama Kali (First-Run)

Saat container `api` pertama kali berjalan, script `init.sh` akan otomatis:

1. Menunggu database PostgreSQL siap
2. Menjalankan migrasi database (`alembic upgrade head`)
3. Mengisi data awal (seed): 15 timeslot tetap dan akun admin default
4. Menjalankan server API

Pantau proses ini dengan:

```bash
docker compose logs api
```

Anda akan melihat output seperti:

```
[init] Waiting for PostgreSQL to be ready...
[init] PostgreSQL is ready.
[init] Running Alembic migrations...
[init] Migrations complete.
[init] Running seed script...
[init] Seed complete.
[init] Starting uvicorn...
```

### 1.6 Verifikasi Semua Service Berjalan

Cek status semua container:

```bash
docker compose ps
```

Semua service harus berstatus `healthy`:

```
NAME         STATUS
cts-db-1       Up (healthy)
cts-api-1      Up (healthy)
cts-frontend-1 Up (healthy)
cts-proxy-1    Up (healthy)
```

Jika ada service yang berstatus `unhealthy` atau `Exit`, periksa log-nya:

```bash
docker compose logs <nama-service>
# Contoh:
docker compose logs api
docker compose logs db
```

### 1.7 Akses Aplikasi

Setelah semua service `healthy`, aplikasi dapat diakses melalui browser:

- **Dari server itu sendiri:** `http://localhost`
- **Dari jaringan intranet:** `http://<IP_SERVER>` (ganti dengan IP server di jaringan kampus)

> Hanya port **80** yang terbuka ke jaringan. Port database (5432) dan API (8000) hanya dapat diakses dari dalam jaringan Docker internal.

### 1.8 Kredensial Admin Default

Setelah instalasi, gunakan akun berikut untuk login pertama kali:

| Field | Nilai |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |

> **Sangat disarankan** untuk segera mengganti password admin default setelah login pertama melalui menu pengaturan profil.

---

## 2. Cara Backup Database PostgreSQL

### 2.1 Backup Manual

Untuk membuat backup database secara manual, jalankan perintah berikut dari direktori project:

```bash
# Buat backup dengan timestamp
docker compose exec db pg_dump \
  -U cts_user \
  -d cts \
  -F c \
  -f /tmp/backup_cts_$(date +%Y%m%d_%H%M%S).dump

# Salin file backup dari container ke host
docker compose exec db sh -c \
  "ls /tmp/backup_cts_*.dump | tail -1" | \
  xargs -I{} docker compose cp db:{} ./backups/
```

Atau dengan cara yang lebih sederhana menggunakan satu perintah:

```bash
# Pastikan folder backups sudah ada
mkdir -p backups

# Backup langsung ke file di host
docker compose exec -T db pg_dump \
  -U cts_user \
  -d cts \
  -F c \
  > backups/backup_cts_$(date +%Y%m%d_%H%M%S).dump
```

Penjelasan opsi `pg_dump`:
- `-U cts_user` — username database
- `-d cts` — nama database
- `-F c` — format custom (terkompresi, direkomendasikan)
- `> backups/...` — simpan ke file di folder `backups/`

### 2.2 Script Backup Otomatis (Cron)

Buat script backup di server:

```bash
nano /opt/cts-backup.sh
```

Isi script:

```bash
#!/bin/bash
# Script backup otomatis CTS
# Simpan di: /opt/cts-backup.sh

# Konfigurasi
CTS_DIR="/path/ke/folder/cts"   # Ganti dengan path project Anda
BACKUP_DIR="/backup/cts"
RETENTION_DAYS=30               # Simpan backup selama 30 hari

# Buat folder backup jika belum ada
mkdir -p "$BACKUP_DIR"

# Nama file backup dengan timestamp
FILENAME="backup_cts_$(date +%Y%m%d_%H%M%S).dump"

# Jalankan backup
cd "$CTS_DIR"
docker compose exec -T db pg_dump \
  -U cts_user \
  -d cts \
  -F c \
  > "$BACKUP_DIR/$FILENAME"

# Cek apakah backup berhasil
if [ $? -eq 0 ]; then
    echo "[$(date)] Backup berhasil: $BACKUP_DIR/$FILENAME"
    # Hapus backup yang lebih lama dari RETENTION_DAYS hari
    find "$BACKUP_DIR" -name "backup_cts_*.dump" \
      -mtime +$RETENTION_DAYS -delete
    echo "[$(date)] Backup lama (>$RETENTION_DAYS hari) dihapus."
else
    echo "[$(date)] ERROR: Backup gagal!" >&2
fi
```

Beri izin eksekusi:

```bash
chmod +x /opt/cts-backup.sh
```

Daftarkan ke cron untuk berjalan otomatis setiap hari pukul 02:00:

```bash
crontab -e
```

Tambahkan baris berikut:

```
# Backup CTS setiap hari pukul 02:00
0 2 * * * /opt/cts-backup.sh >> /var/log/cts-backup.log 2>&1
```

Verifikasi cron sudah terdaftar:

```bash
crontab -l
```

### 2.3 Restore dari Backup

Untuk memulihkan database dari file backup:

```bash
# Salin file backup ke dalam container
docker compose cp backups/backup_cts_YYYYMMDD_HHMMSS.dump db:/tmp/restore.dump

# Restore database (akan menimpa data yang ada)
docker compose exec db pg_restore \
  -U cts_user \
  -d cts \
  --clean \
  --if-exists \
  /tmp/restore.dump
```

> **Peringatan:** Perintah `--clean` akan menghapus semua data yang ada sebelum restore. Pastikan Anda sudah membuat backup terbaru sebelum melakukan restore.

Jika restore gagal karena ada koneksi aktif ke database, hentikan service API terlebih dahulu:

```bash
# Hentikan service yang menggunakan database
docker compose stop api

# Jalankan restore
docker compose exec db pg_restore \
  -U cts_user \
  -d cts \
  --clean \
  --if-exists \
  /tmp/restore.dump

# Jalankan kembali service API
docker compose start api
```

### 2.4 Praktik Terbaik Backup

| Aspek | Rekomendasi |
|-------|-------------|
| **Frekuensi** | Minimal 1x sehari (malam hari saat beban rendah) |
| **Retensi** | Simpan 30 hari terakhir untuk backup harian |
| **Lokasi** | Simpan di drive/server terpisah dari server utama |
| **Verifikasi** | Uji restore ke server test setiap bulan |
| **Monitoring** | Pantau log `/var/log/cts-backup.log` secara berkala |
| **Enkripsi** | Enkripsi file backup jika disimpan di cloud/media eksternal |

Untuk menyalin backup ke lokasi lain (misalnya NAS atau server backup):

```bash
# Salin ke server lain via SCP
scp backups/backup_cts_*.dump user@server-backup:/backup/cts/

# Atau sinkronisasi folder backup ke NAS
rsync -av backups/ /mnt/nas/backup-cts/
```

---

## 3. Cara Update Versi

### 3.1 Persiapan Sebelum Update

Sebelum melakukan update, selalu buat backup database terlebih dahulu:

```bash
# Buat backup sebelum update
mkdir -p backups
docker compose exec -T db pg_dump \
  -U cts_user \
  -d cts \
  -F c \
  > backups/pre_update_$(date +%Y%m%d_%H%M%S).dump

echo "Backup selesai. Lanjutkan update."
```

### 3.2 Ambil Kode Terbaru dari Git

```bash
# Masuk ke direktori project
cd /path/ke/folder/cts

# Ambil perubahan terbaru
git fetch origin

# Lihat perubahan yang akan diaplikasikan
git log HEAD..origin/main --oneline

# Terapkan perubahan
git pull origin main
```

> Ganti `main` dengan nama branch yang sesuai jika berbeda (misalnya `master` atau `production`).

### 3.3 Hentikan Container yang Berjalan

```bash
docker compose down
```

Perintah ini menghentikan dan menghapus container, tetapi **tidak** menghapus volume data PostgreSQL.

### 3.4 Rebuild Image

```bash
# Build ulang semua image dengan kode terbaru
docker compose build --no-cache
```

Opsi `--no-cache` memastikan image dibangun dari awal tanpa menggunakan cache lama.

### 3.5 Jalankan Migrasi Database

Jalankan container database terlebih dahulu, lalu jalankan migrasi:

```bash
# Jalankan hanya service database
docker compose up -d db

# Tunggu database siap (sekitar 10 detik)
sleep 10

# Jalankan migrasi Alembic
docker compose run --rm api alembic upgrade head
```

Jika migrasi berhasil, Anda akan melihat output seperti:

```
INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456, add new column
```

Jika tidak ada migrasi baru, output akan menampilkan:

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

### 3.6 Jalankan Semua Service

```bash
docker compose up -d
```

### 3.7 Verifikasi Update Berhasil

```bash
# Cek status semua container
docker compose ps

# Pantau log untuk memastikan tidak ada error
docker compose logs --tail=50 api
docker compose logs --tail=50 frontend
```

Akses aplikasi di browser dan verifikasi fitur-fitur utama berjalan normal.

Untuk mengecek versi yang sedang berjalan:

```bash
# Cek commit yang sedang aktif
git log --oneline -5
```

### 3.8 Prosedur Rollback (Jika Update Gagal)

Jika terjadi masalah setelah update, ikuti langkah berikut untuk kembali ke versi sebelumnya:

**Langkah 1: Hentikan semua container**

```bash
docker compose down
```

**Langkah 2: Kembali ke commit sebelumnya**

```bash
# Lihat daftar commit terakhir
git log --oneline -10

# Kembali ke commit sebelum update (ganti COMMIT_HASH)
git checkout COMMIT_HASH
```

**Langkah 3: Restore database dari backup pre-update**

```bash
# Jalankan database
docker compose up -d db
sleep 10

# Restore dari backup yang dibuat sebelum update
docker compose cp backups/pre_update_YYYYMMDD_HHMMSS.dump db:/tmp/restore.dump

docker compose exec db pg_restore \
  -U cts_user \
  -d cts \
  --clean \
  --if-exists \
  /tmp/restore.dump
```

**Langkah 4: Build dan jalankan versi lama**

```bash
docker compose build --no-cache
docker compose up -d
```

**Langkah 5: Verifikasi rollback berhasil**

```bash
docker compose ps
docker compose logs --tail=30 api
```

Setelah rollback berhasil, hubungi tim pengembang untuk melaporkan masalah yang terjadi sebelum mencoba update kembali.

---

## Referensi Cepat — Perintah Umum

```bash
# Lihat status semua service
docker compose ps

# Lihat log real-time
docker compose logs -f

# Lihat log service tertentu
docker compose logs -f api

# Restart semua service
docker compose restart

# Restart service tertentu
docker compose restart api

# Hentikan semua service
docker compose down

# Jalankan semua service
docker compose up -d

# Masuk ke shell container database
docker compose exec db psql -U cts_user -d cts

# Masuk ke shell container API
docker compose exec api bash
```

---

*Dokumen ini dibuat untuk Sistem Penjadwalan Kuliah (CTS) — Jurusan Matematika FMIPA Universitas Riau.*
