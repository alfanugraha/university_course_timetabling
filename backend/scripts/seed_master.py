"""
backend/scripts/seed_master.py
Seed data master Jurusan Matematika FMIPA UNRI:
  - Prodi (10)
  - Ruang Kuliah (9)
  - Kurikulum (6)
  - Dosen (46)
  - Mata Kuliah (355: S1 MTK K21/25, S1 STK K21/25, S2 MTK K21/25)

Data bersumber dari:
  - data_dukung_aktualisasi/db.xlsx
  - data_dukung_aktualisasi/db_mata_kuliah.xlsx

Idempotent — aman dijalankan berulang kali; data yang sudah ada akan dilewati.

Jalankan:
    docker compose exec api python -m scripts.seed_master
    atau
    python -m scripts.seed_master   (dari direktori backend/)
"""

import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.dosen import Dosen
from app.models.kurikulum import Kurikulum
from app.models.mata_kuliah import MataKuliah
from app.models.prodi import Prodi
from app.models.ruang import Ruang

# ─────────────────────────────────────────────────────────────────────────────
# 1. PRODI
# ─────────────────────────────────────────────────────────────────────────────

PRODI_DATA = [
    # Internal
    {"kode": "S1MTK", "strata": "S-1", "nama": "Matematika",                    "singkat": "S1 MTK",  "kategori": "Internal"},
    {"kode": "S2MTK", "strata": "S-2", "nama": "Matematika",                    "singkat": "S2 MTK",  "kategori": "Internal"},
    {"kode": "S1STK", "strata": "S-1", "nama": "Statistika",                    "singkat": "S1 STK",  "kategori": "Internal"},
    # Layanan
    {"kode": "S1FIS", "strata": "S-1", "nama": "Fisika",                        "singkat": "S1 FIS",  "kategori": "Layanan"},
    {"kode": "S1KIM", "strata": "S-1", "nama": "Kimia",                         "singkat": "S1 KIM",  "kategori": "Layanan"},
    {"kode": "S1TKM", "strata": "S-1", "nama": "Teknik Kimia",                  "singkat": "S1 TKM",  "kategori": "Layanan"},
    {"kode": "S1TLH", "strata": "S-1", "nama": "Teknik Lingkungan",             "singkat": "S1 TLH",  "kategori": "Layanan"},
    {"kode": "S1TIP", "strata": "S-1", "nama": "Teknologi Industri Pertanian",  "singkat": "S1 TIP",  "kategori": "Layanan"},
    {"kode": "S2BIO", "strata": "S-2", "nama": "Biologi",                       "singkat": "S2 BIO",  "kategori": "Layanan"},
    {"kode": "S2PDM", "strata": "S-2", "nama": "Pendidikan Matematika",         "singkat": "S2 PDM",  "kategori": "Layanan"},
]

# ─────────────────────────────────────────────────────────────────────────────
# 2. RUANG KULIAH
# ─────────────────────────────────────────────────────────────────────────────

RUANG_DATA = [
    {"nama": "R.101",   "lantai": 1, "gedung": "Gedung Kuliah FMIPA",  "kapasitas": 45, "jenis": "Kelas"},
    {"nama": "R.202",   "lantai": 2, "gedung": "Gedung Kuliah FMIPA",  "kapasitas": 45, "jenis": "Kelas"},
    {"nama": "R.302",   "lantai": 3, "gedung": "Gedung Kuliah FMIPA",  "kapasitas": 45, "jenis": "Kelas"},
    {"nama": "R.304",   "lantai": 3, "gedung": "Gedung Kuliah FMIPA",  "kapasitas": 45, "jenis": "Kelas"},
    {"nama": "R.308",   "lantai": 3, "gedung": "Gedung Kuliah FMIPA",  "kapasitas": 45, "jenis": "Kelas"},
    {"nama": "R.208",   "lantai": 2, "gedung": "Gedung Dekanat FMIPA", "kapasitas": 45, "jenis": "Kelas"},
    {"nama": "LAB I",   "lantai": 1, "gedung": "Jurusan Matematika",   "kapasitas": 30, "jenis": "Lab"},
    {"nama": "LAB II",  "lantai": 1, "gedung": "Jurusan Matematika",   "kapasitas": 30, "jenis": "Lab"},
    {"nama": "LAB III", "lantai": 1, "gedung": "Gedung Epsilon",       "kapasitas": 30, "jenis": "Lab"},
]

# ─────────────────────────────────────────────────────────────────────────────
# 3. KURIKULUM
# ─────────────────────────────────────────────────────────────────────────────

KURIKULUM_DATA = [
    {"kode": "21S1MATH", "tahun": "2021", "prodi_kode": "S1MTK"},
    {"kode": "25S1MATH", "tahun": "2025", "prodi_kode": "S1MTK"},
    {"kode": "21S1STAT", "tahun": "2021", "prodi_kode": "S1STK"},
    {"kode": "25S1STAT", "tahun": "2025", "prodi_kode": "S1STK"},
    {"kode": "21S2MATH", "tahun": "2021", "prodi_kode": "S2MTK"},
    {"kode": "25S2MATH", "tahun": "2025", "prodi_kode": "S2MTK"},
]

# ─────────────────────────────────────────────────────────────────────────────
# 4. DOSEN
# homebase_kode: kode prodi dari PRODI_DATA, atau None untuk dosen external
# ─────────────────────────────────────────────────────────────────────────────

