# Versioning & Release Policy

InkTracker follows [Semantic Versioning](https://semver.org) — `MAJOR.MINOR.PATCH`.

This is the public fork's versioning policy. It is **ported from the internal source repo**
and adapted: the public repo keeps its **own independent version sequence** (it diverges on
dependencies, Python version, and governance files), but each release stays **traceable** to
the internal version/commit it derives from.

## 1. Single source of truth
- The **`VERSION` file** (repo root) is the single source of truth. The app reads it at runtime
  (`APP_VERSION` env overrides it, else the `VERSION` file — see `app/main.py`).
- `package.json` `version` is **derived from `VERSION`** via `npm run version:sync` and must
  match. CI fails otherwise (`npm run version:check`).
- A release **git tag** is `v<VERSION>` and must equal the `VERSION` file at that commit.
- **Invariant:** `VERSION` == `package.json.version` == release tag (without `v`).

## 2. When to bump (NOT every change)
- **Do not bump on every merged PR** (including Dependabot bumps). Merges are *unreleased*.
- The version changes only when **cutting a release**. Accumulate changes under
  `## [Unreleased]` in `CHANGELOG.md`; the release process renames it to the new version.
- Bump size follows SemVer from the Conventional Commit history:
  | Commits since last release | Bump |
  |---|---|
  | `feat!:` / `BREAKING CHANGE:` | **MAJOR** |
  | `feat:` (incl. notable security hardening) | **MINOR** |
  | `fix:` / `perf:` / dependency-security bumps | **PATCH** |
  | `chore:` / `docs:` / `ci:` only | no release on their own |

## 3. Independent sequence + traceability to internal
- The public `VERSION` is **independent** — do not copy the internal repo's `VERSION` verbatim.
- Each public release records the internal version + commit it was ported from. The
  `CHANGELOG.md` entry carries a footer:
  `Ported from internal vX.Y.Z (commit <sha>)`.
- Public-originated releases (e.g. security hardening that has no internal counterpart) note
  that explicitly instead.

## 4. Release process (hybrid: CI suggests, human approves)
1. The **Suggest Next Version** workflow inspects Conventional Commits since the last `v*` tag
   and suggests the next SemVer (job summary). It does not auto-tag.
2. A maintainer runs the **Release** workflow (`workflow_dispatch`) with the confirmed version.
   It updates `VERSION` (+ `npm run version:sync`), updates `CHANGELOG.md`, commits, and tags
   `vX.Y.Z`.

## 4a. Hotfix / patch fast-track
`main` is always releasable, so an urgent fix ships on its own **without waiting for or
dragging in unrelated in-flight work**. Use this when a released version has a bug that
shouldn't wait for the next `feat` release.

1. Branch off the current `main`: `fix/<short-name>`.
2. Make the **smallest** change that fixes it; commit as `fix(scope): …` (a `fix:` maps to a
   **PATCH** bump — see §2). Keep unrelated changes out of the branch.
3. Open a PR; let required checks pass (`lint-test`, CodeQL, plus the desktop `build` when
   `desktop/**`/`app/**`/`packaging/**` are touched); merge to `main`.
4. Cut the patch: bump to the next PATCH (`X.Y.(Z+1)`) via the Release process (§4) — or, for a
   one-off, `node scripts/prepare-release.mjs X.Y.Z` on a release branch, PR, merge, then tag.
5. Push the `vX.Y.(Z+1)` tag → `desktop-windows.yml` builds the release (installer/portable, and
   MSIX on tag). Submit the new MSIX to the Store as the next update.

Notes:
- **Don't batch** an urgent fix with features — that's the whole point of the fast-track.
- If a fix must land while a larger release is mid-certification, ship it as the **next PATCH
   after** that release publishes (avoids re-tagging an in-flight submission). Example: 0.13.1
   was cut this way while 0.13.0 was still certifying.
- The Store's own gradual rollout + rollback covers "safe rollout" — no extra tooling needed.

## 5. Guards (enforced in CI by Version Guard)
- `VERSION` == `package.json.version` (always).
- On a `v*` tag: tag must equal `VERSION`, and a matching `CHANGELOG.md` entry must exist.

## Quick reference
```
npm run version:sync    # sync package.json from VERSION (after editing VERSION)
npm run version:check   # verify they match (CI guard)
```
