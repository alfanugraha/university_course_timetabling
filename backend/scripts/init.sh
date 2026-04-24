#!/bin/bash
# backend/scripts/init.sh
# First-run initialization script for CTS API container.
# Runs: DB readiness check → Alembic migrations → seed data → start uvicorn
#
# NOTE: On Windows hosts, ensure this file has LF line endings (not CRLF).
#       Run: git config core.autocrlf false  OR  dos2unix scripts/init.sh
#       The file must also be executable inside the container; this is handled
#       by the Dockerfile (chmod +x scripts/init.sh).

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log()  { echo "[init] $*"; }
err()  { echo "[init] ERROR: $*" >&2; }

# ---------------------------------------------------------------------------
# 1. Wait for PostgreSQL to be ready
# ---------------------------------------------------------------------------

log "Waiting for PostgreSQL to be ready..."

MAX_RETRIES=30
RETRY_INTERVAL=2
attempt=0

until python - <<'PYEOF'
import os, sys
try:
    import psycopg2
    url = os.environ.get("DATABASE_URL", "")
    # Convert SQLAlchemy URL to psycopg2-compatible URL if needed
    url = url.replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(url, connect_timeout=3)
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
PYEOF
do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge "$MAX_RETRIES" ]; then
        err "PostgreSQL did not become ready after $((MAX_RETRIES * RETRY_INTERVAL)) seconds. Aborting."
        exit 1
    fi
    log "  PostgreSQL not ready yet (attempt $attempt/$MAX_RETRIES). Retrying in ${RETRY_INTERVAL}s..."
    sleep "$RETRY_INTERVAL"
done

log "PostgreSQL is ready."

# ---------------------------------------------------------------------------
# 2. Run Alembic migrations
# ---------------------------------------------------------------------------

log "Running Alembic migrations..."
alembic upgrade head
log "Migrations complete."

# ---------------------------------------------------------------------------
# 3. Run seed script
# ---------------------------------------------------------------------------

log "Running seed script (admin)..."
python -m scripts.seed
log "Running seed_master (master data)..."
python -m scripts.seed_master
log "Seed complete."

# ---------------------------------------------------------------------------
# 4. Start the application
# ---------------------------------------------------------------------------

log "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
