# InkTrack v0.15.0

This release combines the **v0.15.0** Service/ink-tracking polish with the **v0.14.0**
cartridge-lot expiry + maintenance features (v0.14.0 shipped only as a Docker beta, so its
features are generally available for the first time here). Additive and **data-safe — no
schema changes**; existing databases upgrade in place.

---

## ✨ Ink corrections, reimagined

- **"Set Current Ink Level."** Corrections are now **absolute** — type each cartridge's actual
  remaining ml (fields prefill with the current tracked level) and the app computes the
  adjustment, replacing the error-prone +/− delta form. A live per-channel **"→ new value"**
  badge previews the change, and the save button stays disabled (**"No changes to save"**)
  until a value actually differs.
- **Per-ink breakdown in the Service Action Log.** Correction rows expand to show the ml change
  for **each channel**, not just the summed total.
- **Undo on every correction row** — not just the transient toast. The "saved" pop-up is now
  dismissible with an auto-hide countdown that pauses on hover.
- **Ink levels are clamped to 0–100%,** so a correction lands exactly where you set it (no more
  surprise jumps on an over-consumed channel).

## 🧽 Cleaning cartridge as one part

- **Cleaning + Moisturizing Liquid** now appear as a single **UV Cleaning Cartridge** — one
  card with both compartments, one replacement count, and one **Replace** that resets both.
  Moisturizer capacity is corrected to **125 ml** to match the real hardware.

## 📦 Cartridge-lot expiry management

- **Expiry alerts** with a configurable warning window (Settings → Preferences, default 30
  days): soon/expired **badges** across Inventory, a filter bar (All / Expiring / Expired / In
  use), and a **"Use next"** FEFO indicator pointing to the earliest-expiring lot per channel.
- A dismissible, snooze-able **Dashboard banner** (1 day / 1 week / 1 month) and an **Expiring
  & Expired Lots** section in the Inventory PDF.
- **Add Cartridge Lot** redesigned as a mobile-friendly modal with a **Box Expiry** camera/image
  scan that auto-extracts the date.

## 🛠️ Printer maintenance accuracy (eufyMake E1)

- Cleaning/moisturizing usage is modelled **per ink channel** across the 6 active channels, with
  White as a single slot (`W` XOR `FW`). New presets: **White Ink Flash Cleaning**, **White Line
  Swap (Hard ↔ Soft)**, and **Ink Injection (after Moisturizing)**.
- **Service Action Log retention** — configurable Archive/Delete windows with a daily purge, plus
  date/quick-range/search filtering and sorting.

## 🎨 Interface fixes

- **Toggle switches are clearly visible** in both light and dark mode.
- Robust Service Action Log rendering (payload sanitized server-side, so one bad legacy row can
  no longer hide the whole log), clearer help tooltips, and better button spacing.

---

## 📥 How you'll get it

- **Docker / self-hosted:** pull the new image and restart — migrations run automatically.
  ```bash
  docker compose -f docker-compose.public.yml pull app
  docker compose -f docker-compose.public.yml up -d
  ```
- **Windows (Microsoft Store):** updates automatically once the release rolls out to you.

## Windows SmartScreen (direct downloads)

The direct **.exe / .zip** downloads are **not code-signed**, so Windows SmartScreen may warn on
first run: click **More info → Run anyway**. The app is open source (GPL-3.0) — you can review or
rebuild it yourself. The signed **Microsoft Store** build is the recommended install.

---

_Full changelog: https://github.com/codebyit/inktracker/blob/main/CHANGELOG.md_
_Ported from internal `main` (v0.15.0 = commit `038c618`; v0.14.0 features from internal v0.13.0, commit `89b9a1f`)._
