# alembic/env.py
# Konfigurasi Alembic — membaca DATABASE_URL dari environment

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object (akses ke nilai dalam alembic.ini)
# ---------------------------------------------------------------------------
config = context.config

# Setup logging dari alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Override sqlalchemy.url dengan DATABASE_URL dari environment
# ---------------------------------------------------------------------------
# Prioritas: env var DATABASE_URL → fallback ke app.config.settings
database_url = os.environ.get("DATABASE_URL")

if not database_url:
    try:
        from app.config import settings
        database_url = settings.database_url
    except Exception:
        pass

if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# ---------------------------------------------------------------------------
# target_metadata untuk autogenerate support
# Import Base dari database.py; model-model akan terdaftar otomatis
# saat model files di-import.
# ---------------------------------------------------------------------------
try:
    from app.database import Base  # noqa: F401

    # Import semua model agar metadata-nya terdaftar ke Base
    # Tambahkan import di sini seiring model dibuat
    try:
        import app.models  # noqa: F401 — package-level import jika ada __init__.py
    except ImportError:
        pass

    target_metadata = Base.metadata
except Exception:
    target_metadata = None


# ---------------------------------------------------------------------------
# Offline migration mode
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Jalankan migrasi dalam mode 'offline' (tanpa koneksi DB aktif).

    Menghasilkan SQL script yang bisa dijalankan manual.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration mode
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """Jalankan migrasi dalam mode 'online' (dengan koneksi DB aktif)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
