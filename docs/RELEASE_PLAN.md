# Release Plan & Process

This is the canonical checklist for shipping a public InkTracker release. It codifies the
order of operations so a release is repeatable and low-risk, and so the Microsoft Store
submission (which is slow and hard to reverse) only happens after staging validation.

> **Golden rules**
> - **Docker staging is the functional gate.** Nothing goes to the Store until it passes there.
> - **Submit MSIX to the Microsoft Store on Monday–Wednesday only.** Certification takes
>   24 h–3 days; a Thu/Fri submission risks certifying over a weekend (a prior submission was
>   not approved during a weekend).
> - **Port app code only.** The public fork is ahead on dependencies, Docker base image, CI,
>   and governance. See `../PUBLIC_FORK_DIVERGENCE.md` (internal) / preserve list below.
> - **Independent version sequence.** Public has its own `VERSION`; record the internal
>   baseline it derives from in the CHANGELOG footer.

---

## Release pipeline (in order)

```
freeze internal snapshot
  → cherry-pick app-layer changes into public (preserve deps/CI/governance)
  → bump public VERSION + CHANGELOG (Ported from internal vX.Y.Z (commit <sha>))
  → deploy public Docker image to STAGING
  → validate (functional + migration gate)  ← GATE 1
  → draft release notes (GitHub Release + docs Pages What's New; GA as a window)
  → [Mon–Wed] tag v* → build signed MSIX → submit to Store (gradual rollout < 100%)
  → MSIX smoke test (in parallel with cert)          ← GATE 2
  → cert passes + rollout ramps → GA: publish Release + flip What's New / Announcement
  → update Wiki + fresh screenshots (UI now frozen & shipped)
```

---

## Checklist

### 0. Pre-flight
- [ ] Internal `develop` == internal `main` at a known, tagged snapshot (record commit).
- [ ] Decide the public version bump (SemVer from Conventional Commits) and GA **window**.
- [ ] Confirm no open blocker in the public fork (CI green on `main`).

### 1. Port (private → public)
- [ ] Cherry-pick **app-layer** changes only (see the port manifest: `docs/PORT_MANIFEST_v0.14.0.md`).
- [ ] **Preserve** (do NOT overwrite): dependency pins, `python:3.14-slim`, CodeQL,
      dependabot, governance files, Tailwind v3. Adjust paths — public app is at repo root
      (no `inktrack/` prefix).
- [ ] Append new Alembic migrations onto the public head (public ends at `0018`; internal
      `0019–0023` append in order).
- [ ] Bump `VERSION` + `npm run version:sync`; update `CHANGELOG.md` with a
      `Ported from internal vX.Y.Z (commit <sha>)` footer.

### 2. GATE 1 — Docker staging validation
- [ ] Build + deploy the public Docker image to staging.
- [ ] **Migration gate:** `alembic upgrade head` succeeds on (a) a fresh DB and (b) a
      copy-of-prod-shaped DB. No manual SQL.
- [ ] Functional smoke: new features exercised end-to-end; existing flows unbroken.
- [ ] CI green on the public PR: lint/test, build, CodeQL, version guard, Bandit/pip-audit.

### 3. Release notes
- [ ] Draft the GitHub **Release** notes (authoritative, per-tag).
- [ ] Update the docs **What's New / Roadmap** page (features + GA **window**, not a hard date).
- [ ] (Optional) Prepare a **Discussions → Announcements** post for GA.

### 4. [Mon–Wed] Tag → MSIX → Store
- [ ] Tag `vX.Y.Z` on the public `main` (triggers build + signed MSIX + GitHub Release).
- [ ] Submit MSIX to Partner Center with **package rollout < 100%** (safety valve).
- [ ] Note: Docker image ≠ MSIX. Staging did not validate MSIX-specific behavior.

### 5. GATE 2 — MSIX smoke test (parallel with cert)
- [ ] Install from the `.msix`; app launches and closes cleanly (WebView2).
- [ ] **Store data redirect** exists:
      `%LOCALAPPDATA%\Packages\<PFN>\LocalCache\Local\InkTrack\` (db, uploads, docs_links.yaml).
- [ ] Update banner is **suppressed** on the packaged build (`running_as_msix()`).
- [ ] One real project created → cost/margin correct.

### 6. GA
- [ ] Partner Center status = **In the Store** and rollout ramped to 100%.
- [ ] Publish the GitHub Release; flip What's New / Announcement to "live."
- [ ] Close the release tracking issue.

### 7. Post-GA
- [ ] Update the **GitHub Wiki** (UI now frozen & shipped).
- [ ] Capture **fresh screenshots** (standard window size, seed data, light + dark).
- [ ] Sync any docs deltas back to the internal repo's tracking notes.

---

## Rollback story per surface

| Surface | Rollback |
|---|---|
| **Docker / self-hosted** | Redeploy the previous image tag. Migrations are additive & non-retroactive; forward-only. |
| **MSIX (Store)** | Cannot be trivially un-published → **staging + MSIX smoke test are the safety net.** Gradual rollout % limits blast radius; halt the rollout if issues surface. |
| **Store rollout** | Start < 100%, ramp after a soak period; roll back the rollout % or submit a fixed patch. |

---

## Where things get published

| Artifact | Home | Purpose |
|---|---|---|
| Per-tag release notes | **GitHub Releases** | Authoritative, version-anchored changelog + download assets. |
| "What's New / Roadmap" | **GitHub Pages** (from `docs/`) | Polished public feature page; features + GA window. |
| GA announcement + feedback | **GitHub Discussions → Announcements** | Community-facing, comments/reactions. |
| Deep docs + screenshots | **GitHub Wiki** | How-to, updated post-GA once UI is frozen. |

_A product marketing site (Vercel/Azure) is intentionally deferred until there is a clear
need — it adds a second surface to keep in sync._
