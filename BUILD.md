# Building the InkTrack Windows desktop app

InkTrack ships as a standalone Windows desktop app: the **same** FastAPI
application (`app.main:app`) run inside a native [pywebview](https://pywebview.flowrl.com/)
window by [`desktop/launcher.py`](desktop/launcher.py). It is SQLite-only and
stores user data under `%LOCALAPPDATA%\InkTrack` — there is no server, no Docker,
and no fork of the business logic.

This document covers local builds, the CI pipeline, code signing via the
**SignPath Foundation**, and **Microsoft Store MSIX** packaging.

---

## 1. Prerequisites

| Tool | Why | Notes |
|---|---|---|
| **Python 3.12+** | Runs the app and PyInstaller | CI uses **3.14** (matches the server image). |
| **Node 20** | Compiles Tailwind CSS | **Build-time only** — Node is *not* a runtime dependency. |
| **Inno Setup 6** | Builds the installer `.exe` | `choco install innosetup` or <https://jrsoftware.org/isdl.php>. |
| **Windows 10/11 SDK** | `makeappx.exe` / `signtool.exe` for MSIX | Only needed for the Store package. |
| **Edge WebView2 Runtime** | Renders the window | Preinstalled on Win11; the installer bootstraps it on Win10. |

One-time setup (from the repo root):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r desktop/requirements-desktop.txt -r desktop/requirements-build.txt

# Frontend assets (must run before PyInstaller so the built CSS is bundled)
npm ci            # or: npm install
npm run build:css
npm run vendor:jsqr
```

> `requirements-desktop.txt` mirrors `requirements.txt` **minus** the PostgreSQL
> driver (the desktop build is SQLite-only) **plus** `pywebview`.
> `requirements-build.txt` adds PyInstaller.

---

## 2. Local builds

### 2a. Onedir (installed app)

The default build is a **onedir** bundle (`dist/InkTrack/InkTrack.exe` + an
`_internal\` payload). It starts fast and is what the installer ships.

```powershell
pyinstaller desktop/inktrack.spec --noconfirm
# -> dist\InkTrack\InkTrack.exe
```

Smoke-test the packaged binary headlessly (boots the server, fetches `/`, exits):

```powershell
$env:INKTRACK_SELFTEST = "1"
$env:INKTRACK_DATA_DIR = "$env:TEMP\inktrack_test"
.\dist\InkTrack\InkTrack.exe      # prints "InkTrack self-test: GET / -> 200", exit 0
Remove-Item Env:INKTRACK_SELFTEST
```

### 2b. Portable ZIP (no install)

The portable download is a **ZIP containing a top-level `InkTrack\` folder** (plus
a short `READ ME FIRST.txt`). The user **extracts** it, then runs
`InkTrack\InkTrack.exe` — no installer, no admin.

```powershell
# Build the onedir first (2a), then stage a top-level InkTrack\ folder and zip it:
$stage = "portable_stage"
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item dist\InkTrack "$stage\InkTrack" -Recurse
Compress-Archive -Path "$stage\*" -DestinationPath InkTrack-portable.zip -Force
```

> **Extract before running.** The zip is packaged with a containing `InkTrack\`
> folder specifically so it is **not** run from inside Explorer's zip viewer.
> Double-clicking `InkTrack.exe` from inside the zip makes Windows extract just
> the exe to `%TEMP%` without its `InkTrack\_internal\` DLLs, causing
> `Failed to load Python DLL ... LoadLibrary: The specified module could not be
> found`. Extracting the whole folder first avoids this.

> **Why not a single-file (onefile) exe?** PyInstaller onefile extracts an
> unsigned `python3xx.dll` to a temp folder at launch, which Windows
> **Application Control / Smart App Control** blocks
> (`LoadLibrary: An Application Control policy has blocked this file`) — even
> when the outer exe is signed. The onedir loads its DLLs from beside the signed
> exe, so the ZIP-of-onedir portable works on locked-down machines.

### 2c. Installer (Inno Setup)

The installer is per-user (no admin), installs to `%LOCALAPPDATA%\Programs\InkTrack`,
adds Start-menu/uninstall entries, bootstraps WebView2 when missing, and
**preserves** `%LOCALAPPDATA%\InkTrack` user data on uninstall.

```powershell
# Optional: bundle the WebView2 bootstrapper (else it is fetched at install time)
Invoke-WebRequest "https://go.microsoft.com/fwlink/p/?LinkId=2124703" `
  -OutFile desktop\MicrosoftEdgeWebview2Setup.exe

# DistDir must be ABSOLUTE (Inno resolves relative [Files] paths against the .iss dir)
$dist = Join-Path $PWD "dist"
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "/DDistDir=$dist" desktop\installer.iss
# -> dist\InkTrack-Setup-<version>.exe
```

### 2d. MSIX (Microsoft Store / sideload)

`packaging/make-msix.ps1` lays out a package root (the token-filled
[`AppxManifest.xml`](packaging/AppxManifest.xml) + `Assets\` + the onedir
`InkTrack\` folder) and runs `makeappx pack`. The Store **re-signs** the package
on submission, so the CI/Store package is intentionally unsigned.

Build a **self-signed** package for local sideload testing:

```powershell
# Build the onedir first (2a), then:
./packaging/make-msix.ps1 -SelfSign `
  -IdentityName "InkTrack.Dev" `
  -Publisher "CN=Your Name" `
  -PublisherDisplayName "Your Name"
# -> InkTrack-<version>.msix  (self-signed)
```

To install the self-signed package, trust its certificate first (import it into
**Local Machine → Trusted People**), then:

```powershell
Add-AppxPackage .\InkTrack-0.10.0.msix
```

Fast inner-loop alternative (no packaging — register the staged folder in dev
mode). After `make-msix.ps1` stages a layout, or by hand, you can run:

```powershell
Add-AppxPackage -Register .\AppxManifest.xml   # from a folder that has Assets\ + InkTrack\
```

---

## 3. CI pipeline

[`.github/workflows/desktop-windows.yml`](.github/workflows/desktop-windows.yml)
runs on `windows-latest` for PRs touching the desktop/app/packaging paths, on
`workflow_dispatch`, and on `v*` tags.

```
build (always)
  Tailwind → install deps → parity check (import app.main) →
  PyInstaller onedir → smoke-test the packaged exe →
  ZIP the onedir (portable) → Inno installer →
  upload artifacts; on a tag, stage signable files + (if unsigned) attach to Release
sign (tag + SignPath configured)   → SignPath signs the installer + the exe inside the portable ZIP → attach SIGNED to Release
msix (tag + MSIX identity set)     → makeappx pack the onedir → upload .msix artifact
```

The `build` job is **fail-fast and observable**: every heavy step has a
`timeout-minutes`, the packaged smoke-test captures the app's stdout/stderr and
kills+reports on a 120 s timeout, and a Defender exclusion avoids first-launch
scan stalls on the unsigned binary.

`sign` and `msix` are **gated on repository config** (below), so the core build
stays green before signing/Store are set up. Because code signing is not currently
configured, a tagged release gets the **unsigned** installer + portable.

---

## 4. Code signing (not currently active)

> **Status:** The InkTrack SignPath Foundation OSS application was **declined**
> (the project does not yet meet their public-reputation bar), so direct downloads
> are currently **unsigned**. Users may see a Windows SmartScreen "unknown
> publisher" prompt (**More info → Run anyway**). The Microsoft Store build is
> signed by the Store on ingestion, so the Store version is trusted.
>
> The `sign` job scaffolding below is **retained and gated** — it stays dormant
> until the signing variables are set, so it can be re-enabled later with SignPath
> (on reapplication) or another provider without a workflow change.
>
> **Publicly-trusted signing is not currently viable for this publisher.**
> Azure Trusted Signing (now **Azure Artifact Signing**) issues **Public Trust**
> certificates to organizations in the US/CA/EU/UK, but to **individual developers
> only in the US and Canada** — an **EU-based individual does not qualify**. The
> EU-individual alternative, a **Private Trust** certificate, chains to a
> self-distributed root that each recipient's machine must already trust (via
> GPO/Intune), so it does **nothing** for public GitHub downloads (no better than
> self-signed). Publicly signing direct downloads would therefore require either
> registering an EU **business entity** (to obtain an org Public Trust cert) or a
> traditional commercial **OV code-signing** cert (paid, hardware-token bound).
> Until then, the Microsoft Store — which signs the package on ingestion — remains
> the only trusted distribution channel, and direct downloads stay unsigned.

[SignPath Foundation](https://signpath.org/) provides **free** code signing for
open-source projects. Signed builds are trusted by Windows and avoid the
SmartScreen "unknown publisher" prompt.

### 4.1 One-time setup (external — you do this once)

1. **Apply** for the SignPath Foundation OSS program with this repo:
   <https://signpath.org/apply>.
2. Once approved, in the SignPath web app:
   - note your **Organization ID**;
   - create/confirm a **Project** for `inktracker` (note its **slug**);
   - install the **GitHub Actions** trusted build system / connector and point it
     at `codebyit/inktracker`;
   - create an **Artifact Configuration** that signs the contents of the uploaded
     zip. It must sign the installer PE (`InkTrack-Setup-*.exe`) directly **and**
     sign the `InkTrack\InkTrack.exe` *inside* the portable zip
     (`InkTrack-*-portable.zip`), re-zipping it. Note its **slug**;
   - create/confirm a **Signing Policy** named `release-signing` (note its **slug**);
   - create a **CI user** + **API token**.

### 4.2 GitHub repository configuration

Create these in **Settings → Secrets and variables → Actions**:

| Kind | Name | Value |
|---|---|---|
| **Secret** | `SIGNPATH_API_TOKEN` | SignPath CI user API token |
| Variable | `SIGNPATH_ORGANIZATION_ID` | Your SignPath organization GUID |
| Variable | `SIGNPATH_PROJECT_SLUG` | e.g. `inktracker` |
| Variable | `SIGNPATH_SIGNING_POLICY_SLUG` | `release-signing` |
| Variable | `SIGNPATH_ARTIFACT_CONFIG_SLUG` | Your artifact-configuration slug |

> The `sign` job only runs when `SIGNPATH_PROJECT_SLUG` is set. Setting the
> variables above "turns on" signing for the next tagged release — no workflow
> change needed.

### 4.3 Release flow

1. Cut a release (bump `VERSION`, tag `vX.Y.Z`) — see [`VERSIONING.md`](inktrack/VERSIONING.md)
   conventions; the `Release` workflow creates the tag.
2. The `v*` tag triggers `desktop-windows.yml`:
   - `build` produces the installer + portable and uploads them as the
     `inktrack-signable` artifact;
   - `sign` submits that artifact to SignPath, waits for completion, downloads the
     signed binaries, and attaches them to the GitHub Release.
3. The release now carries **signed** `InkTrack-Setup-<ver>.exe` and
   `InkTrack-<ver>-portable.zip` (with a signed `InkTrack.exe` inside).

---

## 5. Microsoft Store (MSIX)

A one-time **$19** individual registration at
[Partner Center](https://partner.microsoft.com/dashboard) gives you a publisher
identity. Store-distributed apps are trusted (no SmartScreen), and the Store
signs the package for you.

### 5.1 Reserve identity & configure CI

1. In Partner Center, **reserve the app name** (e.g. `InkTrack`) and open
   **Product management → Product identity**. Copy:
   - **Package/Identity/Name** → `MSIX_IDENTITY_NAME`
   - **Package/Identity/Publisher** (the `CN=…` string) → `MSIX_PUBLISHER`
   - **Publisher display name** → `MSIX_PUBLISHER_DISPLAY_NAME`
2. Add those three as **Actions variables**. The `msix` CI job runs on the next
   tag once `MSIX_IDENTITY_NAME` is set and uploads an `InkTrack-<ver>-msix`
   artifact (unsigned — the Store signs on submission).

### 5.2 Submit

1. Create a new submission in Partner Center.
2. Upload the `.msix` from the `msix` job artifact (or built locally — unsigned
   is correct for Store upload; do **not** self-sign for submission).
3. Fill listing details, age rating, and screenshots; submit for certification.

> **Local validation before submitting:** build a self-signed package (2d),
> sideload it, and confirm the app launches and serves the UI. Then build the
> unsigned package for the actual upload.

---

## 6. Where data lives

The packaged app never writes inside its install directory. All user data goes to
a per-user folder (overridable via `INKTRACK_DATA_DIR`):

```
%LOCALAPPDATA%\InkTrack\
  inktracker.db        SQLite database
  uploads\             project photos
  docs_links.yaml      editable documentation links
```

This is created on first run and preserved across upgrades and uninstalls.
