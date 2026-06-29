from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect as sa_inspect, func as sa_func
from ..database import get_db, DB_INFO, _DB_PATH
from ..cache import invalidate_dashboard_analytics_cache
from .. import crud
from ..models import INK_CHANNELS, INK_CHANNEL_NAMES
from ..cogs import machine_cost_per_hour, machine_cost_breakdown
from ..security import require_admin
from ..templates_config import templates
import logging, json, io, time
from datetime import datetime

log = logging.getLogger(__name__)

# Hard cap on uploaded restore payloads to prevent OOM via 1+ GB files.
MAX_RESTORE_BYTES = 50 * 1024 * 1024

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    machine     = crud.get_machine_config(db)
    ink_cfgs    = crud.get_ink_configs(db)
    ink_global  = crud.get_ink_global_config(db)
    labor       = crud.get_labor_config(db)
    margins     = crud.get_margin_config(db)
    automation  = crud.get_automation_config(db)
    breakdown   = machine_cost_breakdown(machine)
    stats       = crud.get_data_stats(db)
    return templates.TemplateResponse(request, "settings.html", {
        "machine":           machine,
        "ink_cfgs":          ink_cfgs,
        "ink_global":        ink_global,
        "labor":             labor,
        "margins":           margins,
        "automation":        automation,
        "breakdown":         breakdown,
        "ink_channels":      INK_CHANNELS,
        "ink_channel_names": INK_CHANNEL_NAMES,
        "stats":             stats,
        "active":            "/settings",
        "tab":               request.query_params.get("tab", "ink"),
        "saved":             request.query_params.get("saved", ""),
    })


def _normalize_hhmm(raw: str) -> str:
    try:
        hh, mm = (raw or "").strip().split(":", 1)
        h, m = int(hh), int(mm)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"
    except ValueError:
        return "03:00"
    return "03:00"


# ── Ink ───────────────────────────────────────────────────────────────────────

