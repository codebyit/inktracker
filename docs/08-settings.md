# 8. Settings

**Settings** is where you tell InkTracker about your shop. These values power every
cost and profit calculation, so it's worth setting them up carefully once.

---

## Machine
Enter your printer's **purchase price**, **lifespan**, and **annual hours**. InkTracker
spreads the cost across jobs so each project carries a fair share.

<p align="center"><img src="images/settings-machine.png" alt="Machine configuration" width="620"></p>

## Ink costs
Each ink color channel is a card where you set its **price per cartridge** and its
**ink density** (in g/ml). The price drives per-job ink cost; the density is used by the
weight-based remaining-ink estimate on the Service page (white and gloss inks are denser
than CMYK, so each channel has its own value). The card also shows the cost **per ml**.

<p align="center"><img src="images/settings-ink-costs.png" alt="Ink cost and density per channel" width="620"></p>

| Channel | Color |
|---|---|
| C | Cyan |
| M | Magenta |
| Y | Yellow |
| K | Black |
| W | White |
| GL | Gloss |
| FW | Flex White |

**Tip:** Leave density at **1.0** if you're unsure - that matches the old "1 ml = 1 g"
behavior. The **Cartridge Capacity** card on this page also lets you set the **empty
cartridge weight (tare)**, so the Service page's weight -> remaining-ink helper stays accurate.

## Labor & overhead
Set your **hourly labor rate** and an **overhead %** to cover rent, power, and other
running costs.

## Margins & currency
Choose your **currency** and the **margin thresholds** that decide the profit badges
(Strong / Target / Minimum / Loss).

## Auto-maintenance sync
Turn on a daily automatic maintenance log and pick the time - keeps ink levels accurate
without manual entry.

## Features
Optional features you can turn on or off. These settings apply to **both** the web app and
the Windows desktop app.

<p align="center"><img src="images/settings-features.png" alt="Features settings" width="700"></p>

- **Multiple craft modes** - lets a single project define several **craft faces** (for
  example, a 2-sided case with a different craft on each side) in the New Project wizard.
  It's **on by default**; existing single-craft projects are unaffected.

## Backup & restore (admin)
Download a **backup** of your data, or **restore** from one. Admins can also **reset**
the database.

<p align="center"><img src="images/settings-backup.png" alt="Backup and restore" width="700"></p>

**Note:** Reset and restore replace your data. Take a backup first.

**Tip:** Update prices whenever ink or material costs change - new projects use the
latest numbers automatically.

---

Next: **[Documentation Links ->](09-documentation-links.md)**
