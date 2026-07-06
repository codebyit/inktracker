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

## Coming soon — v0.14.0 · _Target GA: July 20, 2026_

**Cartridge-lot expiry management**
- **Expiry alerts** with a configurable warning window (Settings → Preferences).
- Inventory **badges and filters** (Expiring / Expired / In use) and a **"Use next"**
  indicator that points you to the earliest-expiring lot so nothing is wasted.
- A dismissible, snooze-able **dashboard banner** when lots need attention.
- An **Expiring & Expired Lots** section in the inventory PDF export.

**Printer maintenance accuracy (eufyMake E1)**
- Cleaning and moisturizing fluid usage is now modeled **per ink channel** to match the
  manufacturer's published consumption, so cartridge refill timing is accurate.
- New maintenance actions: **White Ink Flash Cleaning**, **White Line Swap (Hard ↔ Soft)**,
  and a post-moisturize **Ink Injection**.

**Service log housekeeping**
- Configurable **archive** and **delete** windows for the service action log, with a
  **Show archived** filter.

**UI polish**
- Redesigned **Add Cartridge Lot** form (mobile-friendly), expiry dates default a year ahead,
  **Box Expiry QR scan**, clearer toggles, and service-log filtering/sorting.

---

## Released

See the [full changelog](https://github.com/codebyit/inktracker/blob/main/CHANGELOG.md) and
[Releases](https://github.com/codebyit/inktracker/releases) for every version, including the
Windows desktop app, the first-time setup wizard, printer presets, and the security &
dependency hardening.

---

_Dates on unreleased items are targets, not commitments; the Store build goes live after
Microsoft Store certification completes._
