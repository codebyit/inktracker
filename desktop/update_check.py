"""Lightweight 'is there a newer release?' check for the desktop app.

Compares the running version with the latest published GitHub release of the
public repository. This is a *manual* update mechanism: it never downloads or
installs anything; the launcher simply surfaces a banner with a link so the
user can grab the new installer themselves. Any failure (offline, rate limited,
parse error) is swallowed and reported as "no update" so the app never breaks
because of a failed check.

Microsoft Store installs are excluded: those builds update through the Store
itself, so surfacing a GitHub "download" banner would both bypass the Store and
point users at a release the Store may not have published yet.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import urllib.request
from typing import Optional

log = logging.getLogger(__name__)

GITHUB_REPO = "codebyit/inktracker"
_LATEST_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"

# GetCurrentPackageFullName returns this when the process has no package
# identity (i.e. it is NOT an MSIX/Store install).
_APPMODEL_ERROR_NO_PACKAGE = 15700


def running_as_msix() -> bool:
    """True when the process runs with MSIX package identity (Store/sideload).

    Store-installed builds are updated by the Microsoft Store, so the in-app
    GitHub update banner must be suppressed for them. Detection uses the
    Win32 ``GetCurrentPackageFullName`` API, which returns
    ``APPMODEL_ERROR_NO_PACKAGE`` only when the caller has no package identity.
    Any failure (non-Windows, older OS, unexpected error) is treated as
    "not packaged" so the normal update check still runs.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        length = wintypes.UINT(0)
        # Query the required buffer length with a NULL buffer. When the process
        # has package identity this returns ERROR_INSUFFICIENT_BUFFER (122);
        # otherwise it returns APPMODEL_ERROR_NO_PACKAGE (15700).
        rc = kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
        return rc != _APPMODEL_ERROR_NO_PACKAGE
    except Exception as exc:  # pragma: no cover - platform/edge cases
        log.info("MSIX package-identity check failed (assuming not packaged): %s", exc)
        return False



def _parse_version(value: str) -> Optional[tuple[int, ...]]:
    """Parse a semver-ish string (optionally prefixed with 'v') into a tuple.

    Returns None when no numeric version can be extracted.
    """
    if not value:
        return None
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        return None
    return tuple(int(p) for p in match.groups())


def check_for_update(current_version: str, timeout: float = 4.0) -> Optional[dict]:
    """Return update info when a newer release exists, else None.

    On success with a newer release, returns::

        {"current": "0.10.0", "latest": "0.11.0", "url": "https://..."}
    """
    # Store installs are updated by the Microsoft Store; never surface the
    # GitHub download banner for them.
    if running_as_msix():
        return None

    current = _parse_version(current_version)
    if current is None:
        return None

    try:
        req = urllib.request.Request(
            _LATEST_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "InkTrack-Desktop",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 - fixed HTTPS GitHub API URL
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # network/parse errors are non-fatal
        log.info("Update check skipped: %s", exc)
        return None

    tag = data.get("tag_name") or data.get("name") or ""
    latest = _parse_version(tag)
    if latest is None or latest <= current:
        return None

    return {
        "current": ".".join(map(str, current)),
        "latest": ".".join(map(str, latest)),
        "url": data.get("html_url") or RELEASES_PAGE,
    }
