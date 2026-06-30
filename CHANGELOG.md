# Changelog

All notable changes to InkTracker (public fork) are documented here.
Format: [Semantic Versioning](https://semver.org) — `MAJOR.MINOR.PATCH`.

This fork keeps an **independent version sequence** from the internal source repo; each entry
records the internal baseline it derives from where applicable (see `VERSIONING.md`).

---

## [0.11.0] — 2026-06-30

### Added

- **Windows desktop app.** InkTrack now ships as a standalone Windows build: the
  same FastAPI application run inside a native window via pywebview (SQLite-only,
  no server, no Docker). User data lives under `%LOCALAPPDATA%\InkTrack`. A
  PyInstaller **onedir** bundle is packaged as a per-user **Inno Setup installer**
  (Start-menu/uninstall, WebView2 bootstrap, data preserved on uninstall) and as
  a **portable ZIP**. New `desktop-windows.yml` workflow builds, smoke-tests the
  packaged binary, and attaches the installer + portable to the GitHub Release on
  a `v*` tag. See [`BUILD.md`](BUILD.md).
- **Code signing (gated) via the SignPath Foundation** and **Microsoft Store MSIX
  packaging (gated).** A `sign` job code-signs the release binaries and a `msix`
  job builds a Store package; both activate only once the corresponding repository
  variables/secrets are configured, so the core build stays green until then.
  Added `packaging/` (tokenized `AppxManifest.xml`, Store assets, `make-msix.ps1`).
- **Configurable per-user data directory.** `INKTRACK_DATA_DIR` relocates the
  SQLite database, uploads, and `docs_links.yaml` outside the install tree; a new
  `app/paths.py` centralizes writable-path and frozen-resource (`sys._MEIPASS`)
  resolution. When unset, the historical in-repo paths are unchanged.

### Fixed

- **SQLite-safe primary keys in the initial-schema migrations.** The bootstrap
  migrations created tables with PostgreSQL-only `id SERIAL PRIMARY KEY`; on
  SQLite that is not an autoincrement rowid alias, so seed inserts stored `NULL`
  ids and `seed_defaults` could crash on a fresh SQLite database. Primary keys are
  now dialect-aware (`INTEGER PRIMARY KEY` on SQLite). No-op for existing and
  PostgreSQL databases.

Public-originated release (no internal counterpart for the Windows desktop build).

## [0.10.0] — 2026-06-29

### Added

- **Configurable ink density (per channel) and cartridge tare (global).** The weight →
  remaining-ink helper on the Service page no longer assumes 1 ml = 1 g. It now computes
  `remaining_ml = (weight_g − tare) ÷ density`, with each channel's density and a global
  empty-cartridge tare set in **Settings → Ink**. Defaults (density 1.0, tare 75 g) preserve
  the previous behavior. Migration `0016` (additive, SQLite/PostgreSQL-safe).

### Changed

- **Settings → Ink Cost Setup** redesigned as per-channel bordered cards (colored dot +
  name, compact price box with price/ml, and a labeled Density box in g/ml).

Ported from internal v0.10.0.

## [0.9.2] — 2026-06-29

### Fixed

- **Stale theme/CSS behind a reverse proxy.** `app.css` and the vendored JS had fixed
  URLs, so the service worker (cache-first) and the proxy kept serving old CSS after a
  deploy — causing inconsistent dark/light mode and requiring a hard refresh. Asset URLs
  now carry a `?v=<app.css mtime>` cache-buster (changes every build) and the
  service-worker `CACHE_NAME` was bumped (`v2` → `v3`) to purge stale caches.

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
