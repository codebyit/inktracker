---
title: What's New
---

# What's New in InkTracker

InkTracker is a free, open-source cost & inventory tracker for UV printing. This page
summarizes recent and upcoming releases. For exact, version-anchored notes and downloads,
see the [GitHub Releases](https://github.com/codebyit/inktracker/releases).

> **Availability:** the Docker / self-hosted web app updates immediately on each release.
> The **Microsoft Store** desktop build follows after certification (24 h–3 days), so its
> "generally available" date lands a few days after the release tag.

---

## v0.16.0 — _Available now_

The [v0.16.0 release](https://github.com/codebyit/inktracker/releases/tag/v0.16.0) sharpens the
project wizard, links your Bill of Materials to the Materials library, and hardens the web app.
It's additive and data-safe — existing databases upgrade in place.

**Project wizard fixes**
- **Edit keeps what you saved.** A project saved with **white underbase choke = 0.00 mm** or
  **Include Pre-Prime Ink = off** now re-opens in Edit with exactly those settings (previously
  they silently reverted). The pre-prime choice is remembered per project.
- **Legible in dark mode.** The "White Ink Type" labels (Standard / Flexible White) now read
  clearly on the New Project screen in dark mode.

**Bill of Materials ↔ Materials library**
- BOM **Item Name autocompletes** from your Materials library and **prefills** unit cost, unit,
  and category when you pick a known material.
- Opt in to **save new BOM items to your library**, and library-linked items **track stock
  consumption** for the project (reconciled when you edit). Free-text items still work.

**Printer-aware quality list**
- The **Quality** dropdown now matches your printer: **eufyMake** hides the non-existent
  **"Ultra"** setting, while Other/Custom printers keep the full list. Set your printer under
  **Settings → Machine → Printer Profile**.

**Security hardening**
- Safer rendering of wizard data (no HTML injection), **documentation links restricted to
  http/https**, and the interactive API docs are **off by default** in production.

---

## v0.15.0 — _Available now_

**Ink corrections, reimagined**
- **"Set Current Ink Level"** — type each cartridge's actual remaining ml (fields start at
  the current value); the app works out the adjustment. No more +/- guesswork.
- A live **"→ new value"** preview per channel, and the save button stays disabled until
  something actually changes — no accidental no-ops.
- The Service Action Log shows a correction as a **level change** (green = ink added,
  red = ink removed) and lets you **expand each entry for the per-ink breakdown**.
- Every correction has an **Undo**; the "saved" pop-up is now dismissible and auto-hides.
- Ink levels are correctly **capped at 0–100%**, so a correction lands exactly where you set it.

**Cleaning cartridge as one part**
- **Cleaning + Moisturizing Liquid** now appear as a single **UV Cleaning Cartridge** — one
  card with both compartments, one replacement count, and one **Replace** that resets both.

**Cartridge-lot expiry management**
- **Expiry alerts** with a configurable warning window (Settings → Preferences).
- Inventory **badges and filters** (Expiring / Expired / In use) and a **"Use next"**
  indicator that points you to the earliest-expiring lot so nothing is wasted.
- A dismissible, snooze-able **dashboard banner** when lots need attention, and an
  **Expiring & Expired Lots** section in the inventory PDF export.

**Printer maintenance accuracy (eufyMake E1)**
- Cleaning and moisturizing fluid usage is now modeled **per ink channel** to match the
  manufacturer's published consumption, so cartridge refill timing is accurate.
- New maintenance actions: **White Ink Flash Cleaning**, **White Line Swap (Hard ↔ Soft)**,
  and a post-moisturize **Ink Injection**. Configurable service-log **archive/delete** windows.

**Interface fixes**
- **Toggle switches are clearly visible** in both light and dark mode.
- Redesigned mobile-friendly **Add Cartridge Lot** form with **Box Expiry QR scan**, clearer
  help tooltips, better button spacing, and a more robust maintenance log.

> **Get it:** Docker / self-hosted — `docker compose pull && up -d`. Windows — via the
> **Microsoft Store** or the direct downloads on the
> [release page](https://github.com/codebyit/inktracker/releases/tag/v0.15.0).

---

## Released

See the [full changelog](https://github.com/codebyit/inktracker/blob/main/CHANGELOG.md) and
[Releases](https://github.com/codebyit/inktracker/releases) for every version, including the
Windows desktop app, the first-time setup wizard, printer presets, and the security &
dependency hardening.

---

_The Store build goes live after Microsoft Store certification completes; Docker / self-hosted
updates are available immediately on each release._
