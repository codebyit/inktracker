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

---

## ⚠️ Public-repo divergences — PRESERVE, do not clobber (as of 2026-06-28)

The public repo (`codebyit/inktracker`) has hardening that the private source
(`inventario/inktrack`) does **not** have yet. A naive copy from private → public
would **downgrade dependencies, revert the base image, and delete governance files.**
When porting feature changes, keep the public values below unless intentionally bumping.

### 1. Dependency pins — public is AHEAD (copying private would reintroduce 4 starlette CVEs)
Keep the public `requirements.txt` pins (do not overwrite with the older private ones):

| package | private (old) | public (keep) |
|---|---|---|
| fastapi | `>=0.116.0,<0.130.0` | `>=0.138.1,<0.140.0` |
| starlette | `>=0.49.1` | `>=1.3.1` |
| uvicorn[standard] | `==0.30.0` | `==0.49.0` |
| python-multipart | `>=0.0.27` | `>=0.0.32` |
| aiofiles | `==23.2.1` | `==25.1.0` |
| psycopg[binary] | `>=3.3.3` | `>=3.3.4` |
| python-dotenv | `>=1.0.1` | `>=1.2.2` |
| alembic | `>=1.13.2` | `>=1.18.5` |
| redis | `>=5.0.8` | `>=8.0.1` |
| pyyaml | `>=6.0.1` | `>=6.0.3` |
| reportlab | `>=4.2.2` | `>=5.0.0` |

(`sqlalchemy==2.0.32`, `jinja2>=3.1.6` unchanged.)

### 2. Base image — keep `python:3.14-slim`
Public `Dockerfile` uses `FROM python:3.14-slim` (validated: manylinux cp314 wheels exist
for all C-extension deps). Do **not** revert to `python:3.12-slim`.

### 3. Starlette fix approach — public uses the REAL fix, not suppression
Private suppressed the advisory via `pip-audit --ignore-vuln` + `starlette>=0.49.1`.
Public upgraded to `starlette>=1.3.1` + `fastapi>=0.138.1`. When porting, adopt the public
upgrade and **drop the pip-audit suppression** for the starlette advisories.

### 4. Public-only files — keep, never delete on sync
- `SECURITY.md` (GitHub Private Vulnerability Reporting + email fallback)
- `CODE_OF_CONDUCT.md`
- `.github/dependabot.yml`
- `.github/workflows/codeql.yml` (public-only; private intentionally disables CodeQL)
- `.github/workflows/public-ci.yml` (action versions bumped: checkout v7, setup-python v6,
  docker setup-buildx v4 / metadata v6 / build-push v7 / login v4)

### 5. Deferred in public (do NOT auto-apply)
- Tailwind CSS **v4** upgrade is intentionally held (public PR #18 open). `package.json`
  stays on `tailwindcss ^3.4.1` until a deliberate v4 migration.

### Do NOT copy (extends the "Do NOT copy" list above)
- `inktracker.db` / any `*.db`, `.env`
- `.github/workflows/inklab-security.yaml` (internal CI)
- `tailwind.config.js` (only if public continues to build without it)
- Internal-only docs: `BUILD_LOG.md`, `PUBLIC_REPOSITORY_BRAINSTORM.md`, `ROADMAP.md`,
  `SECURITY_AUDIT_2026-05-24.md`, `TECHNICAL_REFERENCE.md`, `*.agent.md`, `AGENTS.md`,
  Proxmox/deploy scripts
