from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database import Base, DATABASE_URL
from app import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    return raw_url


def _escape_for_alembic_config(url: str) -> str:
    # Alembic stores this value via ConfigParser, where '%' is interpolation syntax.
    # URL-encoded credentials (e.g. '%23') must be escaped to '%%23' here.
    return url.replace("%", "%%")


database_url = os.environ.get("DATABASE_URL") or DATABASE_URL
config.set_main_option("sqlalchemy.url", _escape_for_alembic_config(_normalize_database_url(database_url)))


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    sqlalchemy_url = config.get_main_option("sqlalchemy.url")
    # SQLite does not accept PostgreSQL-specific connection arguments.
    # Apply the timeout/keepalive settings only when running against PostgreSQL.
    _connect_args = {}
    if sqlalchemy_url.startswith("postgresql+"):
        # lock_timeout=3s: fail fast with a real error instead of hanging.
        # TCP keepalives (idle=5s, interval=2s, count=2): forces PostgreSQL to detect
        # and release dead connections in ~9s, breaking the restart death-spiral where
        # each crashed run leaves a stale lock that blocks the next run indefinitely.
        _connect_args = {
            "options": "-c lock_timeout=3000",
            "keepalives": 1,
            "keepalives_idle": 5,
            "keepalives_interval": 2,
            "keepalives_count": 2,
        }
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
