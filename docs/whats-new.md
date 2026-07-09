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

## Coming soon — v0.15.0 · _Target GA: coming weeks_

A focused polish of the **Service** and **ink-tracking** experience, based on real feedback.
Nothing changes your data — it just makes correcting ink levels and reading the maintenance
log clearer and harder to get wrong.

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

**Interface fixes**
- **Toggle switches are clearly visible** in both light and dark mode.
- A clearer help tooltip on the cartridge-replacement section, better button spacing, and a
  more robust maintenance log that keeps displaying correctly even with lots of history.

---

## Coming soon — v0.14.0 · _Target GA: July 22, 2026_

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
