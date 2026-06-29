import os
import logging
from pathlib import Path
from urllib.parse import urlsplit
from sqlalchemy.engine import URL
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

log = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent.parent / "inktracker.db"
_SQLITE_URL = f"sqlite:///{_DB_PATH}"


def _getenv(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


_strict_db_startup = _is_truthy(os.environ.get("STRICT_DATABASE_STARTUP"))


def _build_database_url_from_parts() -> str | None:
    db_user = _getenv("DB_USER")
    db_password = _getenv("DB_PASSWORD")
    db_host = _getenv("DB_HOST")
    db_port = _getenv("DB_PORT") or "5432"
    db_name = _getenv("DB_NAME")

    if not any((db_user, db_password, db_host, db_name, _getenv("DB_PORT"))):
        return None

    missing = [
        name
        for name, value in (("DB_USER", db_user), ("DB_HOST", db_host), ("DB_NAME", db_name))
        if not value
    ]
    if missing:
        raise RuntimeError(
            "PostgreSQL DB_* configuration is incomplete. Missing: "
            + ", ".join(missing)
        )

    return URL.create(
        drivername="postgresql+psycopg",
        username=db_user,
        password=db_password,
        host=db_host,
        port=int(db_port),
        database=db_name,
    ).render_as_string(hide_password=False)


_env_database_url = _getenv("DATABASE_URL")
_parts_database_url = _build_database_url_from_parts()
_raw_url = _env_database_url or _parts_database_url or _SQLITE_URL

if _strict_db_startup and not (_env_database_url or _parts_database_url):
    raise RuntimeError(
        "STRICT_DATABASE_STARTUP is enabled, but no PostgreSQL configuration was provided. "
        "Set DATABASE_URL or DB_USER/DB_PASSWORD/DB_HOST/DB_NAME."
    )

# SQLAlchemy 2.x requires postgresql+psycopg:// for psycopg3
if _raw_url.startswith("postgresql://") or _raw_url.startswith("postgres://"):
    _primary_url = _raw_url.replace("postgresql://", "postgresql+psycopg://", 1) \
                           .replace("postgres://", "postgresql+psycopg://", 1)
else:
    _primary_url = _raw_url

_is_postgres = not _primary_url.startswith("sqlite")


def _validate_postgres_url(raw_url: str) -> None:
    parsed = urlsplit(raw_url)
    if parsed.fragment:
        raise RuntimeError(
            "DATABASE_URL appears malformed: the URL contains a '#' fragment. "
            "If your PostgreSQL password contains reserved characters such as '#', '@', ':', '/', or '?', "
            "percent-encode them in the password portion of the URL. "
            "Example: replace '#' with '%23'."
        )


if _is_postgres:
    _validate_postgres_url(_raw_url)


def _make_engine(url: str):
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        # Avoid very long startup hangs when PostgreSQL host is unreachable.
        connect_args = {"connect_timeout": 3}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


# Attempt primary connection; fall back to SQLite if PostgreSQL is unreachable
DB_INFO: dict = {}

try:
    engine = _make_engine(_primary_url)
    with engine.connect() as _conn:
        _conn.execute(text("SELECT 1"))
    _type = "postgresql" if _is_postgres else "sqlite"
    DB_INFO = {
        "type": _type,
        "url_display": engine.url.render_as_string(hide_password=True),
        "fallback": False,
    }
    log.info("Database connected (%s): %s", _type, DB_INFO["url_display"])

except Exception as _err:
    if _is_postgres:
        if _strict_db_startup:
            raise RuntimeError(
                "STRICT_DATABASE_STARTUP is enabled and PostgreSQL is unreachable. "
                "Startup aborted to prevent SQLite fallback. "
                f"Original error: {_err}"
            ) from _err
        log.warning(
            "Primary PostgreSQL database unreachable (%s). Falling back to SQLite at %s.",
            _err, _DB_PATH,
        )
        engine = _make_engine(_SQLITE_URL)
        DB_INFO = {
            "type": "sqlite",
            "url_display": f"sqlite:///{_DB_PATH.name}",
            "fallback": True,
            "fallback_reason": str(_err),
        }
    else:
        raise RuntimeError(f"Cannot connect to SQLite database: {_err}") from _err

DATABASE_URL = str(engine.url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
