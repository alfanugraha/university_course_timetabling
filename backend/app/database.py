# backend/app/database.py
# SQLAlchemy engine, SessionLocal, dan get_db() dependency

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.base import Base  # noqa: F401 — re-export agar Alembic bisa detect

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yield DB session dan tutup setelah request selesai."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
