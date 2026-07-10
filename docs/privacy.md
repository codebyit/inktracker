---
title: Privacy Policy
layout: default
permalink: /privacy/
---

# InkTracker Privacy Policy

**Last updated:** 1 July 2026

InkTracker ("the App") is a free, open-source (GPL-3.0) desktop and self-hosted
application for tracking UV-print production costs, ink and cartridge inventory,
and profitability. This policy explains how the App handles your information.

## Summary

**InkTracker does not collect, transmit, sell, or share any personal data.**
Everything you enter stays on your own device or your own server. There is no
account, no sign-up, no telemetry, no analytics, and no advertising.

## What data the App stores

All data you create — projects, cost entries, ink/cartridge inventory, machine
and material settings, and any photos you attach — is stored **locally**:

- **Microsoft Store / Windows desktop app:** in a local SQLite database and an
  uploads folder under your own user profile
  (`%LOCALAPPDATA%\InkTrack`).
- **Self-hosted (Docker) deployments:** in the database and volumes you
  configure on your own infrastructure.

This data never leaves your device or server unless *you* choose to move it (for
example, by copying the database file or exporting a backup).

## What the App does NOT do

- No personal information is collected or required.
- No usage analytics, telemetry, crash reporting, or tracking.
- No advertising or third-party marketing.
- No data is sold or shared with anyone.
- No background network calls to the developer.

## Network access

The desktop app runs a small web server on your own machine (`localhost`) and
renders its interface using the Microsoft Edge **WebView2** runtime already
present on Windows. It does not send your data over the internet. Any network
activity is limited to actions you explicitly initiate — for example downloading
the App or a software update from GitHub or the Microsoft Store, or, in
self-hosted mode, connecting to a database you configured.

## Photos and attachments

If you attach photos to a project, they are saved locally alongside your
database. They are **not** uploaded anywhere.

## Children's privacy

The App is a business/productivity tool and is not directed at children. Because
it collects no personal data, it does not knowingly collect information from
anyone, including children under 13.

## Data retention and deletion

You are in full control of your data. To delete it, remove the local database and
uploads folder (desktop: `%LOCALAPPDATA%\InkTrack`), or uninstall the App.
Uninstalling through Windows removes the application; your data folder can be
deleted manually if you also want to remove saved projects.

## Open source

InkTracker is open source under the **GNU General Public License v3.0**. You can
review exactly how it handles data in the source code:
<https://github.com/codebyit/inktracker>

## Changes to this policy

If this policy changes, the updated version will be published at this URL with a
new "Last updated" date.

## Contact

Questions or concerns? Please open an issue at
<https://github.com/codebyit/inktracker/issues>.
