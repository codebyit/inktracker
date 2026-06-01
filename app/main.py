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
from . import crud
from .maintenance_scheduler import start_auto_maintenance_scheduler
from .routers import dashboard, projects, analytics, service, settings as settings_router, materials as materials_router, docs as docs_router, inventory as inventory_router
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


# Read version from environment or fallback to VERSION file
APP_VERSION = os.environ.get("APP_VERSION")
if not APP_VERSION:
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        APP_VERSION = version_file.read_text().strip()
    else:
        APP_VERSION = "unknown"

_STATIC_DIR = Path(__file__).parent.parent / "static"
_STATIC_DIR.mkdir(exist_ok=True)
(_STATIC_DIR / "uploads").mkdir(exist_ok=True)

app = FastAPI(title="InkTracker", description="UV Print Cost Tracker — LT Atelier")

app.add_middleware(SecurityHeadersMiddleware)

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
    except Exception:
        log.exception("FATAL: seed_defaults or template globals failed during startup")
        raise
    finally:
        db.close()

    start_auto_maintenance_scheduler()

    log.info("Startup complete")
