# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the InkTrack Windows desktop app.

Bundles the existing FastAPI app plus the pywebview launcher into a single
windowed executable. Data files are placed so that ``app.paths.resource_path``
(which reads from ``sys._MEIPASS`` when frozen) finds them at the same relative
locations used from source:

    _MEIPASS/static/...            (built CSS/JS/icons/sw.js/manifest.json)
    _MEIPASS/app/templates/...     (Jinja2 templates)
    _MEIPASS/app/docs_links.yaml   (default docs seed)
    _MEIPASS/alembic/...           (env.py, script.py.mako, versions/*.py)
    _MEIPASS/alembic.ini
    _MEIPASS/VERSION

Build (from the repo root, with the venv active)::

    pyinstaller desktop/inktrack.spec --noconfirm \
        --distpath ../inktrack-windows/dist --workpath ../inktrack-windows/build

By default this is a ONEDIR build (a folder under dist/InkTrack/ with
InkTrack.exe plus an _internal/ payload). Onedir is preferred for the installed
app because it ships via an Inno Setup installer that lays down the whole folder:
startup is fast (no per-launch self-extraction or antivirus re-scan).

A single-file (onefile) build was intentionally NOT used: PyInstaller onefile
extracts an unsigned ``pythonXY.dll`` to a temp folder at launch, which Windows
Application Control / Smart App Control blocks ("LoadLibrary: An Application
Control policy has blocked this file"). The onedir layout loads its DLLs from
beside the signed exe, so it is not affected. The portable download is therefore
a ZIP of this onedir folder, not a onefile exe.

Set ``INKTRACK_DEBUG_CONSOLE=1`` to build a console variant whose startup errors
are visible on stderr (diagnostics only; the shipped build is windowed).
"""
import os

from PyInstaller.utils.hooks import collect_submodules, collect_all

repo = os.path.abspath(os.path.join(SPECPATH, ".."))
# Diagnostic only: build a console app so startup errors are visible on stderr.
CONSOLE = os.environ.get("INKTRACK_DEBUG_CONSOLE") == "1"


def _p(*parts):
    return os.path.join(repo, *parts)


# --- Bundled data (read-only resources) ------------------------------------
datas = [
    (_p("static"), "static"),
    (_p("app", "templates"), "app/templates"),
    (_p("app", "docs_links.yaml"), "app"),
    (_p("alembic"), "alembic"),
    (_p("alembic.ini"), "."),
    (_p("VERSION"), "."),
]

# reportlab ships font metrics / data files needed for PDF export.
_rl_datas, _rl_binaries, _rl_hidden = collect_all("reportlab")
datas += _rl_datas

# --- Hidden imports ---------------------------------------------------------
hiddenimports = []
hiddenimports += collect_submodules("app")        # routers, crud, cogs, etc.
hiddenimports += collect_submodules("uvicorn")    # loops/protocols/lifespan
hiddenimports += collect_submodules("alembic")
hiddenimports += _rl_hidden
hiddenimports += ["desktop.update_check"]

# --- Excludes (SQLite-only desktop build) ----------------------------------
excludes = ["psycopg", "psycopg_binary", "psycopg2"]


a = Analysis(
    [_p("desktop", "launcher.py")],
    pathex=[repo],
    binaries=_rl_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

# Onedir: a slim launcher EXE plus an _internal/ payload, assembled by COLLECT.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,               # onedir: binaries/datas go in COLLECT
    name="InkTrack",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=CONSOLE,                      # windowed app, no console (unless debugging)
    disable_windowed_traceback=False,
    icon=_p("desktop", "inktrack.ico"),
    version=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="InkTrack",
)
