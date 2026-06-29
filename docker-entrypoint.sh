#!/bin/sh
set -e

# ── Wait for PostgreSQL to be ready ──────────────────────────────────────────
# Skipped automatically when DATABASE_URL is not set (SQLite dev mode).
python - <<'EOF'
import os, sys, time
from sqlalchemy import create_engine, text

raw_url = os.environ.get("DATABASE_URL", "")
if not raw_url or raw_url.startswith("sqlite"):
    print("INFO  [entrypoint] SQLite mode — skipping PostgreSQL readiness check.")
    sys.exit(0)

url = raw_url
if url.startswith("postgresql://") or url.startswith("postgres://"):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1) \
             .replace("postgres://", "postgresql+psycopg://", 1)

for attempt in range(30):
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        print(f"INFO  [entrypoint] PostgreSQL is ready (attempt {attempt + 1}).")
        sys.exit(0)
    except Exception as exc:
        print(f"WARN  [entrypoint] PostgreSQL not ready (attempt {attempt + 1}/30): {exc}")
        time.sleep(2)

print("ERROR [entrypoint] PostgreSQL did not become ready after 60s. Aborting.")
sys.exit(1)
EOF

# ── Run database migrations ───────────────────────────────────────────────────
# If app tables already exist but alembic_version is empty, stamp to the latest
# revision so Alembic does not try to re-create existing tables from scratch.
echo "INFO  [entrypoint] Checking migration state..."
python - <<'EOF'
import os, sys
from sqlalchemy import create_engine, text

raw_url = os.environ.get("DATABASE_URL", "")
if not raw_url or raw_url.startswith("sqlite"):
    sys.exit(0)

url = raw_url
if url.startswith("postgresql://") or url.startswith("postgres://"):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1) \
             .replace("postgres://", "postgresql+psycopg://", 1)

engine = create_engine(url, connect_args={"connect_timeout": 3})
with engine.begin() as conn:
    av_exists = conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version'"
    )).fetchone()
    tables_exist = conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name='machine_config'"
    )).fetchone()

    if av_exists:
        rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        versions = [r[0] for r in rows]
        known = {"20260503_01", "0001", "0002_merge_heads", "0003_lifecycle", "0004_craft_mode"}
        orphans = [v for v in versions if v not in known]
        if orphans:
            print(f"WARN  [entrypoint] Removing orphan revisions: {orphans}")
            for v in orphans:
                conn.execute(text("DELETE FROM alembic_version WHERE version_num = :v"), {"v": v})
            rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
            versions = [r[0] for r in rows]
        print(f"INFO  [entrypoint] alembic_version rows: {versions}")
        # If the table exists but is empty AND app tables are present, stamp directly.
        if not versions and tables_exist:
            print("INFO  [entrypoint] alembic_version empty with existing schema — stamping to 0002_merge_heads")
            conn.execute(text("INSERT INTO alembic_version VALUES ('0002_merge_heads')"))
    elif tables_exist:
        # App tables exist but no alembic tracking — stamp to latest so Alembic
        # skips all create-table migrations and only runs additive ones.
        print("INFO  [entrypoint] Schema exists with no alembic_version — stamping to 0002_merge_heads")
        if not av_exists:
            conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"))
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(text("INSERT INTO alembic_version VALUES ('0002_merge_heads')"))
    else:
        print("INFO  [entrypoint] Fresh database — running all migrations.")
engine.dispose()
EOF

echo "INFO  [entrypoint] Running database migrations..."
python -m alembic upgrade heads
echo "INFO  [entrypoint] Migrations complete."

# ── Start application ─────────────────────────────────────────────────────────
echo "INFO  [entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