@router.post("/settings/ink")
async def save_ink(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    capacity     = float(form.get("cartridge_capacity_ml", 100.0))
    tare_g       = float(form.get("cartridge_tare_g", 75.0))
    white_loaded = str(form.get("white_loaded", "W"))
    low_ink_pct  = float(form.get("low_ink_pct", 20.0))
    currency     = str(crud.get_currency(db))  # read current value, don't change it
    crud.update_ink_global_config(
        db,
        cartridge_capacity_ml=capacity,
        white_loaded=white_loaded,
        low_ink_pct=low_ink_pct,
        currency=currency,
        cartridge_tare_g=tare_g,
    )
    for ch in INK_CHANNELS:
        price    = float(form.get(f"price_{ch}", 45.0))
        preprime = float(form.get(f"preprime_{ch}", 0.0))
        density  = float(form.get(f"density_{ch}", 1.0))
        crud.update_ink_config(db, channel=ch, price=price, preprime_ml=preprime,
                               density_g_per_ml=density)
    templates.env.globals["currency"] = currency
    return RedirectResponse("/settings?tab=ink&saved=1", status_code=303)


# ── Machine ───────────────────────────────────────────────────────────────────

@router.post("/settings/machine")
def save_machine(
    purchase_price:     float = Form(...),
    setup_cost:         float = Form(0.0),
    lifespan_hours:     float = Form(...),
    annual_hours:       float = Form(...),
    power_watts:        float = Form(...),
    electricity_rate:   float = Form(...),
    annual_maintenance: float = Form(...),
    db: Session = Depends(get_db),
):
    crud.update_machine_config(
        db,
        purchase_price=purchase_price,
        setup_cost=setup_cost,
        lifespan_hours=lifespan_hours,
        annual_hours=annual_hours,
        power_watts=power_watts,
        electricity_rate=electricity_rate,
        annual_maintenance=annual_maintenance,
    )
    return RedirectResponse("/settings?tab=machine&saved=1", status_code=303)


# ── Preferences ───────────────────────────────────────────────────────────────

@router.post("/settings/preferences")
def save_preferences(
    retail_minimum:    float = Form(...),
    retail_target:     float = Form(...),
    retail_strong:     float = Form(...),
    wholesale_minimum: float = Form(...),
    wholesale_target:  float = Form(...),
    wholesale_strong:  float = Form(...),
    low_inventory_lot_pct: float = Form(25.0),
    db: Session = Depends(get_db),
):
    crud.update_margin_config(
        db,
        retail_minimum=retail_minimum,
        retail_target=retail_target,
        retail_strong=retail_strong,
        wholesale_minimum=wholesale_minimum,
        wholesale_target=wholesale_target,
        wholesale_strong=wholesale_strong,
    )
    ink_global = crud.get_ink_global_config(db)
    ink_global.low_inventory_lot_pct = max(0.0, min(100.0, float(low_inventory_lot_pct or 25.0)))
    db.commit()
    invalidate_dashboard_analytics_cache()
    return RedirectResponse("/settings?tab=preferences&saved=1", status_code=303)


# ── Labor (kept for wizard COGS compatibility) ────────────────────────────────

@router.post("/settings/preferences/display")
async def save_display(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    currency = str(form.get("currency", "€"))
    cfg = crud.get_ink_global_config(db)
    cfg.currency = currency
    db.commit()
    invalidate_dashboard_analytics_cache()
    templates.env.globals["currency"] = currency
    return RedirectResponse("/settings?tab=preferences&saved=1", status_code=303)


@router.post("/settings/labor")
def save_labor(
    hourly_rate:  float = Form(...),
    overhead_pct: float = Form(...),
    db: Session = Depends(get_db),
):
    crud.update_labor_config(db, hourly_rate=hourly_rate, overhead_pct=overhead_pct)
    return RedirectResponse("/settings?tab=preferences&saved=1", status_code=303)


@router.post("/settings/preferences/automation")
async def save_automation_settings(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    enabled = (form.get("auto_maintenance_log_enabled") or "").strip().lower() in {"1", "true", "on", "yes"}
    run_time = _normalize_hhmm(str(form.get("auto_maintenance_log_time") or "03:00"))
    crud.update_automation_config(db, enabled=enabled, run_time=run_time)
    return RedirectResponse("/settings?tab=preferences&saved=1", status_code=303)


# ── Data ──────────────────────────────────────────────────────────────────────
# Destructive data endpoints are guarded by the opt-in admin auth
# dependency. When ADMIN_API_TOKEN is unset the dependency is a no-op so
# existing private-network deployments keep working unchanged.

@router.post("/settings/reset", dependencies=[Depends(require_admin)])
def factory_reset(db: Session = Depends(get_db)):
    crud.factory_reset(db)
    return RedirectResponse("/settings?tab=data&saved=reset", status_code=303)


def _row_to_dict(instance) -> dict:
    result = {}
    for col in sa_inspect(instance.__class__).column_attrs:
        val = getattr(instance, col.key)
        if isinstance(val, datetime):
            val = val.isoformat()
        result[col.key] = val
    return result


@router.get("/api/db-status")
def api_db_status(db: Session = Depends(get_db)):
    t0 = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        ok = True
    except Exception:
        latency_ms = None
        ok = False

    size_bytes = None
    alembic_revision = None
    alembic_ok = False

    try:
        alembic_revision = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        alembic_ok = bool(alembic_revision)
    except Exception:
        alembic_revision = None
        alembic_ok = False

    if ok:
        try:
            if DB_INFO.get("type") == "postgresql":
                size_bytes = db.execute(
                    text("SELECT pg_database_size(current_database())")
                ).scalar()
            else:
                size_bytes = _DB_PATH.stat().st_size if _DB_PATH.exists() else 0
        except Exception:
            size_bytes = None

    return JSONResponse({
        **DB_INFO,
        "ok": ok,
        "latency_ms": latency_ms,
        "size_bytes": size_bytes,
        "alembic_ok": alembic_ok,
        "alembic_revision": alembic_revision,
    })


@router.get("/settings/backup", dependencies=[Depends(require_admin)])
def download_backup(db: Session = Depends(get_db)):
    from .. import models
    export_models = [
        models.MachineConfig, models.InkChannelConfig, models.InkGlobalConfig,
        models.LaborConfig, models.MarginConfig,
        models.Project, models.BOMItem, models.ProjectInkUsage,
        models.CartridgeReplacement, models.MaintenancePreset, models.ServiceAction,
        models.PrintTemplate, models.MaterialCategory, models.MaterialItem,
        models.MaterialInventoryMovement, models.CartridgeInventoryLot,
    ]
    data = {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "engine": DB_INFO.get("type", "unknown"),
        "tables": {m.__tablename__: [_row_to_dict(r) for r in db.query(m).all()]
                   for m in export_models},
    }
    payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    fname = f"inktracker-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    return StreamingResponse(
        io.BytesIO(payload),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post("/settings/restore", dependencies=[Depends(require_admin)])
async def upload_restore(file: UploadFile = File(...), db: Session = Depends(get_db)):
    from .. import models
    content = await file.read()
    if len(content) > MAX_RESTORE_BYTES:
        log.warning(
            "Restore upload rejected: %d bytes exceeds cap of %d",
            len(content), MAX_RESTORE_BYTES,
        )
        return JSONResponse(
            {"error": f"Backup file too large (max {MAX_RESTORE_BYTES // (1024 * 1024)} MB)"},
            status_code=413,
        )
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON file"}, status_code=400)
    if data.get("version") != "1.0":
        return JSONResponse({"error": "Unsupported backup version"}, status_code=400)

    tables_data = data.get("tables", {})

    # Restore order respects FK constraints
    restore_map = [
        ("machine_config",         models.MachineConfig),
        ("ink_global_config",      models.InkGlobalConfig),
        ("ink_channel_config",     models.InkChannelConfig),
        ("labor_config",           models.LaborConfig),
        ("margin_config",          models.MarginConfig),
        ("material_categories",    models.MaterialCategory),
        ("material_items",         models.MaterialItem),
        ("print_templates",        models.PrintTemplate),
        ("projects",               models.Project),
        ("bom_items",              models.BOMItem),
        ("project_ink_usage",      models.ProjectInkUsage),
        ("material_inventory_movements", models.MaterialInventoryMovement),
        ("cartridge_replacements", models.CartridgeReplacement),
        ("cartridge_inventory_lots", models.CartridgeInventoryLot),
        ("maintenance_presets",    models.MaintenancePreset),
        ("service_actions",        models.ServiceAction),
    ]

    try:
        for _, model_cls in reversed(restore_map):
            db.query(model_cls).delete()
        db.flush()

        for table_name, model_cls in restore_map:
            # Whitelist columns from the model schema so an adulterated
            # backup cannot inject unknown keys or trigger TypeError on
            # construction.
            allowed_cols = {c.name for c in model_cls.__table__.columns}
            for row in tables_data.get(table_name, []):
                if not isinstance(row, dict):
                    continue
                clean: dict = {}
                for k, v in row.items():
                    if k not in allowed_cols:
                        continue
                    # Parse ISO datetime strings safely.
                    if isinstance(v, str) and "T" in v and len(v) >= 19:
                        try:
                            v = datetime.fromisoformat(v)
                        except ValueError:
                            pass
                    clean[k] = v
                db.add(model_cls(**clean))

        db.commit()

        # Reset PostgreSQL sequences so future inserts don't collide
        if DB_INFO.get("type") == "postgresql":
            for table_name, model_cls in restore_map:
                max_id = db.query(sa_func.max(model_cls.id)).scalar() or 1
                db.execute(text(
                    "SELECT setval(pg_get_serial_sequence(:table_name, 'id'), :max_id)"
                ), {"table_name": table_name, "max_id": max_id})
            db.commit()

        invalidate_dashboard_analytics_cache()

        return JSONResponse({"ok": True})
    except Exception as e:
        db.rollback()
        log.exception("Restore failed")
        return JSONResponse({"error": str(e)}, status_code=500)

