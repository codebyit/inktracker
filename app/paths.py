"""Centralized filesystem-path resolution for InkTrack.

This module is the single source of truth for two kinds of paths:

* **Writable data locations** — the SQLite database, user photo uploads and the
  editable documentation-links file. These honor the ``INKTRACK_DATA_DIR``
  environment variable so the app can store user data outside a read-only
  install directory (e.g. a packaged Windows desktop build writing to
  ``%LOCALAPPDATA%\\InkTrack``). When the variable is unset, the historical
  in-repo locations are used unchanged, so existing Docker/dev deployments
  behave exactly as before.

* **Bundled read-only resources** — static assets, Jinja templates, the
  ``VERSION`` file and the Alembic migration tree. These use
  :func:`resource_path`, which is aware of PyInstaller's ``sys._MEIPASS``
  extraction directory, so the same code works whether running from source or
  from a frozen executable.

Keeping this logic in one dependency-free module (it imports only the standard
library) avoids import cycles: ``app.database`` and ``app.templates_config``
depend on it, but it depends on nothing inside ``app``.
"""
from __future__ import annotations

import os
import sys
import shutil
from pathlib import Path

# app/paths.py -> app/ -> <repo root>
_APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = _APP_DIR.parent


def resource_path(*parts: str) -> Path:
    """Return an absolute path to a bundled, read-only resource.

    Under PyInstaller, data files are unpacked at runtime to a temporary
    directory exposed as ``sys._MEIPASS``. In normal (source) execution they
    live under the repository root.
    """
    base = Path(getattr(sys, "_MEIPASS", REPO_ROOT))
    return base.joinpath(*parts)


def _resolve_data_dir() -> Path:
    raw = os.environ.get("INKTRACK_DATA_DIR")
    if raw and raw.strip():
        return Path(raw.strip()).expanduser()
    return REPO_ROOT


DATA_DIR = _resolve_data_dir()
USING_CUSTOM_DATA_DIR = DATA_DIR.resolve() != REPO_ROOT.resolve()

# --- Writable locations ----------------------------------------------------
DB_PATH = DATA_DIR / "inktracker.db"

if USING_CUSTOM_DATA_DIR:
    # Clean, flat layout for a dedicated per-user data directory.
    UPLOADS_DIR = DATA_DIR / "uploads"
    DOCS_FILE = DATA_DIR / "docs_links.yaml"
else:
    # Preserve the exact historical in-repo paths for Docker/dev.
    UPLOADS_DIR = REPO_ROOT / "static" / "uploads"
    DOCS_FILE = _APP_DIR / "docs_links.yaml"

# Public URL prefix embedded in stored ``photo_path`` values. Kept stable so
# existing database rows (``/static/uploads/<file>``) keep resolving even though
# the files may now live outside the bundled static directory.
UPLOADS_URL_PREFIX = "/static/uploads"

# --- Bundled read-only resources -------------------------------------------
STATIC_DIR = resource_path("static")
TEMPLATES_DIR = resource_path("app", "templates")
VERSION_FILE = resource_path("VERSION")
ALEMBIC_DIR = resource_path("alembic")
ALEMBIC_INI = resource_path("alembic.ini")

# Bundled default documentation-links file, used to seed a fresh data dir.
_DEFAULT_DOCS_FILE = resource_path("app", "docs_links.yaml")


def ensure_data_dirs() -> None:
    """Create writable data directories and seed first-run defaults.

    Safe to call repeatedly. For a custom data directory, the editable
    ``docs_links.yaml`` is seeded from the bundled default on first run so the
    desktop experience matches the in-repo defaults.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    if USING_CUSTOM_DATA_DIR and not DOCS_FILE.exists():
        try:
            if _DEFAULT_DOCS_FILE.exists():
                shutil.copyfile(_DEFAULT_DOCS_FILE, DOCS_FILE)
        except OSError:
            # Non-fatal: the docs page simply starts empty if seeding fails.
            pass


# Create writable directories at import time. ``app.database`` opens the SQLite
# database at import (which can create the .db file but NOT its parent dir), so
# the data directory must exist before that import completes.
ensure_data_dirs()
