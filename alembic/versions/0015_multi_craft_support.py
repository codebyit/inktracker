"""Add multi-craft support (crafts_json) to projects and print_templates.

Revision ID: 0015_multi_craft
Revises: 0014_merge_heads
Create Date: 2026-06-28

Additive-only migration. A new ``crafts_json`` TEXT column stores an array of
craft variants per project/template. Existing rows are backfilled with a single
"Primary" variant synthesized from the legacy ``craft_mode`` / ``craft_ink_mode``
/ ``craft_mode_params_json`` fields (which are retained for backward compatibility).

Rollback strategy: the legacy single-craft columns are never dropped here, so
rolling the application image back to a pre-0006 build keeps every project
rendering its primary craft. The additive column is harmless if left in place,
hence ``downgrade`` is intentionally a no-op (consistent with 0004/0005).
"""
from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


revision = "0015_multi_craft"
down_revision = "0014_merge_heads"
branch_labels = None
depends_on = None


def _table_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(sa.text(f"PRAGMA table_info({table_name})")).fetchall()
        return {row[1] for row in rows}
    rows = bind.execute(sa.text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :table_name"
    ), {"table_name": table_name}).fetchall()
    return {row[0] for row in rows}


def _add_column_if_missing(table_name: str, column_name: str, ddl: str) -> None:
    if column_name not in _table_columns(table_name):
        op.execute(sa.text(ddl))


def _safe_json_dict(raw) -> dict:
    try:
        value = json.loads(raw or "{}")
    except (ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _safe_json_list(raw) -> list:
    try:
        value = json.loads(raw or "[]")
    except (ValueError, TypeError):
        return []
    return value if isinstance(value, list) else []


def _needs_backfill_clause(column: str) -> str:
    return f"{column} IS NULL OR {column} = '' OR {column} = '[]'"


def _backfill_project_crafts() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, craft_mode, craft_ink_mode, craft_mode_params_json, ink_mode, "
        "layer_stack_json, print_time_hours FROM projects "
        f"WHERE {_needs_backfill_clause('crafts_json')}"
    )).fetchall()
    for row in rows:
        project_id = row[0]
        ink_rows = bind.execute(sa.text(
            "SELECT channel, ml_used FROM project_ink_usage WHERE project_id = :pid"
        ), {"pid": project_id}).fetchall()
        ink_usage = {
            ir[0]: float(ir[1])
            for ir in ink_rows
            if ir[1] is not None and float(ir[1]) > 0
        }
        craft = {
            "variant_name": "Primary",
            "order_index": 0,
            "craft_mode": row[1] or "Flat",
            "craft_ink_mode": row[2] or "",
            "ink_mode": row[4] or "CMYK",
            "craft_mode_params": _safe_json_dict(row[3]),
            "layer_stack": _safe_json_list(row[5]),
            "ink_usage": ink_usage,
            "print_time_hours": float(row[6] or 0.0),
        }
        bind.execute(
            sa.text("UPDATE projects SET crafts_json = :cj WHERE id = :pid"),
            {"cj": json.dumps([craft]), "pid": project_id},
        )


def _backfill_template_crafts() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, craft_mode, craft_ink_mode, craft_mode_params_json, ink_mode, "
        "layer_stack_json FROM print_templates "
        f"WHERE {_needs_backfill_clause('crafts_json')}"
    )).fetchall()
    for row in rows:
        craft = {
            "variant_name": "Primary",
            "order_index": 0,
            "craft_mode": row[1] or "Flat",
            "craft_ink_mode": row[2] or "",
            "ink_mode": row[4] or "CMYK",
            "craft_mode_params": _safe_json_dict(row[3]),
            "layer_stack": _safe_json_list(row[5]),
            "ink_usage": {},
            "print_time_hours": 0.0,
        }
        bind.execute(
            sa.text("UPDATE print_templates SET crafts_json = :cj WHERE id = :tid"),
            {"cj": json.dumps([craft]), "tid": row[0]},
        )


def upgrade() -> None:
    _add_column_if_missing(
        "projects", "crafts_json",
        "ALTER TABLE projects ADD COLUMN crafts_json TEXT DEFAULT '[]'",
    )
    _add_column_if_missing(
        "print_templates", "crafts_json",
        "ALTER TABLE print_templates ADD COLUMN crafts_json TEXT DEFAULT '[]'",
    )
    _backfill_project_crafts()
    _backfill_template_crafts()


def downgrade() -> None:
    # Intentionally a no-op. The additive crafts_json column is harmless, and the
    # legacy single-craft columns remain authoritative, so an application rollback
    # needs no schema change. (Consistent with migrations 0004 and 0005.)
    pass
