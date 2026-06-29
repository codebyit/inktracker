# 8. Settings

**Settings** is where you tell InkTrack about your shop. These values power every
cost and profit calculation, so it's worth setting them up carefully once.

---

## Machine
Enter your printer's **purchase price**, **lifespan**, and **annual hours**. InkTrack
spreads the cost across jobs so each project carries a fair share.

![Machine configuration](images/settings-machine.png)

## Ink costs
Each ink color channel is a card where you set its **price per cartridge** and its
**ink density** (in g/ml). The price drives per-job ink cost; the density is used by the
weight-based remaining-ink estimate on the Service page (white and gloss inks are denser
than CMYK, so each channel has its own value). The card also shows the cost **per ml**.

![Ink cost and density per channel](images/settings-ink-costs.png)

| Channel | Color |
|---|---|
| C | Cyan |
| M | Magenta |
| Y | Yellow |
| K | Black |
| W | White |
| GL | Gloss |
| FW | Flex White |

💡 **Tip:** Leave density at **1.0** if you're unsure — that matches the old "1 ml = 1 g"
behavior. The **Cartridge Capacity** card on this page also lets you set the **empty
cartridge weight (tare)**, so the Service page's weight → remaining-ink helper stays accurate.

## Labor & overhead
Set your **hourly labor rate** and an **overhead %** to cover rent, power, and other
running costs.

## Margins & currency
Choose your **currency** and the **margin thresholds** that decide the profit badges
(Strong / Target / Minimum / Loss).

## Auto-maintenance sync
Turn on a daily automatic maintenance log and pick the time — keeps ink levels accurate
without manual entry.

## Backup & restore (admin)
Download a **backup** of your data, or **restore** from one. Admins can also **reset**
the database.

![Backup and restore](images/settings-backup.png)

⚠️ **Note:** Reset and restore replace your data. Take a backup first.

💡 **Tip:** Update prices whenever ink or material costs change — new projects use the
latest numbers automatically.

---

Next: **[Documentation Links →](09-documentation-links.md)**
