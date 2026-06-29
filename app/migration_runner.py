from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def _alembic_config() -> Config:
    project_root = Path(__file__).parent.parent
    cfg = Config(str(project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(project_root / "alembic"))
    return cfg


def migrate_database() -> None:
    """Apply Alembic migrations.

    The migration scripts are written to be fully idempotent (CREATE TABLE IF
    NOT EXISTS, column-existence checks before ADD COLUMN) so running
    ``upgrade head`` is safe against both fresh and existing databases.
    """
    cfg = _alembic_config()
    command.upgrade(cfg, "head")
