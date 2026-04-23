"""
backend/scripts/seed.py
Seed data dasar:
  - 15 timeslot tetap (3 sesi × 5 hari: Senin–Jumat)
  - User admin default

Jalankan dari direktori backend/:
    python -m scripts.seed
atau via Docker:
    docker compose exec api python -m scripts.seed
"""

import datetime
import sys
import os

# Pastikan package app dapat diimport saat dijalankan langsung
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.timeslot import Timeslot
from app.models.user import User, UserRole

# ---------------------------------------------------------------------------
# Data timeslot tetap
# ---------------------------------------------------------------------------

DAYS = [
    ("Senin",  "mon"),
    ("Selasa", "tue"),
    ("Rabu",   "wed"),
    ("Kamis",  "thu"),
    ("Jumat",  "fri"),
]

SESSIONS = [
    (1, datetime.time(7, 30),  datetime.time(10, 0),  "07:30–10:00"),
    (2, datetime.time(10, 0),  datetime.time(12, 30), "10:00–12:30"),
    (3, datetime.time(13, 0),  datetime.time(15, 30), "13:00–15:30"),
]

TIMESLOTS: list[dict] = []
for hari_nama, hari_kode in DAYS:
    for sesi_num, jam_mulai, jam_selesai, jam_label in SESSIONS:
        TIMESLOTS.append({
            "kode":       f"{hari_kode}_s{sesi_num}",
            "hari":       hari_nama,
            "sesi":       sesi_num,
            "jam_mulai":  jam_mulai,
            "jam_selesai": jam_selesai,
            "label":      f"{hari_nama} {jam_label}",
            "sks":        3,
        })

# ---------------------------------------------------------------------------
# Default admin credentials
# ---------------------------------------------------------------------------

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


def _hash_password(plain: str) -> str:
    """Hash password menggunakan bcrypt langsung."""
    import bcrypt
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def seed_timeslots(db) -> None:
    existing_codes = {row.kode for row in db.query(Timeslot.kode).all()}
    inserted = 0
    for data in TIMESLOTS:
        if data["kode"] in existing_codes:
            continue
        db.add(Timeslot(**data))
        inserted += 1
    db.flush()
    print(f"  Timeslot: {inserted} inserted, {len(existing_codes)} already exist")


def seed_admin(db) -> None:
    existing = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    if existing:
        print(f"  Admin user '{ADMIN_USERNAME}' already exists — skipped")
        return
    admin = User(
        username=ADMIN_USERNAME,
        password_hash=_hash_password(ADMIN_PASSWORD),
        role=UserRole.admin.value,
        is_active=True,
    )
    db.add(admin)
    db.flush()
    print(f"  Admin user '{ADMIN_USERNAME}' created")


def run() -> None:
    print("Running seed...")
    db = SessionLocal()
    try:
        seed_timeslots(db)
        seed_admin(db)
        db.commit()
        print("Seed completed successfully.")
    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