DOSEN_DATA = [
    # ── Dosen Tetap ──────────────────────────────────────────────────────────
    {"nidn": "0014096104", "nip": "196109141989031003", "kode": "HAR", "nama": "Harison, Drs., M.Si.",           "jabfung": "Lektor Kepala", "kjfd": "Statistika Teoritis dan Pemodelan",       "homebase": "S1STK", "tgl_lahir": datetime.date(1961, 9, 14),  "status": "Aktif"},
    {"nidn": "0011016201", "nip": "196201111988031001", "kode": "AAD", "nama": "Arisman Adnan, M.Sc., DR.",      "jabfung": "Lektor Kepala", "kjfd": "Statistika, Sains Data, dan Komputasi",   "homebase": "S1STK", "tgl_lahir": datetime.date(1962, 1, 11),  "status": "Aktif"},
    {"nidn": "0010026204", "nip": "196202101986031005", "kode": "MAS", "nama": "Mashadi, M.Si., DR., Prof.",     "jabfung": "Guru Besar",    "kjfd": "Matematika Murni",                        "homebase": "S2MTK", "tgl_lahir": datetime.date(1962, 2, 10),  "status": "Aktif"},
    {"nidn": "0022046203", "nip": "196204221991031002", "kode": "BUS", "nama": "Bustami, Drs., M.Si.",           "jabfung": "Lektor",        "kjfd": "Statistika Teoritis dan Pemodelan",       "homebase": "S1STK", "tgl_lahir": datetime.date(1962, 4, 22),  "status": "Aktif"},
    {"nidn": "0004126204", "nip": "196212041992032003", "kode": "LED", "nama": "Leli Deswita, M.Si., DR.",       "jabfung": "Lektor Kepala", "kjfd": "Matematika Komputasi",                    "homebase": "S1MTK", "tgl_lahir": datetime.date(1962, 12, 4),  "status": "Aktif"},
    {"nidn": "0012056304", "nip": "196305121989031002", "kode": "SYA", "nama": "Syamsudhuha, M.Sc., DR., Prof.","jabfung": "Guru Besar",    "kjfd": "Matematika Komputasi",                    "homebase": "S2MTK", "tgl_lahir": datetime.date(1963, 5, 12),  "status": "Aktif"},
    {"nidn": "0005056403", "nip": "196405051990021001", "kode": "IMR", "nama": "Imran M., M.Sc., DR.",           "jabfung": "Lektor Kepala", "kjfd": "Matematika Komputasi",                    "homebase": "S2MTK", "tgl_lahir": datetime.date(1964, 5, 5),   "status": "Aktif"},
    {"nidn": "0004066502", "nip": "196506041991031002", "kode": "GAM", "nama": "M. D. H. Gamal, M.Sc., DR., Prof.", "jabfung": "Guru Besar", "kjfd": "Matematika Manajemen",                  "homebase": "S2MTK", "tgl_lahir": datetime.date(1965, 6, 4),   "status": "Aktif"},
    {"nidn": "0016126501", "nip": "196512161992032002", "kode": "SGE", "nama": "Sri Gemawati, M.Si., DR.",       "jabfung": "Lektor",        "kjfd": "Matematika Murni",                        "homebase": "S2MTK", "tgl_lahir": datetime.date(1965, 12, 16), "status": "Aktif"},
    {"nidn": "0016036505", "nip": "196706121997021001", "kode": "REF", "nama": "Rustam Efendi, M.Si.",           "jabfung": "Lektor",        "kjfd": "Statistika Teoritis dan Pemodelan",       "homebase": "S1STK", "tgl_lahir": datetime.date(1967, 6, 12),  "status": "Aktif"},
    {"nidn": "0005087202", "nip": "197208051997021002", "kode": "SPU", "nama": "Supriadi Putra, M.Si.",          "jabfung": "Lektor Kepala", "kjfd": "Matematika Komputasi",                    "homebase": "S1MTK", "tgl_lahir": datetime.date(1972, 8, 5),   "status": "Aktif"},
    {"nidn": "0026077302", "nip": "197307261997022001", "kode": "IHA", "nama": "Ihda Hasbiyati, M.Si., DR.",     "jabfung": "Lektor Kepala", "kjfd": "Matematika Manajemen",                    "homebase": "S2MTK", "tgl_lahir": datetime.date(1973, 7, 26),  "status": "Aktif"},
    {"nidn": "0009017401", "nip": "197401091999032002", "kode": "MUS", "nama": "Musraini M., M.Si.",             "jabfung": "Lektor Kepala", "kjfd": "Matematika Murni",                        "homebase": "S1MTK", "tgl_lahir": datetime.date(1974, 1, 9),   "status": "Aktif"},
    {"nidn": "0029088704", "nip": "198708292019032010", "kode": "NGO", "nama": "Noor Ell Goldameir, S.Si., M.Si.", "jabfung": "Asisten Ahli", "kjfd": "Statistika Teoritis dan Pemodelan",    "homebase": "S1STK", "tgl_lahir": datetime.date(1987, 8, 29),  "status": "Aktif"},
    {"nidn": "0027108701", "nip": "198710272012121001", "kode": "ZUL", "nama": "Zulkarnain, M.Si., Ph.D.",       "jabfung": "Lektor",        "kjfd": "Matematika Komputasi",                    "homebase": "S2MTK", "tgl_lahir": datetime.date(1987, 10, 27), "status": "Aktif"},
    {"nidn": "0010018901", "nip": "198901102014041001", "kode": "KMU", "nama": "Khozin Mu'tamar, M.Si., DR.",    "jabfung": "Lektor",        "kjfd": "Matematika Komputasi",                    "homebase": "S2MTK", "tgl_lahir": datetime.date(1989, 1, 10),  "status": "Aktif"},
    {"nidn": "0019058906", "nip": "198905192019031010", "kode": "AHA", "nama": "Abdul Hadi, S.Si., M.Sc.",       "jabfung": "Asisten Ahli", "kjfd": "Matematika Murni",                         "homebase": "S1MTK", "tgl_lahir": datetime.date(1989, 5, 19),  "status": "Aktif"},
    {"nidn": None,         "nip": "199002112024062001", "kode": "INA", "nama": "Iis Nasfianti, M.Si.",           "jabfung": "Asisten Ahli", "kjfd": "Matematika Murni",                         "homebase": "S1MTK", "tgl_lahir": datetime.date(1990, 2, 11),  "status": "Aktif"},
    {"nidn": None,         "nip": "199005162025062005", "kode": "EFI", "nama": "Elsi Fitria, M.Si.",             "jabfung": None,            "kjfd": "Matematika Murni",                        "homebase": "S1MTK", "tgl_lahir": datetime.date(1990, 5, 16),  "status": "Aktif"},
    {"nidn": "0009119009", "nip": "199011092022032014", "kode": "RMA", "nama": "Rike Marjulisa, S.Pd., M.Si.",   "jabfung": "Asisten Ahli", "kjfd": "Matematika Komputasi",                     "homebase": "S1MTK", "tgl_lahir": datetime.date(1990, 11, 9),  "status": "Aktif"},
    {"nidn": "0028119002", "nip": "199011282023212043", "kode": "SUS", "nama": "Susilawati, M.Si., DR.",         "jabfung": "Lektor",        "kjfd": "Matematika Murni",                        "homebase": "S2MTK", "tgl_lahir": datetime.date(1990, 11, 28), "status": "Aktif"},
    {"nidn": "0023129102", "nip": "199112232022032010", "kode": "APU", "nama": "Ayunda Putri, S.Si., M.Sc.",     "jabfung": "Asisten Ahli", "kjfd": "Matematika Komputasi",                     "homebase": "S1MTK", "tgl_lahir": datetime.date(1991, 12, 23), "status": "Aktif"},
    {"nidn": "0011089305", "nip": "199308112022032025", "kode": "GER", "nama": "Gustriza Erda, S.Stat., M.Si.",  "jabfung": "Asisten Ahli", "kjfd": "Statistika, Sains Data, dan Komputasi",    "homebase": "S1STK", "tgl_lahir": datetime.date(1993, 8, 11),  "status": "Aktif"},
    {"nidn": None,         "nip": "199308262024062002", "kode": "EAG", "nama": "Efni Agustiarini, M.Si.",        "jabfung": "Asisten Ahli", "kjfd": "Matematika Manajemen",                     "homebase": "S1MTK", "tgl_lahir": datetime.date(1993, 8, 26),  "status": "Aktif"},
    {"nidn": None,         "nip": "199410222025062001", "kode": "RWA", "nama": "Rezi Wahyuni, S.Si., M.Si.",     "jabfung": None,            "kjfd": "Statistika, Sains Data, dan Komputasi",   "homebase": "S1STK", "tgl_lahir": datetime.date(1994, 10, 22), "status": "Aktif"},
    {"nidn": "0023069501", "nip": "199506232020122018", "kode": "AYO", "nama": "Anne Mudya Yolanda, S.Stat., M.Si.", "jabfung": "Lektor",   "kjfd": "Statistika, Sains Data, dan Komputasi",   "homebase": "S1STK", "tgl_lahir": datetime.date(1995, 6, 23),  "status": "Aktif"},
    {"nidn": None,         "nip": "199507282024062003", "kode": "NWA", "nama": "Nindya Wulandari, M.Si.",        "jabfung": "Asisten Ahli", "kjfd": "Statistika, Sains Data, dan Komputasi",    "homebase": "S1STK", "tgl_lahir": datetime.date(1995, 7, 28),  "status": "Aktif"},
    {"nidn": None,         "nip": "199704152025062007", "kode": "ANR", "nama": "Anisa Nurizki, S.Si., M.Si.",    "jabfung": None,            "kjfd": "Statistika, Sains Data, dan Komputasi",   "homebase": "S1MTK", "tgl_lahir": datetime.date(1997, 4, 15),  "status": "Aktif"},
    {"nidn": None,         "nip": "199803172025062004", "kode": "AMA", "nama": "Aziza Masli, S.Si., M.Si.",      "jabfung": None,            "kjfd": "Matematika Manajemen",                    "homebase": "S1MTK", "tgl_lahir": datetime.date(1998, 3, 17),  "status": "Aktif"},
    {"nidn": None,         "nip": "199806292025062014", "kode": "RRE", "nama": "Refi Revina, S.Si., M.Mat.",     "jabfung": None,            "kjfd": "Matematika Manajemen",                    "homebase": "S1MTK", "tgl_lahir": datetime.date(1998, 6, 29),  "status": "Aktif"},
    {"nidn": None,         "nip": "199807182024062001", "kode": "RAP", "nama": "Rizka Amalia Putri, M.Stat.",    "jabfung": "Asisten Ahli", "kjfd": "Statistika Teoritis dan Pemodelan",         "homebase": "S1STK", "tgl_lahir": datetime.date(1998, 7, 18),  "status": "Aktif"},
    {"nidn": None,         "nip": "200104152025061009", "kode": "TBI", "nama": "Tasnim Bilal, S.Si., M.Sc.",     "jabfung": None,            "kjfd": "Matematika Murni",                        "homebase": "S1MTK", "tgl_lahir": datetime.date(2001, 4, 15),  "status": "Aktif"},
    # ── Dosen External (luar jurusan) ─────────────────────────────────────────
    {"nidn": None, "nip": None, "kode": "ext1",  "nama": "Zetra Hainul Putra, S.Si., M.Sc., DR., Prof.", "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext2",  "nama": "Kartini, M.Si., DR.",                          "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext3",  "nama": "Elfizar, S.Si, M.Kom, DR., Prof.",              "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext4",  "nama": "Khairni Sukmawati, S.T., M.Kom.",              "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext5",  "nama": "Herlina, S.Kom, M.Cs.",                        "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext6",  "nama": "Riryn Novianty, M.Si.",                        "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext7",  "nama": "Siti Saidah Siregar, M.Si.",                   "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext8",  "nama": "Nikmatia Herfena, M.Si.",                      "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext9",  "nama": "Mukhlis, M.Si.",                               "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext10", "nama": "Widya Tania Artha, M.Si.",                     "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext11", "nama": "Fitra Perdana, S.Si., M.Sc.",                  "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext12", "nama": "Nur Afriana, M.Si.",                           "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext13", "nama": "Dosen T. Kim",                                 "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
    {"nidn": None, "nip": None, "kode": "ext14", "nama": "Dosen TIP",                                    "jabfung": None, "kjfd": None, "homebase": None, "tgl_lahir": None, "status": "Aktif"},
]

# ─────────────────────────────────────────────────────────────────────────────
# 5. MATA KULIAH
# Format: (kurikulum_kode, kode_mk, nama, jenis, semester, sks)
# ─────────────────────────────────────────────────────────────────────────────

MATA_KULIAH_DATA = [
    # ═══ S1 Statistika — Kurikulum 2021 (21S1STAT) ═══════════════════════════
    ("21S1STAT", "MST1101", "Metode Statistika", "Wajib", 1, 3),
    ("21S1STAT", "MST1102", "Pengantar Komputer", "Wajib", 1, 3),
    ("21S1STAT", "MST1103", "Kalkulus I", "Wajib", 1, 3),
    ("21S1STAT", "MST1201", "Algoritma dan Pemrograman", "Wajib", 2, 3),
    ("21S1STAT", "MST1202", "Analisis Regresi", "Wajib", 2, 3),
    ("21S1STAT", "MST1203", "Bahasa Inggris untuk Statistika", "Wajib", 2, 2),
    ("21S1STAT", "MST1204", "Kalkulus II", "Wajib", 2, 3),
    ("21S1STAT", "MST1205", "Aljabar Linear Elementer", "Wajib", 2, 3),
    ("21S1STAT", "MST1206", "Basis Data", "Wajib", 2, 3),
    ("21S1STAT", "MST1301", "Kalkulus Peubah Banyak", "Wajib", 3, 3),
    ("21S1STAT", "MST1302", "Persamaan Diferensial", "Wajib", 3, 3),
    ("21S1STAT", "MST1303", "Probabilitas", "Wajib", 3, 3),
    ("21S1STAT", "MST1304", "Statistika Matematika I", "Wajib", 3, 3),
    ("21S1STAT", "MST1305", "Pemrograman Statistika", "Wajib", 3, 3),
    ("21S1STAT", "MST1306", "Statistika Industri", "Wajib", 3, 3),
    ("21S1STAT", "MST1401", "Analisis Multivariat", "Wajib", 4, 3),
    ("21S1STAT", "MST1402", "Analisis Survival", "Wajib", 4, 3),
    ("21S1STAT", "MST1403", "Metode Sampling", "Wajib", 4, 3),
    ("21S1STAT", "MST1404", "Statistika Matematika II", "Wajib", 4, 3),
    ("21S1STAT", "MST1405", "Data Mining", "Wajib", 4, 3),
    ("21S1STAT", "MST1406", "Analisis Deret Waktu", "Wajib", 4, 3),
    ("21S1STAT", "MST1501", "Komputasi Statistika", "Wajib", 5, 3),
    ("21S1STAT", "MST1502", "Model Linier", "Wajib", 5, 3),
    ("21S1STAT", "MST1503", "Metodologi Penelitian", "Wajib", 5, 2),
    ("21S1STAT", "MST1504", "Perencanaan Percobaan", "Wajib", 5, 3),
    ("21S1STAT", "MST1505", "Analisis Data Kategorik", "Wajib", 5, 3),
    ("21S1STAT", "MST1506", "Statistika Spasial", "Pilihan", 5, 3),
    ("21S1STAT", "MST1507", "Statistika Bayesian", "Pilihan", 5, 3),
    ("21S1STAT", "MST1508", "Analisis Finansial", "Pilihan", 5, 3),
    ("21S1STAT", "MST1509", "Teori Permainan", "Pilihan", 5, 3),
    ("21S1STAT", "MST1601", "KKN / Magang", "Wajib", 6, 4),
    ("21S1STAT", "MST1602", "Skripsi", "Wajib", 6, 6),
    ("21S1STAT", "MST1603", "Kapita Selekta Statistika Terapan", "Pilihan", 6, 3),
    ("21S1STAT", "MST1604", "Statistika Pendidikan", "Pilihan", 6, 3),
    ("21S1STAT", "MST1605", "Kewirausahaan", "Pilihan", 6, 3),
    ("21S1STAT", "MST1606", "Analisis Resiko", "Pilihan", 6, 3),
    ("21S1STAT", "MST1607", "Biostatistika", "Pilihan", 6, 3),
    ("21S1STAT", "MST1608", "Statistika Sosial", "Pilihan", 6, 3),
    ("21S1STAT", "MST1609", "Statistika Non Parametrik", "Pilihan", 6, 3),
    ("21S1STAT", "MST1610", "Teori Antrian", "Pilihan", 6, 3),
    ("21S1STAT", "MST1611", "Demografi", "Pilihan", 6, 3),
    ("21S1STAT", "MST1612", "Riset Operasi", "Pilihan", 6, 3),
    ("21S1STAT", "UNR0001", "Pancasila", "Wajib", 1, 2),
    ("21S1STAT", "UNR0002", "Pendidikan Agama", "Wajib", 1, 2),
    ("21S1STAT", "UNR0003", "Bahasa Indonesia", "Wajib", 1, 2),
    ("21S1STAT", "UNR0004", "Kewarganegaraan", "Wajib", 2, 2),
    ("21S1STAT", "UNR0005", "Bahasa Inggris", "Wajib", 2, 2),
    ("21S1STAT", "UNR0006", "KKN", "Wajib", 6, 4),
    ("21S1STAT", "UNR0007", "Etika Profesi", "Wajib", 5, 2),
    ("21S1STAT", "UNR0008", "Kewirausahaan", "Wajib", 4, 2),
    ("21S1STAT", "UNR0009", "Kuliah Kerja Profesi", "Wajib", 6, 2),
    ("21S1STAT", "UNR0010", "Seminar Proposal", "Wajib", 6, 1),
    ("21S1STAT", "UNR0011", "Komprehensif", "Wajib", 7, 0),
    ("21S1STAT", "UNR0012", "Tugas Akhir", "Wajib", 7, 6),

    # ═══ S1 Statistika — Kurikulum 2025 (25S1STAT) ═══════════════════════════
    ("25S1STAT", "STK03111001", "Metode Statistika", "Wajib", 1, 3),
    ("25S1STAT", "STK03111002", "Pengantar Komputer", "Wajib", 1, 3),
    ("25S1STAT", "STK03111003", "Kalkulus I", "Wajib", 1, 3),
    ("25S1STAT", "STK03122004", "Algoritma dan Pemrograman", "Wajib", 2, 3),
    ("25S1STAT", "STK03122005", "Analisis Regresi", "Wajib", 2, 3),
    ("25S1STAT", "STK03122006", "Bahasa Inggris untuk Statistika", "Wajib", 2, 2),
    ("25S1STAT", "STK03122007", "Kalkulus II", "Wajib", 2, 3),
    ("25S1STAT", "STK03122008", "Aljabar Linear Elementer", "Wajib", 2, 3),
    ("25S1STAT", "STK03122009", "Basis Data", "Wajib", 2, 3),
    ("25S1STAT", "STK03133010", "Kalkulus Peubah Banyak", "Wajib", 3, 3),
    ("25S1STAT", "STK03133011", "Persamaan Diferensial", "Wajib", 3, 3),
    ("25S1STAT", "STK03133012", "Probabilitas", "Wajib", 3, 3),
    ("25S1STAT", "STK03133013", "Statistika Matematika I", "Wajib", 3, 3),
    ("25S1STAT", "STK03133014", "Pemrograman Statistika", "Wajib", 3, 3),
    ("25S1STAT", "STK03133015", "Statistika Industri", "Wajib", 3, 3),
    ("25S1STAT", "STK03144016", "Analisis Multivariat", "Wajib", 4, 3),
    ("25S1STAT", "STK03144017", "Analisis Survival", "Wajib", 4, 3),
    ("25S1STAT", "STK03144018", "Metode Sampling", "Wajib", 4, 3),
    ("25S1STAT", "STK03144019", "Statistika Matematika II", "Wajib", 4, 3),
    ("25S1STAT", "STK03144020", "Data Mining", "Wajib", 4, 3),
    ("25S1STAT", "STK03144021", "Analisis Deret Waktu", "Wajib", 4, 3),
    ("25S1STAT", "STK03155022", "Komputasi Statistika", "Wajib", 5, 3),
    ("25S1STAT", "STK03155023", "Model Linier", "Wajib", 5, 3),
    ("25S1STAT", "STK03155024", "Metodologi Penelitian", "Wajib", 5, 2),
    ("25S1STAT", "STK03155025", "Perencanaan Percobaan", "Wajib", 5, 3),
    ("25S1STAT", "STK03155026", "Analisis Data Kategorik", "Wajib", 5, 3),
    ("25S1STAT", "STK03155027", "Statistika Spasial", "Pilihan", 5, 3),
    ("25S1STAT", "STK03155028", "Statistika Bayesian", "Pilihan", 5, 3),
    ("25S1STAT", "STK03155029", "Analisis Finansial", "Pilihan", 5, 3),
    ("25S1STAT", "STK03155030", "Teori Permainan", "Pilihan", 5, 3),
    ("25S1STAT", "STK03166031", "Kapita Selekta Statistika Terapan", "Pilihan", 6, 3),
    ("25S1STAT", "STK03166032", "Statistika Pendidikan", "Pilihan", 6, 3),
    ("25S1STAT", "STK03166033", "Kewirausahaan", "Pilihan", 6, 3),
    ("25S1STAT", "STK03166034", "Analisis Resiko", "Pilihan", 6, 3),
    ("25S1STAT", "STK03166035", "Biostatistika", "Pilihan", 6, 3),
    ("25S1STAT", "STK03166036", "Statistika Sosial", "Pilihan", 6, 3),
    ("25S1STAT", "STK03166037", "Statistika Non Parametrik", "Pilihan", 6, 3),
    ("25S1STAT", "STK03166038", "Teori Antrian", "Pilihan", 6, 3),
    ("25S1STAT", "STK03166039", "Demografi", "Pilihan", 6, 3),
    ("25S1STAT", "STK03166040", "Riset Operasi", "Pilihan", 6, 3),
    ("25S1STAT", "STK03177041", "KKN / Magang", "Wajib", 7, 4),
    ("25S1STAT", "STK03188042", "Skripsi", "Wajib", 8, 6),
    ("25S1STAT", "UNR2025001", "Pancasila", "Wajib", 1, 2),
    ("25S1STAT", "UNR2025002", "Pendidikan Agama", "Wajib", 1, 2),
    ("25S1STAT", "UNR2025003", "Bahasa Indonesia", "Wajib", 1, 2),
    ("25S1STAT", "UNR2025004", "Kewarganegaraan", "Wajib", 2, 2),
    ("25S1STAT", "UNR2025005", "Bahasa Inggris", "Wajib", 2, 2),
    ("25S1STAT", "UNR2025006", "Etika Profesi", "Wajib", 5, 2),
    ("25S1STAT", "UNR2025007", "Kuliah Kerja Profesi", "Wajib", 6, 2),
    ("25S1STAT", "UNR2025008", "Seminar Proposal", "Wajib", 7, 1),
    ("25S1STAT", "UNR2025009", "Komprehensif", "Wajib", 8, 0),
    ("25S1STAT", "UNR2025010", "Tugas Akhir", "Wajib", 8, 6),
    ("25S1STAT", "UNR2025011", "Pendidikan Jasmani", "Wajib", 1, 1),
    ("25S1STAT", "UNR2025012", "Budaya Melayu Riau", "Wajib", 2, 2),

    # ═══ S1 Matematika — Kurikulum 2021 (21S1MATH) ═══════════════════════════
    ("21S1MATH", "MFI1199", "Fisika Dasar", "Wajib", 1, 3),
    ("21S1MATH", "MMA1001", "Kalkulus I", "Wajib", 1, 3),
    ("21S1MATH", "MMA1102", "Logika Matematika", "Wajib", 1, 3),
    ("21S1MATH", "MMA1103", "Statistika Elementer", "Wajib", 1, 3),
    ("21S1MATH", "MMA1104", "Pengantar Komputer", "Wajib", 1, 3),
    ("21S1MATH", "UNR0001", "Pendidikan Agama", "Wajib", 1, 2),
    ("21S1MATH", "UNR0002", "Bahasa Indonesia", "Wajib", 1, 2),
    ("21S1MATH", "MMA1201", "Kalkulus II", "Wajib", 2, 3),
    ("21S1MATH", "MMA1202", "Matematika Diskrit", "Wajib", 2, 3),
    ("21S1MATH", "MMA1203", "Pengantar Aljabar", "Wajib", 2, 3),
    ("21S1MATH", "MMA1204", "Algoritma dan Pemrograman", "Wajib", 2, 3),
    ("21S1MATH", "MMA1205", "Geometri Analitik", "Wajib", 2, 3),
    ("21S1MATH", "UNR0003", "Pancasila", "Wajib", 2, 2),
    ("21S1MATH", "UNR0004", "Kewarganegaraan", "Wajib", 2, 2),
    ("21S1MATH", "MMA2001", "Kalkulus Peubah Banyak", "Wajib", 3, 3),
    ("21S1MATH", "MMA2002", "Aljabar Linear", "Wajib", 3, 3),
    ("21S1MATH", "MMA2003", "Analisis Riil I", "Wajib", 3, 3),
    ("21S1MATH", "MMA2104", "Persamaan Diferensial Biasa", "Wajib", 3, 3),
    ("21S1MATH", "MMA2105", "Komputasi Matematika I", "Wajib", 3, 3),
    ("21S1MATH", "UNR0005", "Bahasa Inggris", "Wajib", 3, 2),
    ("21S1MATH", "MMA2201", "Analisis Riil II", "Wajib", 4, 3),
    ("21S1MATH", "MMA2202", "Analisis Vektor", "Wajib", 4, 3),
    ("21S1MATH", "MMA2203", "Persamaan Diferensial Parsial", "Wajib", 4, 3),
    ("21S1MATH", "MMA2204", "Teori Probabilitas", "Wajib", 4, 3),
    ("21S1MATH", "MMA2205", "Komputasi Matematika II", "Wajib", 4, 3),
    ("21S1MATH", "MMA2206", "Pemrograman Berorientasi Objek", "Pilihan", 4, 3),
    ("21S1MATH", "MMA2207", "Pengantar Teori Graf", "Pilihan", 4, 3),
    ("21S1MATH", "MMA2208", "Matematika Asuransi", "Pilihan", 4, 3),
    ("21S1MATH", "MMA3001", "Analisis Kompleks", "Wajib", 5, 3),
    ("21S1MATH", "MMA3002", "Matematika Keuangan", "Wajib", 5, 3),
    ("21S1MATH", "MMA3003", "Metodologi Penelitian", "Wajib", 5, 2),
    ("21S1MATH", "MMA3104", "Riset Operasi", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3105", "Analisis Numerik", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3106", "Teori Ukuran", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3107", "Analisis Fungsional", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3108", "Teori Ring dan Modul", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3109", "Geometri Diferensial", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3110", "Teori Kontrol", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3111", "Pemodelan Matematika", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3112", "Analisis Konveks", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3113", "Kriptografi", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3201", "Kapita Selekta Matematika Murni", "Pilihan", 6, 3),
    ("21S1MATH", "MMA3202", "Kapita Selekta Mat. Komputasi", "Pilihan", 6, 3),
    ("21S1MATH", "MMA3203", "Kapita Selekta Mat. Manajemen", "Pilihan", 6, 3),
    ("21S1MATH", "MMA3204", "Basis Data", "Pilihan", 6, 3),
    ("21S1MATH", "MMA3205", "Keamanan Jaringan", "Pilihan", 6, 3),
    ("21S1MATH", "MMA3206", "Teori Bilangan", "Pilihan", 6, 3),
    ("21S1MATH", "MMA3207", "Kombinatorika", "Pilihan", 6, 3),
    ("21S1MATH", "MMA3208", "Matematika Fuzzy", "Pilihan", 6, 3),
    ("21S1MATH", "MMA3209", "Pemrosesan Citra Digital", "Pilihan", 6, 3),
    ("21S1MATH", "MMA3210", "Teori Coding", "Pilihan", 6, 3),
    ("21S1MATH", "UNR0006", "Kewirausahaan", "Wajib", 4, 2),
    ("21S1MATH", "UNR0007", "Etika Profesi", "Wajib", 5, 2),
    ("21S1MATH", "UNR0008", "KKN", "Wajib", 6, 4),
    ("21S1MATH", "UNR0009", "Magang / Kuliah Kerja Profesi", "Wajib", 6, 2),
    ("21S1MATH", "UNR0010", "Seminar Proposal", "Wajib", 7, 1),
    ("21S1MATH", "UNR0011", "Komprehensif", "Wajib", 7, 0),
    ("21S1MATH", "UNR0012", "Skripsi", "Wajib", 7, 6),
    ("21S1MATH", "UNR0013", "Pemikiran Kritis dan Kreativitas", "Wajib", 1, 2),
    ("21S1MATH", "UNR0014", "Komunikasi Efektif", "Wajib", 2, 2),
    ("21S1MATH", "UNR0015", "Kolaborasi dan Kepemimpinan", "Wajib", 3, 2),
    ("21S1MATH", "UNR0016", "Literasi Digital", "Wajib", 4, 2),
    ("21S1MATH", "UNR0017", "Pendidikan Jasmani", "Wajib", 1, 1),
    ("21S1MATH", "UNR0018", "Budaya Melayu Riau", "Wajib", 2, 2),
    ("21S1MATH", "MFI1198", "Kimia Dasar", "Wajib", 1, 3),
    ("21S1MATH", "MMA2009", "Fungsi Khusus", "Pilihan", 4, 3),
    ("21S1MATH", "MMA3003a", "Aljabar Abstrak", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3003b", "Topologi", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3003c", "Teori Graph Terapan", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3003d", "Program Linear", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3003e", "Metode Numerik", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3003f", "Simulasi Komputer", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3003g", "Persamaan Integral", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3003h", "Teori Antrian", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3003i", "Matematika Asuransi Lanjutan", "Pilihan", 5, 3),
    ("21S1MATH", "MMA3003j", "Analisis Regresi", "Pilihan", 5, 3),

    # ═══ S1 Matematika — Kurikulum 2025 (25S1MATH) ═══════════════════════════
    ("25S1MATH", "MTK03111001", "Fisika Dasar", "Wajib", 1, 3),
    ("25S1MATH", "MTK03111002", "Kalkulus Diferensial", "Wajib", 1, 3),
    ("25S1MATH", "MTK03111003", "Logika Matematika", "Wajib", 1, 3),
    ("25S1MATH", "MTK03111004", "Statistika Elementer", "Wajib", 1, 3),
    ("25S1MATH", "MTK03111005", "Pengantar Komputer", "Wajib", 1, 3),
    ("25S1MATH", "MTK03122006", "Kalkulus Integral", "Wajib", 2, 3),
    ("25S1MATH", "MTK03122007", "Matematika Diskrit", "Wajib", 2, 3),
    ("25S1MATH", "MTK03122008", "Pengantar Aljabar", "Wajib", 2, 3),
    ("25S1MATH", "MTK03122009", "Algoritma dan Pemrograman", "Wajib", 2, 3),
    ("25S1MATH", "MTK03122010", "Geometri Analitik", "Wajib", 2, 3),
    ("25S1MATH", "MTK03133011", "Kalkulus Peubah Banyak", "Wajib", 3, 3),
    ("25S1MATH", "MTK03133012", "Aljabar Linear", "Wajib", 3, 3),
    ("25S1MATH", "MTK03133013", "Analisis Riil I", "Wajib", 3, 3),
    ("25S1MATH", "MTK03133014", "Persamaan Diferensial Biasa", "Wajib", 3, 3),
    ("25S1MATH", "MTK03133015", "Komputasi Matematika I", "Wajib", 3, 3),
    ("25S1MATH", "MTK03144016", "Analisis Riil II", "Wajib", 4, 3),
    ("25S1MATH", "MTK03144017", "Analisis Vektor", "Wajib", 4, 3),
    ("25S1MATH", "MTK03144018", "Persamaan Diferensial Parsial", "Wajib", 4, 3),
    ("25S1MATH", "MTK03144019", "Teori Probabilitas", "Wajib", 4, 3),
    ("25S1MATH", "MTK03144020", "Komputasi Matematika II", "Wajib", 4, 3),
    ("25S1MATH", "MTK03155021", "Analisis Kompleks", "Wajib", 5, 3),
    ("25S1MATH", "MTK03155022", "Metodologi Penelitian", "Wajib", 5, 2),
    ("25S1MATH", "MTK03155023", "Riset Operasi", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155024", "Analisis Numerik", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155025", "Teori Ukuran", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155026", "Analisis Fungsional", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155027", "Teori Ring dan Modul", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155028", "Geometri Diferensial", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155029", "Teori Kontrol", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155030", "Pemodelan Matematika", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155031", "Kriptografi", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155032", "Kombinatorika", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155033", "Matematika Keuangan", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155034", "Program Linear", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03166035", "Kapita Selekta Matematika Murni", "Pilihan", 6, 3),
    ("25S1MATH", "MTK03166036", "Kapita Selekta Mat. Komputasi", "Pilihan", 6, 3),
    ("25S1MATH", "MTK03166037", "Kapita Selekta Mat. Manajemen", "Pilihan", 6, 3),
    ("25S1MATH", "MTK03166038", "Teori Bilangan", "Pilihan", 6, 3),
    ("25S1MATH", "MTK03166039", "Matematika Fuzzy", "Pilihan", 6, 3),
    ("25S1MATH", "MTK03166040", "Topologi", "Pilihan", 6, 3),
    ("25S1MATH", "MTK03166041", "Teori Graph Terapan", "Pilihan", 6, 3),
    ("25S1MATH", "MTK03166042", "Simulasi Komputer", "Pilihan", 6, 3),
    ("25S1MATH", "MTK03166043", "Persamaan Integral", "Pilihan", 6, 3),
    ("25S1MATH", "MTK03166044", "Analisis Regresi", "Pilihan", 6, 3),
    ("25S1MATH", "MTK03166045", "Matematika Asuransi", "Pilihan", 6, 3),
    ("25S1MATH", "MTK03177046", "Magang", "Wajib", 7, 4),
    ("25S1MATH", "MTK03188047", "Skripsi", "Wajib", 8, 6),
    ("25S1MATH", "UNR2025001", "Pendidikan Agama", "Wajib", 1, 2),
    ("25S1MATH", "UNR2025002", "Bahasa Indonesia", "Wajib", 1, 2),
    ("25S1MATH", "UNR2025003", "Pancasila", "Wajib", 2, 2),
    ("25S1MATH", "UNR2025004", "Kewarganegaraan", "Wajib", 2, 2),
    ("25S1MATH", "UNR2025005", "Bahasa Inggris", "Wajib", 3, 2),
    ("25S1MATH", "UNR2025006", "Kewirausahaan", "Wajib", 4, 2),
    ("25S1MATH", "UNR2025007", "Etika Profesi", "Wajib", 5, 2),
    ("25S1MATH", "UNR2025008", "Kuliah Kerja Nyata", "Wajib", 6, 4),
    ("25S1MATH", "UNR2025009", "Kuliah Kerja Profesi", "Wajib", 6, 2),
    ("25S1MATH", "UNR2025010", "Seminar Proposal", "Wajib", 7, 1),
    ("25S1MATH", "UNR2025011", "Komprehensif", "Wajib", 7, 0),
    ("25S1MATH", "UNR2025012", "Pendidikan Jasmani", "Wajib", 1, 1),
    ("25S1MATH", "UNR2025013", "Budaya Melayu Riau", "Wajib", 2, 2),
    ("25S1MATH", "MTK03111000", "Kimia Dasar", "Wajib", 1, 3),
    ("25S1MATH", "MTK03144021", "Pemrograman Berorientasi Objek", "Pilihan", 4, 3),
    ("25S1MATH", "MTK03144022", "Fungsi Khusus", "Pilihan", 4, 3),
    ("25S1MATH", "MTK03144023", "Pengantar Teori Graf", "Pilihan", 4, 3),
    ("25S1MATH", "MTK03144024", "Matematika Asuransi", "Pilihan", 4, 3),
    ("25S1MATH", "MTK03144025", "Analisis Data dan Visualisasi", "Pilihan", 4, 3),
    ("25S1MATH", "MTK03155035", "Aljabar Abstrak", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155036", "Metode Numerik", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155037", "Teori Antrian", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155038", "Matematika Asuransi Lanjutan", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155039", "Pemrosesan Citra Digital", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155040", "Teori Coding", "Pilihan", 5, 3),
    ("25S1MATH", "MTK03155041", "Keamanan Jaringan", "Pilihan", 5, 3),

    # ═══ S2 Matematika — Kurikulum 2021 (21S2MATH) ═══════════════════════════
    ("21S2MATH", "MMA5001", "Analisis Real", "Wajib", 1, 3),
    ("21S2MATH", "MMA5102", "Aljabar Linear Lanjut", "Wajib", 1, 3),
    ("21S2MATH", "MMA5103", "Teori Peluang", "Wajib", 1, 3),
    ("21S2MATH", "MMA5002", "Geometri", "Pilihan", 1, 2),
    ("21S2MATH", "MMA5003", "Teori Bilangan", "Pilihan", 1, 2),
    ("21S2MATH", "MMA5004", "Topologi", "Pilihan", 1, 2),
    ("21S2MATH", "MMA5005", "Optimasi", "Wajib", 2, 3),
    ("21S2MATH", "MMA5006", "Metode Numerik Lanjut", "Wajib", 2, 3),
    ("21S2MATH", "MMA5007", "Statistika Matematika", "Wajib", 2, 3),
    ("21S2MATH", "MMA5008", "Analisis Fungsional", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5009", "Aljabar Abstrak Lanjut", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5010", "Riset Operasi Lanjut", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5011", "Matematika Komputasi Lanjut", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5012", "Pemodelan Matematika Lanjut", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5013", "Analisis Numerik Lanjut", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5014", "Teori Kontrol Lanjut", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5015", "Matematika Keuangan Lanjut", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5016", "Kriptografi Lanjut", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5101", "Seminar", "Wajib", 3, 2),
    ("21S2MATH", "MMA5104", "Publikasi Ilmiah", "Wajib", 3, 2),
    ("21S2MATH", "MMA5105", "Tesis", "Wajib", 4, 6),
    ("21S2MATH", "MMA5106", "Metodologi Penelitian", "Wajib", 1, 2),
    ("21S2MATH", "MMA5107", "Kapita Selekta I", "Pilihan", 3, 3),
    ("21S2MATH", "MMA5108", "Kapita Selekta II", "Pilihan", 3, 3),
    ("21S2MATH", "MMA5109", "Kapita Selekta III", "Pilihan", 4, 3),
    ("21S2MATH", "MMA5110", "Kapita Selekta IV", "Pilihan", 4, 3),
    ("21S2MATH", "MMA5111", "Analisis Kompleks Lanjut", "Pilihan", 1, 3),
    ("21S2MATH", "MMA5112", "Persamaan Diferensial Lanjut", "Pilihan", 1, 3),
    ("21S2MATH", "MMA5113", "Teori Ukuran dan Integrasi", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5114", "Analisis Konveks Lanjut", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5115", "Kombinatorika Lanjut", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5116", "Graf dan Jaringan", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5117", "Program Linear Lanjut", "Pilihan", 2, 3),
    ("21S2MATH", "MMA5118", "Simulasi dan Pemodelan", "Pilihan", 3, 3),
    ("21S2MATH", "MMA5119", "Pembelajaran Mesin", "Pilihan", 3, 3),
    ("21S2MATH", "MMA5120", "Analisis Data Besar", "Pilihan", 3, 3),
    ("21S2MATH", "MMA5121", "Statistika Komputasi Lanjut", "Pilihan", 3, 3),
    ("21S2MATH", "MMA5122", "Matematika Biologi", "Pilihan", 3, 3),
    ("21S2MATH", "MMA5123", "Aljabar Homologis", "Pilihan", 3, 3),
    ("21S2MATH", "MMA5124", "Geometri Riemannian", "Pilihan", 4, 3),
    ("21S2MATH", "MMA5125", "Teori Representasi", "Pilihan", 4, 3),
    ("21S2MATH", "MMA5126", "Dinamika Fluida", "Pilihan", 4, 3),
    ("21S2MATH", "MMA5127", "Teori Informasi dan Kodasi", "Pilihan", 4, 3),
    ("21S2MATH", "MMA5128", "Analisis Stokastik", "Pilihan", 4, 3),
    ("21S2MATH", "MMA5129", "Teori Antrian Lanjut", "Pilihan", 4, 3),

    # ═══ S2 Matematika — Kurikulum 2025 (25S2MATH) ═══════════════════════════
    ("25S2MATH", "MTK03201001", "Analisis Real", "Wajib", 1, 3),
    ("25S2MATH", "MTK03201002", "Aljabar Linear Lanjut", "Wajib", 1, 3),
    ("25S2MATH", "MTK03201003", "Teori Peluang", "Wajib", 1, 3),
    ("25S2MATH", "MTK03201004", "Matematika Riset Operasi", "Wajib", 1, 3),
    ("25S2MATH", "MTK03201005", "Metodologi Penelitian", "Wajib", 1, 2),
    ("25S2MATH", "MTK03202006", "Optimasi", "Wajib", 2, 3),
    ("25S2MATH", "MTK03202007", "Metode Numerik Lanjut", "Wajib", 2, 3),
    ("25S2MATH", "MTK03202008", "Statistika Matematika", "Wajib", 2, 3),
    ("25S2MATH", "MTK03202009", "Analisis Fungsional", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03202010", "Aljabar Abstrak Lanjut", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03202011", "Riset Operasi Lanjut", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03202012", "Matematika Komputasi Lanjut", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03202013", "Pemodelan Matematika Lanjut", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03202014", "Teori Kontrol Lanjut", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03202015", "Matematika Keuangan Lanjut", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03202016", "Kriptografi Lanjut", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03203017", "Seminar", "Wajib", 3, 2),
    ("25S2MATH", "MTK03203018", "Publikasi Ilmiah", "Wajib", 3, 2),
    ("25S2MATH", "MTK03203019", "Kapita Selekta I", "Pilihan", 3, 3),
    ("25S2MATH", "MTK03203020", "Kapita Selekta II", "Pilihan", 3, 3),
    ("25S2MATH", "MTK03204021", "Tesis", "Wajib", 4, 6),
    ("25S2MATH", "MTK03204022", "Kapita Selekta III", "Pilihan", 4, 3),
    ("25S2MATH", "MTK03204023", "Kapita Selekta IV", "Pilihan", 4, 3),
    ("25S2MATH", "MTK03201101", "Analisis Kompleks Lanjut", "Pilihan", 1, 3),
    ("25S2MATH", "MTK03201102", "Persamaan Diferensial Lanjut", "Pilihan", 1, 3),
    ("25S2MATH", "MTK03201103", "Topologi", "Pilihan", 1, 3),
    ("25S2MATH", "MTK03201104", "Teori Bilangan Lanjut", "Pilihan", 1, 3),
    ("25S2MATH", "MTK03201105", "Geometri Lanjut", "Pilihan", 1, 3),
    ("25S2MATH", "MTK03202101", "Teori Ukuran dan Integrasi", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03202102", "Analisis Konveks Lanjut", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03202103", "Kombinatorika Lanjut", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03202104", "Graf dan Jaringan", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03202105", "Program Linear Lanjut", "Pilihan", 2, 3),
    ("25S2MATH", "MTK03203101", "Simulasi dan Pemodelan", "Pilihan", 3, 3),
    ("25S2MATH", "MTK03203102", "Pembelajaran Mesin", "Pilihan", 3, 3),
    ("25S2MATH", "MTK03203103", "Analisis Data Besar", "Pilihan", 3, 3),
    ("25S2MATH", "MTK03203104", "Statistika Komputasi Lanjut", "Pilihan", 3, 3),
    ("25S2MATH", "MTK03203105", "Matematika Biologi", "Pilihan", 3, 3),
    ("25S2MATH", "MTK03204101", "Geometri Riemannian", "Pilihan", 4, 3),
    ("25S2MATH", "MTK03204102", "Teori Representasi", "Pilihan", 4, 3),
    ("25S2MATH", "MTK03204103", "Dinamika Fluida", "Pilihan", 4, 3),
    ("25S2MATH", "MTK03204104", "Analisis Stokastik", "Pilihan", 4, 3),
    ("25S2MATH", "MTK03204105", "Teori Antrian Lanjut", "Pilihan", 4, 3),
    ("25S2MATH", "MTK03204106", "Teori Informasi dan Kodasi", "Pilihan", 4, 3),
    ("25S2MATH", "MTK03204107", "Kecerdasan Buatan Terapan", "Pilihan", 4, 3),
    ("25S2MATH", "MTK03204108", "Optimasi Lanjut", "Pilihan", 4, 3),
]


# ─────────────────────────────────────────────────────────────────────────────
# Seed Functions
# ─────────────────────────────────────────────────────────────────────────────

def seed_prodi(db) -> dict[str, object]:
    """Seed prodi. Returns {kode: Prodi} map."""
    existing = {p.kode: p for p in db.query(Prodi).all()}
    inserted = 0
    for d in PRODI_DATA:
        if d["kode"] in existing:
            continue
        obj = Prodi(**d, is_active=True)
        db.add(obj)
        existing[d["kode"]] = obj
        inserted += 1
    db.flush()
    print(f"  Prodi: {inserted} inserted, {len(existing) - inserted} already exist")
    return existing


def seed_ruang(db) -> None:
    """Seed ruang kuliah."""
    existing_names = {r.nama for r in db.query(Ruang.nama).all()}
    inserted = 0
    for d in RUANG_DATA:
        if d["nama"] in existing_names:
            continue
        db.add(Ruang(**d, is_active=True))
        inserted += 1
    db.flush()
    print(f"  Ruang: {inserted} inserted, {len(existing_names)} already exist")


def seed_kurikulum(db, prodi_map: dict) -> dict[str, object]:
    """Seed kurikulum. Returns {kode: Kurikulum} map."""
    existing = {k.kode: k for k in db.query(Kurikulum).all()}
    inserted = 0
    for d in KURIKULUM_DATA:
        if d["kode"] in existing:
            continue
        prodi = prodi_map.get(d["prodi_kode"])
        if not prodi:
            print(f"  WARN: prodi '{d['prodi_kode']}' tidak ditemukan, kurikulum '{d['kode']}' dilewati.")
            continue
        obj = Kurikulum(kode=d["kode"], tahun=d["tahun"], prodi_id=prodi.id, is_active=True)
        db.add(obj)
        existing[d["kode"]] = obj
        inserted += 1
    db.flush()
    print(f"  Kurikulum: {inserted} inserted, {len(existing) - inserted} already exist")
    return existing


def seed_dosen(db, prodi_map: dict) -> None:
    """Seed dosen."""
    existing_kode = {d.kode for d in db.query(Dosen.kode).all()}
    inserted = 0
    for d in DOSEN_DATA:
        if d["kode"] in existing_kode:
            continue
        homebase_id = None
        if d["homebase"]:
            p = prodi_map.get(d["homebase"])
            if p:
                homebase_id = p.id
        obj = Dosen(
            nidn=d["nidn"],
            nip=d["nip"].strip() if d["nip"] else None,
            kode=d["kode"],
            nama=d["nama"],
            jabfung=d["jabfung"],
            kjfd=d["kjfd"],
            homebase_prodi_id=homebase_id,
            tgl_lahir=d["tgl_lahir"],
            status=d["status"],
        )
        db.add(obj)
        existing_kode.add(d["kode"])
        inserted += 1
    db.flush()
    print(f"  Dosen: {inserted} inserted, {len(existing_kode) - inserted} already exist")


def seed_mata_kuliah(db, kurikulum_map: dict) -> None:
    """Seed mata kuliah."""
    # Build existing set as (kurikulum_id, kode)
    existing = {
        (str(mk.kurikulum_id), mk.kode)
        for mk in db.query(MataKuliah.kurikulum_id, MataKuliah.kode).all()
    }
    inserted = 0
    skipped_kurikulum = set()
    for (kur_kode, kode_mk, nama, jenis, smt, sks) in MATA_KULIAH_DATA:
        kur = kurikulum_map.get(kur_kode)
        if not kur:
            skipped_kurikulum.add(kur_kode)
            continue
        key = (str(kur.id), kode_mk)
        if key in existing:
            continue
        obj = MataKuliah(
            kode=kode_mk,
            kurikulum_id=kur.id,
            nama=nama,
            sks=sks,
            semester=smt,
            jenis=jenis,
        )
        db.add(obj)
        existing.add(key)
        inserted += 1
    if skipped_kurikulum:
        print(f"  WARN: kurikulum tidak ditemukan: {skipped_kurikulum}")
    print(f"  Mata Kuliah: {inserted} inserted, {len(existing) - inserted} already exist")


def run() -> None:
    print("Running seed_master...")
    db = SessionLocal()
    try:
        prodi_map = seed_prodi(db)
        seed_ruang(db)
        kurikulum_map = seed_kurikulum(db, prodi_map)
        seed_dosen(db, prodi_map)
        seed_mata_kuliah(db, kurikulum_map)
        db.commit()
        print("seed_master completed successfully.")
    except Exception as exc:
        db.rollback()
        print(f"seed_master failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
