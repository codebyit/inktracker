from __future__ import annotations

from alembic import command
from alembic.config import Config

from .paths import ALEMBIC_INI, ALEMBIC_DIR


def _alembic_config() -> Config:
    # Resolve alembic.ini and the migration tree via app.paths so this works
    # both from source and from a frozen PyInstaller bundle (sys._MEIPASS).
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    return cfg


def migrate_database() -> None:
    """Apply Alembic migrations.

    The migration scripts are written to be fully idempotent (CREATE TABLE IF
    NOT EXISTS, column-existence checks before ADD COLUMN) so running
    ``upgrade head`` is safe against both fresh and existing databases.
    """
    cfg = _alembic_config()
    command.upgrade(cfg, "head")
