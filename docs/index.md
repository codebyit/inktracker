---
title: InkTrack — UV-print costing, inventory & profitability
description: Free, self-hosted cost and inventory tracker for UV printing. Know your true cost and profit per job, keep an eye on ink, and never get caught out by an expired cartridge.
---

**Free, self-hosted cost & inventory tracking for UV printing.** Know your true cost and
profit on every job, keep an eye on your ink and supplies, and get a heads-up before a
cartridge expires — all on your own computer, with no subscription and no account.

[![Get it on the Microsoft Store](https://img.shields.io/badge/Microsoft%20Store-Download-0067b8?logo=windows)](https://apps.microsoft.com/detail/9N913N963RB1)
&nbsp;
[![Source on GitHub](https://img.shields.io/badge/GitHub-Source-181717?logo=github)](https://github.com/codebyit/inktracker)

---

## Why InkTrack?

- 💶 **Real cost & profit per job.** Add ink, materials, machine time, and labour, and see a
  clear margin — colour-coded so a losing job is obvious at a glance.
- 🧪 **Ink & cartridge inventory.** Track levels and lots per channel, including White, Gloss,
  and the textured/Flex modes. Estimate remaining ink **by weight** with a kitchen scale.
- ⏰ **Expiry alerts.** Get warned before a cartridge dries out or goes out of date, with a
  "use this one next" hint so nothing is wasted. *(New in v0.14.0.)*
- 🔧 **Maintenance tracking.** Log cleaning, moisturizing, and cartridge swaps, and keep your
  ink levels honest over time.
- 🔒 **Private by design.** Everything stays on your machine. No subscription, no account,
  no cloud.

---

## Get started

**Windows** — install from the **[Microsoft Store](https://apps.microsoft.com/detail/9N913N963RB1)**; it updates automatically.

**Docker / self-hosted** — two files and one command:

```bash
curl -O https://raw.githubusercontent.com/codebyit/inktracker/main/docker-compose.public.yml
curl -o .env https://raw.githubusercontent.com/codebyit/inktracker/main/.env.example
docker compose -f docker-compose.public.yml up -d
```

Then open **http://localhost:8000**. Full steps in the [Installation guide](installation.md).

---

## Learn more

- 🚀 **[Getting Started](01-getting-started.md)** — set up in about 5 minutes
- 📖 **[User Manual](README.md)** — a guide for every part of the app
- ✨ **[What's New](whats-new.md)** — recent and upcoming releases
- 🛠️ **[Installation](installation.md)** · **[Configuration](configuration.md)** · **[Upgrading](upgrading.md)** · **[Troubleshooting](troubleshooting.md)**
- 🔐 **[Privacy](privacy.md)**

---

## Community

Questions, ideas, or want to help test? Join the conversation in
**[GitHub Discussions](https://github.com/codebyit/inktracker/discussions)**, or browse the
version-anchored notes and downloads on **[Releases](https://github.com/codebyit/inktracker/releases)**.

_InkTrack is open source (GPL-3.0)._
