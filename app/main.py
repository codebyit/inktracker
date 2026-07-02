import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Ensure app logs are always visible in Docker regardless of alembic.ini root level.
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
    force=True,
)

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from .database import SessionLocal, DB_INFO
from .paths import STATIC_DIR, UPLOADS_DIR, VERSION_FILE, ensure_data_dirs
from . import crud
from .maintenance_scheduler import start_auto_maintenance_scheduler
from .routers import dashboard, projects, analytics, service, settings as settings_router, materials as materials_router, docs as docs_router, inventory as inventory_router, setup as setup_router
from .templates_config import templates

log = logging.getLogger(__name__)


# Content-Security-Policy: allow inline styles (Tailwind+Alpine emit inline
# style attributes) and inline scripts on templates that bootstrap Alpine
# state (e.g., x-data="..."). External scripts/styles are restricted to
# 'self'. Images allow data: URIs for inline icons/charts.
_CSP_POLICY = (
    "default-src 'self'; "
    "img-src 'self' data: blob:; "
    # Alpine's standard runtime evaluates directive expressions (x-data,
    # x-show, x-on) via Function/AsyncFunction, which requires 'unsafe-eval'.
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply baseline security headers to every response.

    Headers chosen to be safe defaults for a self-hosted FastAPI app served
    behind a reverse proxy. ``Strict-Transport-Security`` is only set when
    the upstream request is already HTTPS (so plain-HTTP LAN access is not
    broken).
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(self), microphone=(), geolocation=(), payment=()",
        )
        response.headers.setdefault("Content-Security-Policy", _CSP_POLICY)
        # Only advertise HSTS when the client already arrived over HTTPS to
        # avoid locking out plain-HTTP LAN deployments by accident.
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        if request.url.scheme == "https" or forwarded_proto == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


# Read version from environment or fallback to the bundled VERSION file.
APP_VERSION = os.environ.get("APP_VERSION")
if not APP_VERSION:
    if VERSION_FILE.exists():
        APP_VERSION = VERSION_FILE.read_text().strip()
    else:
        APP_VERSION = "unknown"

# Bundled (read-only) static assets vs. the writable uploads directory, which
# may live in a separate per-user data directory (see app.paths). Creating the
# writable data directories here is idempotent and safe for every deployment.
_STATIC_DIR = STATIC_DIR
ensure_data_dirs()

from .branding import APP_NAME, APP_OWNER, APP_TITLE

app = FastAPI(title=APP_NAME, description=f"UV Print Cost Tracker{f' — {APP_OWNER}' if APP_OWNER else ''}")

app.add_middleware(SecurityHeadersMiddleware)

# Serve writable user uploads from the data directory FIRST (the more specific
# prefix wins), then the bundled read-only static assets. This keeps stored
# photo_path values (/static/uploads/<file>) resolving even when uploads live
# outside the bundled static directory (e.g. a desktop per-user data folder).
app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# Serve PWA service worker and manifest from root for full-site scope.
# Service workers can only control URLs within their served path's scope.
@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(
        str(_STATIC_DIR / "sw.js"),
        media_type="application/javascript",
        headers={
            "Service-Worker-Allowed": "/",
            "Cache-Control": "no-cache",
        },
    )


@app.get("/manifest.json", include_in_schema=False)
def manifest() -> FileResponse:
    return FileResponse(
        str(_STATIC_DIR / "manifest.json"),
        media_type="application/manifest+json",
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(
        str(_STATIC_DIR / "icons" / "icon-192.png"),
        media_type="image/png",
    )


app.include_router(dashboard.router)
app.include_router(projects.router)
app.include_router(analytics.router)
app.include_router(service.router)
app.include_router(settings_router.router)
app.include_router(materials_router.router)
app.include_router(docs_router.router)
app.include_router(inventory_router.router)
app.include_router(setup_router.router)


@app.on_event("startup")
def startup() -> None:
    # Database migrations are handled by docker-entrypoint.sh before uvicorn starts.
    # For local SQLite dev, the migration_runner can be invoked directly if needed.
    log.info("Startup: seeding defaults and setting template globals")
    db = SessionLocal()
    try:
        crud.seed_defaults(db)
        templates.env.globals["currency"] = crud.get_currency(db)
        templates.env.globals["db_info"] = DB_INFO
        templates.env.globals["app_version"] = APP_VERSION
        # Cache-busting token for static assets. app.css is rebuilt on every
        # Docker build, so its mtime changes per deploy even when VERSION does
        # not (dev and prod share one version line). Appended as ?v= to asset
        # URLs so the reverse proxy, service worker, and browser fetch fresh
        # CSS after an update instead of serving a stale theme.
        try:
            _asset_version = str(int((_STATIC_DIR / "app.css").stat().st_mtime))
        except OSError:
            _asset_version = APP_VERSION
        templates.env.globals["asset_version"] = _asset_version
    except Exception:
        log.exception("FATAL: seed_defaults or template globals failed during startup")
        raise
    finally:
        db.close()

    start_auto_maintenance_scheduler()

    log.info("Startup complete")
