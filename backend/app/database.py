# backend/app/database.py
# SQLAlchemy engine, SessionLocal, dan get_db() dependency

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.base import Base  # noqa: F401 — re-export agar Alembic bisa detect

engine = create_engine(
    settings.database_url,
    # ── Neon serverless / cold-start hardening ─────────────────────────────
    # Neon free tier scales to zero after ~5 min idle. Existing pool connections
    # become stale when the compute restarts. pool_pre_ping issues a lightweight
    # SELECT 1 before handing out a connection; stale ones are discarded and
    # replaced transparently instead of failing mid-request.
    pool_pre_ping=True,
    # Recycle connections after 4 minutes so they are never handed back to the
    # pool when they are close to Neon's ~5-min server-side timeout.
    pool_recycle=240,
    # Keep the pool small — Neon free tier allows only 5 concurrent connections.
    pool_size=3,
    max_overflow=2,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yield DB session dan tutup setelah request selesai."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
