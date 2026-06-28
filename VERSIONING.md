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

## 5. Guards (enforced in CI by Version Guard)
- `VERSION` == `package.json.version` (always).
- On a `v*` tag: tag must equal `VERSION`, and a matching `CHANGELOG.md` entry must exist.

## Quick reference
```
npm run version:sync    # sync package.json from VERSION (after editing VERSION)
npm run version:check   # verify they match (CI guard)
```
