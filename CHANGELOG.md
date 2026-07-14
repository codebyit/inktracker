# Changelog

All notable changes to InkTracker (public fork) are documented here.
Format: [Semantic Versioning](https://semver.org) — `MAJOR.MINOR.PATCH`.

This fork keeps an **independent version sequence** from the internal source repo; each entry
records the internal baseline it derives from where applicable (see `VERSIONING.md`).

---

## [0.15.0] — 2026-07-14

A focused polish of the **Service** and ink-tracking experience. Additive and data-safe;
no schema changes.

### Added

- **Undo on every ink-correction row.** The Service Action Log now shows a persistent
  **Undo** button on each ink-correction entry (not just the transient "saved" toast),
  reverting ink levels to before the correction. (Fixes #97)
- **Per-ink breakdown in the Service Action Log.** Correction rows are expandable to show
  the ml change for **each channel**, instead of only the summed total. (Fixes #96)

### Changed

- **Ink corrections are now absolute — "Set Current Ink Level".** Enter each cartridge's
  actual remaining ml (fields prefilled with the current tracked level) and the app computes
  the adjustment, replacing the error-prone +/- delta form. A live per-channel **"→ new
  value"** badge previews the change, and the save button stays disabled (**"No changes to
  save"**) until a value actually differs.
- **Cleaning + Moisturizing Liquid are one UV Cleaning Cartridge.** Shown as a single card
  with both compartments, one replacement count, and one **Replace** that resets both
  channels — matching the physical hardware.
- **Dismissible "correction saved" toast** with a close button and an auto-hide countdown
  that pauses on hover.

### Fixed

- **Ink levels are clamped to 0–100%.** The derived level previously had no upper bound, so a
  negative correction on an over-consumed channel (displayed as 0%) could jump unexpectedly or
  exceed 100%. Corrections now land exactly on the entered value. (Fixes #98)
- **Toggle switches are visible in light mode.** Added a reusable `.ui-toggle` component so
  on/off switches (Settings, Inventory "mark in use", and the project wizard) render clearly
  in both light and dark themes.
- **Robust Service Action Log rendering.** The log payload is now built and sanitized
  server-side (non-finite floats coerced to 0), so a single legacy row can no longer break
  `JSON.parse` and hide the entire log.

_Ported from internal `main` (merge commit `038c618`)._

---

## [0.14.0] — 2026-07-14

### Added

- **Cartridge-lot expiry alerts.** A configurable **Expiry Alert Window**
  (Settings → Preferences, default 30 days) drives soon/expired badges across
  **Inventory**, a filter bar (All / Expiring / Expired / In use), and a **"Use
  next"** FEFO indicator that points to the earliest-expiring available lot per
  channel (earliest of chip or box expiry). The **Dashboard** gains a dismissible
  expiry banner with snooze (1 day / 1 week / 1 month), and the **Inventory PDF**
  gains an **Expiring & Expired Lots** section, most-urgent first.
- **eufyMake per-channel maintenance model.** Cleaning (CLN) and moisturizing
  (ML) consumption is now modelled across **6 active channels** (C, M, Y, K,
  W|FW, GL), with White as a single slot (`W` XOR `FW`). New service presets:
  **White Ink Flash Cleaning**, **White Line Swap (Hard ↔ Soft)**, and **Ink
  Injection (after Moisturizing)**. Canonical reference: `docs/maintenance-rules.md`.
- **Service Action Log retention.** Configurable **Archive after (days)** and
  **Delete after (days)** windows (Settings → Preferences) with a daily scheduler
  purge and a **Show archived** filter, plus date / quick-range / search filtering,
  sorting, and header help on the log.

### Changed

- **Extended Shutdown Restart** now models an **ink injection** rather than a full
  15 ml/channel initial fill.
- **Inventory → Add Cartridge Lot** redesigned as a mobile-friendly modal (aligned
  identity/expiry blocks + action rail); chip and box expiry default to one year
  ahead. QR scan controls are now icons, with a **Box Expiry** camera/image scan
  that auto-extracts the date.

### Fixed

- **Moisturizing Liquid capacity 500 → 125 ml** to match the real UV Cleaning
  Cartridge compartment (cleaning 255, moisturizer 125, waste 125). CLN/ML are no
  longer overwritten by the global ink-capacity sync.
- **Mark-in-use toggle contrast** in light and dark mode (grey off / green on).

Ported from internal v0.13.0 (commit 89b9a1f).

## [0.13.1] — 2026-07-02

### Fixed

- **Desktop:** the "update available" banner is no longer shown on **Microsoft
  Store** installs. Those builds update through the Store itself, so surfacing a
  GitHub download link both bypassed the Store and could point users at a release
  the Store had not yet published. Installer and portable builds are unaffected
  and still show the banner. Detection uses the Windows package-identity API
  (`GetCurrentPackageFullName`), so non-packaged builds behave exactly as before.

## [0.13.0] — 2026-07-02

### Added

- **First-time setup wizard.** A fresh install now shows a dismissible "Finish
  your setup" banner on the Dashboard that launches a guided, full-screen wizard:
  **Currency → Printer → Machine → Ink → (optional) Labour & Margins → Review**.
  It pre-fills sensible defaults and writes through the existing settings, so cost
  and profit numbers are accurate from day one. Works identically on the Docker /
  self-hosted web app and the Windows desktop build. Re-runnable anytime from
  **Settings → Preferences → Run setup wizard**.
- **More currencies.** Currency selection expands from € / $ to five options —
  **Euro (€), British Pound (£), US Dollar ($), Canadian Dollar (CA$), and
  Australian Dollar (A$)** — available in both the wizard and Settings.
- **Printer presets.** A new `app/printer_presets.py` defines printer models
  (currently **Eufymake E1** plus **Other / Custom**) with their machine and ink
  defaults, including per-currency cartridge prices. New models can be added in
  code without a migration. Picking a printer in the wizard pre-fills cartridge
  capacity, tare weight, and ink price.

### Changed

- Seeded defaults for a **fresh database** now come from the Eufymake E1 preset.
  The default colour-ink price per cartridge is corrected from `45.00` to the real
  E1 EUR price **`42.99`**. Existing installs are unaffected (seeding only fills
  empty rows).

### Fixed

- **Settings → Ink → Ink Cost Setup:** widened the price and density inputs so
  longer currency symbols (e.g. `CA$`) no longer clip the last digit of the value.

### Notes

- New `feature_config.setup_completed` flag + migration `0018_setup_completed`
  (additive, SQLite-safe). **Existing installs are backfilled to "completed"** so
  they are never prompted to onboard.

## [0.12.0] — 2026-07-01

### Added

- **Multiple craft modes are now a Settings toggle.** The multi-craft feature
  (several craft faces per project in the New Project wizard) is now controlled
  from **Settings → Preferences → Features** instead of the `MULTI_CRAFT_ENABLED`
  environment variable, so it works the same way in the Docker and Windows
  desktop builds. It is **enabled by default**. Existing single-craft projects
  are unaffected.

### Changed

- The `MULTI_CRAFT_ENABLED` environment variable is now only a one-time seed for
  the initial value on a fresh database; the in-app setting is the source of
  truth thereafter. New `feature_config` table + migration `0017_feature_config`
  (additive, SQLite-safe, seeds from the env var when explicitly set, otherwise
  defaults to enabled).

### Fixed

- **Project status pill did nothing when clicked.** The status badge on the
  Projects list passed the project name into the click handler with `| tojson`,
  whose double quotes collided with the double-quoted HTML attribute and broke
  the Alpine expression, so the "Set Project Status" modal never opened (most
  visible in the Windows desktop app). The name/id/status are now passed via
  `data-*` attributes, so any project name (including quotes/apostrophes) works.

## [0.11.2] — 2026-07-01

### Fixed

- **Windows desktop app failed to launch (installer and portable).** On a normal
  double-click the app did nothing and showed no error. The windowed (no-console)
  build has `sys.stdout`/`sys.stderr` set to `None`; constructing the local
  uvicorn server runs its default logging setup, whose formatter calls
  `sys.stdout.isatty()` and raised `AttributeError: 'NoneType' object has no
  attribute 'isatty'` (`ValueError: Unable to configure formatter 'default'`),
  killing startup before the window opened. The launcher now guarantees writable
  `stdout`/`stderr` streams first thing at startup — pointing any missing stream
  at a per-user `inktrack-runtime.log` (falling back to `os.devnull`) — so the
  server and window start normally.

### Changed

- **CI can no longer hide this class of failure.** The packaged smoke-test now
  reproduces the real windowed no-console condition (`INKTRACK_SIMULATE_NO_CONSOLE`)
  instead of masking it with redirected stdio, so a regression fails the build.

## [0.11.1] — 2026-07-01

### Fixed

- **Portable ZIP failed if run from inside the archive.** Double-clicking
  `InkTrack.exe` directly inside the zip made Windows extract only the exe to a
  temp folder without its `_internal\` DLLs, causing `Failed to load Python DLL …
  python314.dll — The specified module could not be found`. The portable download
  is now packaged with a top-level `InkTrack\` folder and a `READ ME FIRST.txt`,
  so users extract it first and run `InkTrack\InkTrack.exe`. The installer was
  never affected.

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
