# Changelog

All notable changes to InkTracker (public fork) are documented here.
Format: [Semantic Versioning](https://semver.org) — `MAJOR.MINOR.PATCH`.

This fork keeps an **independent version sequence** from the internal source repo; each entry
records the internal baseline it derives from where applicable (see `VERSIONING.md`).

---

## [0.9.1] — 2026-06-29

### Fixed

- **Settings → Ink:** the Pre-Prime Inputs fields no longer overflow the card border.
  The number inputs used `flex-1` without `min-w-0`, so they could not shrink below their
  intrinsic width and pushed the right grid column past the card. Added `min-w-0`.

## [0.9.0] — 2026-06-28

First versioned release of the public fork after the security-hardening and
dependency-modernization wave. Consolidates everything merged since `v0.8.17`.

### Added

- **Security & governance:** GitHub Private Vulnerability Reporting plus an email fallback
  (`SECURITY.md`, `CODE_OF_CONDUCT.md`), Dependabot configuration, and a CodeQL scanning
  workflow (`.github/workflows/codeql.yml`).
- **Versioning policy & tooling:** `VERSIONING.md`, `VERSION` as the single source of truth,
  `scripts/sync-version.mjs` + `scripts/prepare-release.mjs`, `version:sync`/`version:check`
  npm scripts, and the Version Guard / Suggest Next Version / Release workflows.
- **Fork divergence docs:** the public-fork "preserve, do not clobber" guidance (maintainer
  copy checklist; now kept in the private source repo).

### Changed

- **Python base image** bumped `3.12-slim` → `3.14-slim` (validated against manylinux cp314
  wheels for all C-extension dependencies).
- **Dependency upgrades:** uvicorn `0.30.0`→`0.49.0`, aiofiles `23.2.1`→`25.1.0`,
  redis `>=5.0.8`→`>=8.0.1`, alembic `>=1.13.2`→`>=1.18.5`, reportlab `>=4.2.2`→`>=5.0.0`,
  python-multipart, python-dotenv `>=1.0.1`→`>=1.2.2`, pyyaml `>=6.0.1`→`>=6.0.3`,
  psycopg `>=3.3.3`→`>=3.3.4`.
- **CI action bumps:** checkout, setup-python, codeql-action, docker/* actions to current majors.

### Fixed

- **Starlette CVEs (real fix):** bumped FastAPI/Starlette (`fastapi>=0.138.1`,
  `starlette>=1.3.1`) to patch 4 starlette advisories, replacing the prior `pip-audit`
  suppression. CI dependency-install and audit workflow fixes.

> Public-originated release (security/dependency hardening with no internal counterpart).
> Internal baseline at time of writing: internal `v0.9.0` (commit `cd3950d`).
