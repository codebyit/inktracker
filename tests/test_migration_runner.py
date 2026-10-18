"""Run the real startup migration command on disposable SQLite databases."""
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]


def _migrate(path):
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{path}", "REDIS_URL": ""}
    return subprocess.run(
        [sys.executable, "-m", "app.migration_runner"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )


def test_startup_migrates_fresh_db_and_preserves_current_revision_and_custom_presets(tmp_path):
    path = tmp_path / "startup.db"
    result = _migrate(path)
    assert result.returncode == 0, result.stdout + result.stderr
    engine = create_engine(f"sqlite:///{path}")
    try:
        with engine.begin() as conn:
            head = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            conn.execute(text(
                "UPDATE maintenance_presets SET volumes_json=:vols WHERE name='White Ink Flash Cleaning'"
            ), {"vols": '{"W":123}'})
        result = _migrate(path)
        assert result.returncode == 0, result.stdout + result.stderr
        with engine.connect() as conn:
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == head
            assert conn.execute(text(
                "SELECT volumes_json FROM maintenance_presets WHERE name='White Ink Flash Cleaning'"
            )).scalar_one() == '{"W":123}'
    finally:
        engine.dispose()


def test_unknown_migration_revision_aborts_without_rewriting_history(tmp_path):
    path = tmp_path / "unknown.db"
    engine = create_engine(f"sqlite:///{path}")
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
            conn.execute(text("INSERT INTO alembic_version VALUES ('unknown_revision')"))
        result = _migrate(path)
        assert result.returncode != 0
        assert "unknown_revision" in result.stdout + result.stderr
        with engine.connect() as conn:
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "unknown_revision"
    finally:
        engine.dispose()


def test_unversioned_existing_schema_uses_idempotent_bootstrap(tmp_path):
    from app import models

    path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{path}")
    try:
        models.MachineConfig.__table__.create(engine)
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO machine_config (id, purchase_price) VALUES (1, 9876)"))
        result = _migrate(path)
        assert result.returncode == 0, result.stdout + result.stderr
        with engine.connect() as conn:
            assert conn.execute(text("SELECT purchase_price FROM machine_config")).scalar_one() == 9876
            assert "printer_profile" in {
                col["name"] for col in inspect(conn).get_columns("feature_config")
            }
    finally:
        engine.dispose()


def test_valid_older_revision_upgrades_without_replaying_prior_data_migrations(tmp_path):
    from alembic import command
    from alembic.config import Config

    path = tmp_path / "older.db"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    # env.py reads DATABASE_URL at migration time rather than the config URL.
    import pytest
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite:///{path}")
        command.upgrade(config, "0024_project_include_preprime")
    engine = create_engine(f"sqlite:///{path}")
    try:
        with engine.begin() as conn:
            conn.execute(text(
                "UPDATE maintenance_presets SET volumes_json=:vols WHERE name='White Ink Flash Cleaning'"
            ), {"vols": '{"W":123}'})
        result = _migrate(path)
        assert result.returncode == 0, result.stdout + result.stderr
        with engine.connect() as conn:
            assert "printer_profile" in {
                col["name"] for col in inspect(conn).get_columns("feature_config")
            }
            assert conn.execute(text(
                "SELECT volumes_json FROM maintenance_presets WHERE name='White Ink Flash Cleaning'"
            )).scalar_one() == '{"W":123}'
    finally:
        engine.dispose()


def test_container_uses_the_tested_startup_migration_runner():
    entrypoint = (ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")
    assert "python -m app.migration_runner" in entrypoint
    assert "DELETE FROM alembic_version" not in entrypoint
