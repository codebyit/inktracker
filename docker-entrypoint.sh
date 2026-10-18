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
echo "INFO  [entrypoint] Running database migrations..."
python -m app.migration_runner
echo "INFO  [entrypoint] Migrations complete."

# ── Start application ─────────────────────────────────────────────────────────
echo "INFO  [entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
