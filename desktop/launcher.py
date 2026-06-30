"""InkTrack desktop launcher.

Runs the existing FastAPI application — the very same ``app.main:app`` used by
the Docker image — inside a native window via pywebview. There is no fork of the
business logic, so the desktop build cannot drift from the server build.

Flow:

1. Resolve a writable per-user data directory and export it as
   ``INKTRACK_DATA_DIR`` *before* importing the app, so ``app.paths`` stores the
   SQLite database, uploads and ``docs_links.yaml`` there (outside the
   read-only install directory).
2. Enforce a single running instance (Windows named mutex).
3. Apply Alembic migrations against the SQLite database.
4. Start uvicorn on ``127.0.0.1`` on an automatically chosen free port, in a
   background thread.
5. Open a pywebview window pointing at the local server and block until the
   user closes it, then shut the server down cleanly.
6. In the background, check GitHub Releases and show an in-window banner if a
   newer version is available (manual update — link only, no auto-install).
"""
from __future__ import annotations

import os
import sys
import socket
import threading
import time
from pathlib import Path

APP_TITLE = "InkTrack"
_HOST = "127.0.0.1"

# Make ``import app`` work when running from source (python desktop/launcher.py).
# Harmless under PyInstaller, where the app package is already importable.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _default_data_dir() -> Path:
    """Per-user writable data directory.

    Windows: ``%LOCALAPPDATA%\\InkTrack``. Other OSes (dev convenience): an
    XDG-style ``~/.local/share/InkTrack``.
    """
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "InkTrack"
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".local" / "share")
    return base / "InkTrack"


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((_HOST, 0))
        return int(sock.getsockname()[1])


def _acquire_single_instance() -> bool:
    """Return True if this is the only instance, False if another is running.

    Uses a Windows named mutex; on other platforms always returns True. The
    mutex handle is intentionally kept for the process lifetime.
    """
    if os.name != "nt":
        return True
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    error_already_exists = 183
    handle = kernel32.CreateMutexW(None, wintypes.BOOL(True), "Global\\InkTrackDesktopSingleton")
    if not handle:
        return True  # fail open — better to launch than to wrongly block
    if kernel32.GetLastError() == error_already_exists:
        return False
    globals()["_singleton_handle"] = handle
    return True


def _wait_for_server(server, port: int, timeout: float = 30.0) -> bool:
    """Block until uvicorn reports started AND the port accepts connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if getattr(server, "should_exit", False):
            return False
        if getattr(server, "started", False):
            try:
                with socket.create_connection((_HOST, port), timeout=1):
                    return True
            except OSError:
                pass
        time.sleep(0.1)
    return False


def _show_update_banner_when_ready(window, current_version: str) -> None:
    """Background: if a newer release exists, inject a dismissible banner."""
    try:
        from desktop.update_check import check_for_update
    except ImportError:  # frozen build: module bundled at top level
        from update_check import check_for_update

    info = check_for_update(current_version)
    if not info:
        return
    # Build a small, self-contained banner and inject it via JS.
    url = info["url"].replace("'", "%27")
    latest = info["latest"]
    js = (
        "(function(){"
        "if(document.getElementById('it-update-banner'))return;"
        "var b=document.createElement('div');"
        "b.id='it-update-banner';"
        "b.style.cssText='position:fixed;left:0;right:0;bottom:0;z-index:9999;"
        "background:#0f172a;color:#fff;padding:10px 16px;font:14px system-ui,sans-serif;"
        "display:flex;gap:12px;align-items:center;justify-content:center';"
        "b.innerHTML='InkTrack " + latest + " is available. "
        "<a href=\\'" + url + "\\' target=\\'_blank\\' "
        "style=\\'color:#38bdf8;text-decoration:underline\\'>Download</a>';"
        "var x=document.createElement('button');"
        "x.textContent='Dismiss';"
        "x.style.cssText='margin-left:8px;background:#334155;color:#fff;border:0;"
        "border-radius:6px;padding:4px 10px;cursor:pointer';"
        "x.onclick=function(){b.remove();};"
        "b.appendChild(x);"
        "document.body.appendChild(b);"
        "})();"
    )
    try:
        window.evaluate_js(js)
    except Exception:  # window may have closed; ignore
        pass


def main() -> int:
    import multiprocessing
    multiprocessing.freeze_support()

    if not _acquire_single_instance():
        return 0  # another instance owns the singleton

    # Establish the writable data dir BEFORE importing the app so app.paths
    # picks it up. Respect an explicit override (e.g. for testing).
    if not os.environ.get("INKTRACK_DATA_DIR"):
        data_dir = _default_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        os.environ["INKTRACK_DATA_DIR"] = str(data_dir)

    # SQLite-only desktop build: never accidentally use a server DB/cache config.
    for var in ("DATABASE_URL", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME", "REDIS_URL"):
        os.environ.pop(var, None)

    # Apply migrations, then import the app (its startup event seeds defaults).
    from app.migration_runner import migrate_database
    migrate_database()

    from app.main import app, APP_VERSION

    import uvicorn
    port = _pick_free_port()
    config = uvicorn.Config(app, host=_HOST, port=port, log_level="warning")
    server = uvicorn.Server(config)
    # uvicorn installs signal handlers, which is only valid on the main thread.
    server.install_signal_handlers = lambda: None

    thread = threading.Thread(target=server.run, name="uvicorn", daemon=True)
    thread.start()

    if not _wait_for_server(server, port):
        server.should_exit = True
        print("InkTrack: local server failed to start.", file=sys.stderr)
        return 1

    url = f"http://{_HOST}:{port}/"

    # Headless self-test (used by CI to smoke-test the packaged binary): boot the
    # server, fetch the home page, report, and exit without opening a window.
    if os.environ.get("INKTRACK_SELFTEST") == "1":
        import urllib.request
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:  # nosec B310 - local loopback URL
                ok = resp.status == 200
                print(f"InkTrack self-test: GET / -> {resp.status}")
        except Exception as exc:
            print(f"InkTrack self-test failed: {exc}", file=sys.stderr)
            ok = False
        finally:
            server.should_exit = True
            thread.join(timeout=5)
        # Hard-exit so the process can never hang on a lingering daemon thread,
        # buffered output, or a frozen-runtime atexit handler on CI. We flush
        # explicitly because os._exit() skips normal interpreter shutdown.
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0 if ok else 1)

    import webview
    window = webview.create_window(
        APP_TITLE, url, width=1280, height=860, min_size=(960, 600),
    )

    def _on_loaded() -> None:
        threading.Thread(
            target=_show_update_banner_when_ready,
            args=(window, APP_VERSION),
            daemon=True,
        ).start()

    try:
        window.events.loaded += _on_loaded
    except Exception:
        pass

    try:
        webview.start()  # blocks until the window is closed
    finally:
        server.should_exit = True
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
