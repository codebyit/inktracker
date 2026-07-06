# Port Manifest — internal v0.13.0 → public v0.14.0

What to bring from the internal source repo into this public fork for the next release, and
what must be **preserved** (the public fork is ahead on security/deps/governance). Pairs with
`RELEASE_PLAN.md` and the internal `PUBLIC_FORK_DIVERGENCE.md`.

## Baselines

| | Version | Alembic head |
|---|---|---|
| **Public (this fork)** | v0.13.1 | `0018_setup_completed` |
| **Internal source** | v0.13.0 | `0023_expiry_alert_days` |
| **This release (public)** | **v0.14.0** | `0023_expiry_alert_days` |

The public migration chain ends at exactly `0018`, matching the internal numbering (same
merge structure, same `c463253ff49b` stray head). Internal migrations **0019–0023 append
cleanly** onto the public head — no renumbering needed.

## What to PORT (app-layer only)

### Feature: eufyMake per-channel maintenance model
- Per-channel cleaning (CLN) and moisturizing (ML) consumption × **6 active channels**
  (C, M, Y, K, W|FW, GL). White is a single slot (`W` XOR `FW`).
- New service presets: **White Ink Flash Cleaning**, **White Line Swap (Hard ↔ Soft)**,
  **Ink Injection (after Moisturizing)**.
- **Extended Shutdown Restart** = ink injection (not a full 15 ml/ch initial fill).
- Canonical reference doc: `docs/maintenance-rules.md`.
- Migrations: `0019_maintenance_consumption`, `0020_ml_capacity_125`, `0022_white_swap_both_whites`.

### Fix: Moisturizing Liquid capacity
- ML cartridge compartment 500 → **125 ml** (real UV Cleaning Cartridge: cleaning 255,
  moisturizer 125, waste 125). CLN/ML no longer overwritten by the global ink-capacity sync.
- Migration: `0020_ml_capacity_125`.

### Feature: Service Action Log retention
- Configurable **Archive after (days)** / **Delete after (days)** in Settings → Preferences.
- Daily scheduler purge; **Show archived** filter on the log.
- Migration: `0021_service_log_retention`.

### Feature: Cartridge-lot expiry alerts
- Configurable **Expiry Alert Window** (Settings → Preferences, default 30 days).
- Inventory: soon/expired badges, filter bar (All / Expiring / Expired / In use), and a
  **"Use next"** FEFO indicator (earliest-expiring available lot per channel; earliest of
  chip/box expiry).
- Dashboard: dismissible + snooze (1 day / 1 week / 1 month) expiry banner.
- Inventory PDF: **Expiring & Expired Lots** section, most-urgent first.
- Migration: `0023_expiry_alert_days`.

### UI polish
- Inventory: QR scan buttons → icons; **Box Expiry** camera/image scan with date auto-extract;
  **Add Cartridge Lot** redesigned as a mobile-friendly modal (aligned identity/expiry blocks +
  action rail); chip/box expiry default to one year ahead; **Mark-in-use** toggle contrast
  (grey off / green on).
- Settings: floating **Overhead (%)** help tooltip.
- Service: **Cartridge Replacements** grey out the non-loaded white with a link to Settings;
  **Service Action Log** date/quick-range/search filter + sort + header help; hardware-event
  forms show only the channels a preset consumes.

### Migrations to port (append onto public `0018`)
1. `0019_maintenance_consumption.py`
2. `0020_ml_capacity_125.py`
3. `0021_service_log_retention.py`
4. `0022_white_swap_both_whites.py`
5. `0023_expiry_alert_days.py`

> Put migrations in the public repo's `alembic/versions/` (app is at repo **root** — no
> `inktrack/` prefix). This exact wrong-folder mistake cost a broken deploy internally;
> double-check the destination path.

## What to PRESERVE (do NOT overwrite from internal)

- **Dependency pins** — public is ahead (older pins reintroduce 4 starlette CVEs):
  fastapi `>=0.138.1`, starlette `>=1.3.1`, uvicorn `==0.49.0`, and the rest per
  `PUBLIC_FORK_DIVERGENCE.md`.
- **Docker base image** `python:3.14-slim` (do not revert to 3.12).
- **Real starlette fix** (`starlette>=1.3.1`), not the internal pip-audit suppression.
- **Public-only files:** `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/dependabot.yml`,
  `.github/workflows/codeql.yml`, `.github/workflows/public-ci.yml`.
- **Tailwind CSS v3** (v4 intentionally held).
- **Independent version sequence** — do not copy internal `VERSION`/`package.json`; bump
  public to **v0.14.0** and add the CHANGELOG footer
  `Ported from internal v0.13.0 (commit 89b9a1f)`.

## Never push to public
`.env`, any `*.db`, internal-only workflows/docs (`inklab-security.yaml`, `AGENTS.md`,
Proxmox/deploy scripts, internal audit/roadmap docs).

## Suggested public CHANGELOG entry (skeleton)

```
## [0.14.0] — <date>

### Added
- Cartridge-lot expiry alerts (configurable window, Inventory badges/filter, FEFO "use next",
  dashboard banner, PDF section).
- eufyMake per-channel maintenance model (×6 CLN/ML, W XOR FW, White Ink Flash Cleaning,
  White Line Swap, Ink Injection after Moisturizing).
- Service Action Log retention (archive/delete windows + show-archived filter).

### Changed
- Extended Shutdown Restart now an ink injection (not a full initial fill).
- Inventory Add Cartridge Lot redesigned as a modal; chip/box expiry default one year ahead.

### Fixed
- Moisturizing Liquid capacity 500 → 125 ml (real compartment); CLN/ML no longer clobbered by
  the global ink-capacity setting.
- Mark-in-use toggle contrast in light and dark mode.

Ported from internal v0.13.0 (commit 89b9a1f).
```
