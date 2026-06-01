# Copy Checklist for Public Release

## What to copy from private repo to public repo

**Source:** `c:\Users\petavare\Documents\onedrive-pessoal\OneDrive\Apps\Inventario\inventario\inktrack`
**Target:** `c:\Users\petavare\Documents\onedrive-pessoal\OneDrive\Apps\Inventario\intrack-public`

### Core app code (required)
- [ ] Copy `app/` folder entirely (all Python modules)
- [ ] Copy `static/` folder entirely (CSS, JS, vendor libs)
- [ ] Copy `alembic/` folder entirely (database migrations)
- [ ] Copy `docker-entrypoint.sh` (Docker startup script)
- [ ] Copy `requirements.txt` (Python dependencies) — if different from what's already there

### After copying
1. Run: `git add app/ static/ alembic/ docker-entrypoint.sh VERSION Dockerfile .dockerignore`
2. Run: `git commit -m "feat: add InkTrack app code (v0.8.16)"`
3. Run: `git push`

### Do NOT copy
- `.github/workflows/inklab-security.yaml` (internal CI only)
- Any `.env` files with secrets
- `*.db` SQLite files
- `uploads/` directory
- `postgres_data/`, `redis_data/` directories
- Any Proxmox-specific scripts

### Files already in public repo
- `docker-compose.public.yml`, `docker-compose.external-db.yml`
- `requirements.txt` — compare/update if newer in private
- `.env.example`
- Governance docs (README, LICENSE, etc.)
