import json
from datetime import datetime
from collections import defaultdict
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session
from . import models
from .models import INK_CHANNELS, SERVICE_CHANNELS, INK_CHANNEL_DEFAULT_CAPACITY
from .cogs import calculate_cogs, margin_status, ink_level_pct, ink_level_status


def _invalidate_dashboard_analytics_cache() -> None:
    try:
        from .cache import invalidate_dashboard_analytics_cache
        invalidate_dashboard_analytics_cache()
    except Exception:
        # Cache is optional; never fail writes because of cache issues.
        return


# ── Seeding ───────────────────────────────────────────────────────────────────

def seed_defaults(db: Session) -> None:
    if not db.query(models.MachineConfig).first():
        db.add(models.MachineConfig(
            id=1, purchase_price=2500.0, setup_cost=0.0,
            lifespan_hours=10000.0, annual_hours=500.0,
            power_watts=250.0, electricity_rate=0.13,
            annual_maintenance=499.0,
        ))

    channel_defaults = [
        ("C",  45.0), ("M", 45.0), ("Y",  45.0),
        ("K",  45.0), ("W", 45.0), ("GL", 45.0), ("FW", 45.0),
        ("CLN", 0.0), ("ML", 0.0),
    ]
    for ch, price in channel_defaults:
        if not db.query(models.InkChannelConfig).filter_by(channel=ch).first():
            db.add(models.InkChannelConfig(
                channel=ch, price_per_cartridge=price,
                cartridge_capacity_ml=INK_CHANNEL_DEFAULT_CAPACITY.get(ch, 100.0),
                preprime_ml=0.0,
            ))

    if not db.query(models.InkGlobalConfig).first():
        db.add(models.InkGlobalConfig(
            id=1, cartridge_capacity_ml=100.0,
            white_loaded="W", low_ink_pct=20.0, low_inventory_lot_pct=25.0, currency="€",
        ))

    if not db.query(models.LaborConfig).first():
        db.add(models.LaborConfig(id=1, hourly_rate=15.0, overhead_pct=25.0))

    if not db.query(models.MarginConfig).first():
        db.add(models.MarginConfig(
            id=1,
            retail_minimum=30.0, retail_target=50.0, retail_strong=65.0,
            wholesale_minimum=20.0, wholesale_target=35.0, wholesale_strong=50.0,
        ))

    if not db.query(models.AutomationConfig).first():
        db.add(models.AutomationConfig(
            id=1,
            auto_maintenance_log_enabled=True,
            auto_maintenance_log_time="03:00",
        ))

    default_cats = ["Substrate", "Packaging", "Finishing", "Consumable", "Other"]
    existing_cats = {c.name for c in db.query(models.MaterialCategory).all()}
    for i, cat in enumerate(default_cats):
        if cat not in existing_cats:
            db.add(models.MaterialCategory(name=cat, sort_order=i))

    db.commit()

    # Seed default maintenance presets (idempotent: only when table is empty).
    seed_default_presets(db)


# ── Settings ──────────────────────────────────────────────────────────────────

def get_machine_config(db: Session) -> models.MachineConfig:
    return db.query(models.MachineConfig).first()


def update_machine_config(db: Session, **kwargs) -> models.MachineConfig:
    cfg = db.query(models.MachineConfig).first()
    for k, v in kwargs.items():
        setattr(cfg, k, v)
    db.commit()
    _invalidate_dashboard_analytics_cache()
    return cfg


def get_ink_configs(db: Session) -> dict:
    return {c.channel: c for c in db.query(models.InkChannelConfig).all()}


def get_ink_global_config(db: Session) -> models.InkGlobalConfig:
    return db.query(models.InkGlobalConfig).first()


def get_currency(db: Session) -> str:
    cfg = db.query(models.InkGlobalConfig).first()
    return cfg.currency if cfg else "€"


def update_ink_config(db: Session, channel: str, price: float, preprime_ml: float = 0.0) -> None:
    cfg = db.query(models.InkChannelConfig).filter_by(channel=channel).first()
    cfg.price_per_cartridge = price
    cfg.preprime_ml = preprime_ml
    db.commit()
    _invalidate_dashboard_analytics_cache()


def update_ink_global_config(
    db: Session,
    cartridge_capacity_ml: float,
    white_loaded: str,
    low_ink_pct: float,
    currency: str,
) -> None:
    cfg = db.query(models.InkGlobalConfig).first()
    cfg.cartridge_capacity_ml = cartridge_capacity_ml
    cfg.white_loaded = white_loaded
    cfg.low_ink_pct = low_ink_pct
    cfg.currency = currency
    # Sync capacity to all channels
    for ch_cfg in db.query(models.InkChannelConfig).all():
        ch_cfg.cartridge_capacity_ml = cartridge_capacity_ml
    db.commit()
    _invalidate_dashboard_analytics_cache()


def get_labor_config(db: Session) -> models.LaborConfig:
    return db.query(models.LaborConfig).first()


def update_labor_config(db: Session, hourly_rate: float, overhead_pct: float) -> None:
    cfg = db.query(models.LaborConfig).first()
    cfg.hourly_rate = hourly_rate
    cfg.overhead_pct = overhead_pct
    db.commit()
    _invalidate_dashboard_analytics_cache()


def get_margin_config(db: Session) -> models.MarginConfig:
    return db.query(models.MarginConfig).first()


def update_margin_config(
    db: Session,
    retail_minimum: float, retail_target: float, retail_strong: float,
    wholesale_minimum: float, wholesale_target: float, wholesale_strong: float,
) -> None:
    cfg = db.query(models.MarginConfig).first()
    cfg.retail_minimum    = retail_minimum
    cfg.retail_target     = retail_target
    cfg.retail_strong     = retail_strong
    cfg.wholesale_minimum = wholesale_minimum
    cfg.wholesale_target  = wholesale_target
    cfg.wholesale_strong  = wholesale_strong
    db.commit()
    _invalidate_dashboard_analytics_cache()


def get_automation_config(db: Session) -> models.AutomationConfig:
    cfg = db.query(models.AutomationConfig).first()
    if cfg is None:
        cfg = models.AutomationConfig(
            id=1,
            auto_maintenance_log_enabled=True,
            auto_maintenance_log_time="03:00",
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def update_automation_config(db: Session, *, enabled: bool, run_time: str) -> None:
    cfg = get_automation_config(db)
    cfg.auto_maintenance_log_enabled = bool(enabled)
    cfg.auto_maintenance_log_time = run_time
    db.commit()


def get_data_stats(db: Session) -> dict:
    return {
        "projects":     db.query(models.Project).count(),
        "replacements": db.query(models.CartridgeReplacement).count(),
        "maintenance":  db.query(models.ServiceAction).count(),
    }


def factory_reset(db: Session) -> None:
    """Delete all user-generated data. Settings are preserved."""
    db.query(models.ProjectInkUsage).delete()
    db.query(models.BOMItem).delete()
    db.query(models.Project).delete()
    db.query(models.CartridgeReplacement).delete()
    db.query(models.CartridgeInventoryLot).delete()
    db.query(models.MaterialInventoryMovement).delete()
    db.query(models.ServiceAction).delete()
    db.commit()
    _invalidate_dashboard_analytics_cache()


def get_settings_json(db: Session) -> dict:
    """Returns a JSON-serialisable dict of all settings — used by the wizard."""
    machine    = get_machine_config(db)
    ink_cfgs   = get_ink_configs(db)
    ink_global = get_ink_global_config(db)
    labor      = get_labor_config(db)
    margins    = get_margin_config(db)
    capacity   = ink_global.cartridge_capacity_ml if ink_global else 100.0
    return {
        "machine": {
            "purchase_price":    machine.purchase_price,
            "setup_cost":        machine.setup_cost,
            "lifespan_hours":    machine.lifespan_hours,
            "annual_hours":      machine.annual_hours,
            "power_watts":       machine.power_watts,
            "electricity_rate":  machine.electricity_rate,
            "annual_maintenance":machine.annual_maintenance,
        },
        "ink": {
            ch: {
                "price":       cfg.price_per_cartridge,
                "capacity":    capacity,
                "preprime_ml": cfg.preprime_ml if cfg else 0.0,
            }
            for ch, cfg in ink_cfgs.items()
        },
        "white_loaded": ink_global.white_loaded if ink_global else "W",
        "low_inventory_lot_pct": ink_global.low_inventory_lot_pct if ink_global else 25.0,
        "labor": {
            "hourly_rate":  labor.hourly_rate,
            "overhead_pct": labor.overhead_pct,
        },
        "margins": {
            "strong": margins.retail_strong,
            "target": margins.retail_target,
        },
    }


# ── Projects ──────────────────────────────────────────────────────────────────

_PIPELINE_STATUSES  = ["Draft", "Queued", "Printing"]
_COMPLETED_STATUSES = ["Completed", "Cancelled", "Failed"]


def _apply_sort(q, sort: str):
    if sort == "oldest":
        return q.order_by(models.Project.created_at.asc())
    if sort == "name":
        return q.order_by(models.Project.name.asc())
    if sort == "margin":
        return q.order_by(models.Project.margin_pct.desc())
    if sort == "revenue":
        return q.order_by(models.Project.total_revenue.desc())
    return q.order_by(models.Project.created_at.desc())  # newest


def _active_q(db):
    return db.query(models.Project).filter(
        models.Project.deleted_at == None,  # noqa: E711
        models.Project.archived == False,   # noqa: E712
    )


def get_pipeline_projects(db: Session, search: str = "", sort: str = "newest") -> list:
    q = _active_q(db).filter(models.Project.status.in_(_PIPELINE_STATUSES))
    if search:
        q = q.filter(models.Project.name.ilike(f"%{search}%"))
    return _apply_sort(q, sort).all()


def get_completed_projects(db: Session, search: str = "", sort: str = "newest") -> list:
    q = _active_q(db).filter(models.Project.status.in_(_COMPLETED_STATUSES))
    if search:
        q = q.filter(models.Project.name.ilike(f"%{search}%"))
    return _apply_sort(q, sort).all()


def get_archived_projects(db: Session, search: str = "", sort: str = "newest") -> list:
    q = db.query(models.Project).filter(
        models.Project.archived == True,    # noqa: E712
        models.Project.deleted_at == None,  # noqa: E711
    )
    if search:
        q = q.filter(models.Project.name.ilike(f"%{search}%"))
    return _apply_sort(q, sort).all()


def get_trash_projects(db: Session) -> list:
    return (
        db.query(models.Project)
        .filter(models.Project.deleted_at != None)  # noqa: E711
        .order_by(models.Project.deleted_at.desc())
        .all()
    )


def create_project(
    db: Session,
    name: str,
    units: int,
    sell_price_per_unit: float,
    print_time_hours: float,
    hands_on_hours: float,
    ink_mode: str,
    print_quality: str,
    ink_usage: dict,   # {channel: ml}
    bom_items: list,   # [{name, quantity, unit, unit_cost}]
    material: str = "Ceramics",
    notes: str = "",
    photo_path: str = None,
    print_bed: str = "Standard",
    alignment: str = "Photo",
    craft_mode: str = "Flat",
    craft_ink_mode: str = "",
    craft_mode_params_json: str = "{}",
    substrate: str = "",
    white_choke_mm: float = 0.20,
    layer_stack_json: str = "[]",
    status: str = "Draft",
    project_type: str = "commercial",
) -> models.Project:
    substrate_normalized = (substrate or "").strip()
    machine_cfg = get_machine_config(db)
    ink_cfgs    = get_ink_configs(db)
    labor_cfg   = get_labor_config(db)
    margin_cfg  = get_margin_config(db)

    bom_total = sum(float(i.get("quantity", 1)) * float(i.get("unit_cost", 0)) for i in bom_items)

    cogs = calculate_cogs(
        ink_usage=ink_usage,
        bom_total=bom_total,
        machine_cfg=machine_cfg,
        ink_cfgs=ink_cfgs,
        labor_cfg=labor_cfg,
        print_time_hours=print_time_hours,
        hands_on_hours=hands_on_hours,
        units=units,
    )

    is_commercial = (project_type or "commercial") == "commercial"
    total_revenue = float(sell_price_per_unit) * units
    total_profit  = total_revenue - cogs["total_cogs"]
    if is_commercial and total_revenue > 0:
        margin_pct = total_profit / total_revenue * 100
        m_status   = margin_status(margin_pct, margin_cfg)
    else:
        margin_pct = 0.0
        m_status   = "N/A"

    project = models.Project(
        name=name, units=units,
        sell_price_per_unit=float(sell_price_per_unit),
        print_time_hours=float(print_time_hours),
        hands_on_hours=float(hands_on_hours),
        ink_mode=ink_mode, print_quality=print_quality,
        material=material,
        photo_path=photo_path, notes=notes,
        print_bed=print_bed, alignment=alignment,
        craft_mode=craft_mode, craft_ink_mode=craft_ink_mode,
        craft_mode_params_json=craft_mode_params_json, substrate=substrate_normalized,
        white_choke_mm=white_choke_mm, layer_stack_json=layer_stack_json,
        ink_cost=cogs["ink_cost"],      bom_cost=cogs["bom_cost"],
        machine_cost=cogs["machine_cost"], labor_cost=cogs["labor_cost"],
        overhead_cost=cogs["overhead_cost"], total_cogs=cogs["total_cogs"],
        cogs_per_unit=cogs["cogs_per_unit"],
        total_revenue=round(total_revenue, 4),
        total_profit=round(total_profit, 4),
        margin_pct=round(margin_pct, 2),
        margin_status=m_status,
        status=status,
        project_type=project_type or "commercial",
        completed_at=datetime.utcnow() if status == "Completed" else None,
    )
    db.add(project)
    db.flush()

    for ch, ml in ink_usage.items():
        if float(ml) > 0:
            db.add(models.ProjectInkUsage(project_id=project.id, channel=ch, ml_used=float(ml)))

    for item in bom_items:
        if item.get("name", "").strip():
            qty  = float(item.get("quantity", 1))
            cost = float(item.get("unit_cost", 0))
            db.add(models.BOMItem(
                project_id=project.id,
                name=item["name"].strip(),
                quantity=qty,
                unit=item.get("unit", "pcs"),
                unit_cost=cost,
                total_cost=round(qty * cost, 4),
            ))

    _sync_project_substrate_inventory(
        db,
        project=project,
        old_substrate="",
        old_units=0,
        notes=f"Auto-consumed from project #{project.id}: {project.name}",
    )

    db.commit()
    db.refresh(project)
    _invalidate_dashboard_analytics_cache()
    return project


def update_project(
    db: Session,
    project_id: int,
    name: str,
    units: int,
    sell_price_per_unit: float,
    print_time_hours: float,
    hands_on_hours: float,
    ink_mode: str,
    print_quality: str,
    ink_usage: dict,
    bom_items: list,
    material: str = "Ceramics",
    notes: str = "",
    photo_path: str = None,
    print_bed: str = "Standard",
    alignment: str = "Photo",
    craft_mode: str = "Flat",
    craft_ink_mode: str = "",
    craft_mode_params_json: str = "{}",
    substrate: str = "",
    white_choke_mm: float = 0.20,
    layer_stack_json: str = "[]",
    status: str = None,
    project_type: str = None,
) -> models.Project | None:
    project = get_project(db, project_id)
    if not project:
        return None

    old_substrate = (project.substrate or "").strip()
    old_units = int(project.units or 0)
    new_substrate = (substrate or "").strip()

    machine_cfg = get_machine_config(db)
    ink_cfgs    = get_ink_configs(db)
    labor_cfg   = get_labor_config(db)
    margin_cfg  = get_margin_config(db)

    bom_total = sum(float(i.get("quantity", 1)) * float(i.get("unit_cost", 0)) for i in bom_items)

    cogs = calculate_cogs(
        ink_usage=ink_usage,
        bom_total=bom_total,
        machine_cfg=machine_cfg,
        ink_cfgs=ink_cfgs,
        labor_cfg=labor_cfg,
        print_time_hours=print_time_hours,
        hands_on_hours=hands_on_hours,
        units=units,
    )

    effective_type = project_type if project_type is not None else (project.project_type or "commercial")
    is_commercial  = effective_type == "commercial"
    total_revenue  = float(sell_price_per_unit) * units
    total_profit   = total_revenue - cogs["total_cogs"]
    if is_commercial and total_revenue > 0:
        margin_pct = total_profit / total_revenue * 100
        m_status   = margin_status(margin_pct, margin_cfg)
    else:
        margin_pct = 0.0
        m_status   = "N/A"

    project.name                = name
    project.units               = units
    project.sell_price_per_unit = float(sell_price_per_unit)
    project.print_time_hours    = float(print_time_hours)
    project.hands_on_hours      = float(hands_on_hours)
    project.ink_mode            = ink_mode
    project.print_quality       = print_quality
    project.material            = material
    project.notes               = notes
    project.print_bed           = print_bed
    project.alignment           = alignment
    project.craft_mode          = craft_mode
    project.craft_ink_mode      = craft_ink_mode
    project.craft_mode_params_json = craft_mode_params_json
    project.substrate           = new_substrate
    project.white_choke_mm      = white_choke_mm
    project.layer_stack_json    = layer_stack_json
    if photo_path is not None:
        project.photo_path = photo_path
    project.ink_cost     = cogs["ink_cost"]
    project.bom_cost     = cogs["bom_cost"]
    project.machine_cost = cogs["machine_cost"]
    project.labor_cost   = cogs["labor_cost"]
    project.overhead_cost= cogs["overhead_cost"]
    project.total_cogs   = cogs["total_cogs"]
    project.cogs_per_unit= cogs["cogs_per_unit"]
    project.total_revenue= round(total_revenue, 4)
    project.total_profit = round(total_profit, 4)
    project.margin_pct   = round(margin_pct, 2)
    project.margin_status= m_status
    if project_type is not None:
        project.project_type = project_type
    if status is not None:
        project.status = status
        if status == "Completed":
            if not project.completed_at:
                project.completed_at = datetime.utcnow()
        else:
            project.completed_at = None

    db.query(models.ProjectInkUsage).filter_by(project_id=project_id).delete()
    db.query(models.BOMItem).filter_by(project_id=project_id).delete()
    db.flush()

    for ch, ml in ink_usage.items():
        if float(ml) > 0:
            db.add(models.ProjectInkUsage(project_id=project_id, channel=ch, ml_used=float(ml)))

    for item in bom_items:
        if item.get("name", "").strip():
            qty  = float(item.get("quantity", 1))
            cost = float(item.get("unit_cost", 0))
            db.add(models.BOMItem(
                project_id=project_id,
                name=item["name"].strip(),
                quantity=qty,
                unit=item.get("unit", "pcs"),
                unit_cost=cost,
                total_cost=round(qty * cost, 4),
            ))

    _sync_project_substrate_inventory(
        db,
        project=project,
        old_substrate=old_substrate,
        old_units=old_units,
        notes=f"Auto-adjusted from project update #{project.id}: {project.name}",
    )

    db.commit()
    db.refresh(project)
    _invalidate_dashboard_analytics_cache()
    return project


def get_projects(db: Session, skip: int = 0, limit: int = 200) -> list:
    return (
        db.query(models.Project)
        .order_by(models.Project.created_at.desc())
        .offset(skip).limit(limit).all()
    )


def get_project(db: Session, project_id: int) -> models.Project | None:
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def delete_project(db: Session, project_id: int) -> None:
    """Move project to Trash (soft delete)."""
    p = get_project(db, project_id)
    if p:
        p.deleted_at = datetime.utcnow()
        db.commit()
        _invalidate_dashboard_analytics_cache()


def restore_project(db: Session, project_id: int) -> None:
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if p:
        p.deleted_at = None
        db.commit()
        _invalidate_dashboard_analytics_cache()


def permanent_delete_project(db: Session, project_id: int) -> None:
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if p:
        db.delete(p)
        db.commit()
        _invalidate_dashboard_analytics_cache()


def archive_project(db: Session, project_id: int) -> None:
    p = get_project(db, project_id)
    if p:
        p.archived = True
        db.commit()
        _invalidate_dashboard_analytics_cache()


def unarchive_project(db: Session, project_id: int) -> None:
    p = get_project(db, project_id)
    if p:
        p.archived = False
        db.commit()
        _invalidate_dashboard_analytics_cache()


def set_project_status(db: Session, project_id: int, status: str) -> models.Project | None:
    p = get_project(db, project_id)
    if not p:
        return None
    p.status = status
    if status == "Completed":
        if not p.completed_at:
            p.completed_at = datetime.utcnow()
    else:
        p.completed_at = None
    db.commit()
    _invalidate_dashboard_analytics_cache()
    return p


def duplicate_project(db: Session, project_id: int) -> models.Project | None:
    p = get_project(db, project_id)
    if not p:
        return None
    ink_usage = {u.channel: u.ml_used for u in p.ink_usage}
    bom_items = [
        {"name": b.name, "quantity": b.quantity, "unit": b.unit, "unit_cost": b.unit_cost}
        for b in p.bom_items
    ]
    return create_project(
        db=db,
        name=f"Copy of {p.name}",
        units=p.units,
        sell_price_per_unit=p.sell_price_per_unit,
        print_time_hours=p.print_time_hours,
        hands_on_hours=p.hands_on_hours,
        ink_mode=p.ink_mode,
        print_quality=p.print_quality,
        ink_usage=ink_usage,
        bom_items=bom_items,
        material=p.material or "Ceramics",
        notes=p.notes or "",
        print_bed=p.print_bed or "Standard",
        alignment=p.alignment or "Photo",
        craft_mode=p.craft_mode or "Flat",
        craft_ink_mode=p.craft_ink_mode or "",
        craft_mode_params_json=p.craft_mode_params_json or "{}",
        substrate=p.substrate or "",
        white_choke_mm=p.white_choke_mm or 0.20,
        layer_stack_json=p.layer_stack_json or "[]",
        status="Draft",
    )


# ── Print Templates ───────────────────────────────────────────────────────────

def get_templates(db: Session) -> list:
    return db.query(models.PrintTemplate).order_by(models.PrintTemplate.created_at.desc()).all()


def create_template(
    db: Session, name: str, print_bed: str, alignment: str,
    material: str, substrate: str, print_quality: str,
    white_choke_mm: float, craft_mode: str, ink_mode: str,
    craft_ink_mode: str,
    craft_mode_params_json: str,
    layer_stack_json: str,
) -> models.PrintTemplate:
    t = models.PrintTemplate(
        name=name, print_bed=print_bed, alignment=alignment,
        material=material, substrate=substrate, print_quality=print_quality,
        white_choke_mm=white_choke_mm, craft_mode=craft_mode,
        ink_mode=ink_mode, craft_ink_mode=craft_ink_mode,
        craft_mode_params_json=craft_mode_params_json,
        layer_stack_json=layer_stack_json,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def delete_template(db: Session, template_id: int) -> None:
    t = db.query(models.PrintTemplate).filter_by(id=template_id).first()
    if t:
        db.delete(t)
        db.commit()


# ── Materials Library ──────────────────────────────────────────────────────────

def get_material_categories(db: Session) -> list:
    return db.query(models.MaterialCategory).order_by(models.MaterialCategory.sort_order, models.MaterialCategory.name).all()


def create_material_category(db: Session, name: str) -> models.MaterialCategory:
    max_order = db.query(models.MaterialCategory).count()
    cat = models.MaterialCategory(name=name.strip(), sort_order=max_order)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def delete_material_category(db: Session, name: str) -> None:
    cat = db.query(models.MaterialCategory).filter_by(name=name).first()
    if cat:
        # Re-assign orphaned items to "Other"
        db.query(models.MaterialItem).filter_by(category=name).update({"category": "Other"})
        db.delete(cat)
        db.commit()


def get_material_items(db: Session) -> list:
    return db.query(models.MaterialItem).order_by(models.MaterialItem.category, models.MaterialItem.name).all()


def get_material_item_by_name(db: Session, name: str) -> models.MaterialItem | None:
    needle = (name or "").strip()
    if not needle:
        return None
    return db.query(models.MaterialItem).filter(models.MaterialItem.name.ilike(needle)).first()


def create_material_item(db: Session, name: str, category: str, unit_cost: float, unit: str) -> models.MaterialItem:
    item = models.MaterialItem(name=name.strip(), category=category, unit_cost=unit_cost, unit=unit)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_material_item(db: Session, item_id: int, name: str, category: str, unit_cost: float, unit: str) -> models.MaterialItem | None:
    item = db.query(models.MaterialItem).filter_by(id=item_id).first()
    if item:
        item.name = name.strip()
        item.category = category
        item.unit_cost = unit_cost
        item.unit = unit
        db.commit()
        db.refresh(item)
    return item


def delete_material_item(db: Session, item_id: int) -> None:
    item = db.query(models.MaterialItem).filter_by(id=item_id).first()
    if item:
        material_name = (item.name or "").strip()
        material_name_lc = material_name.lower()

        substrate_refs = (
            db.query(models.Project.id)
            .filter(models.Project.deleted_at == None)  # noqa: E711
            .filter(sa_func.lower(sa_func.trim(models.Project.substrate)) == material_name_lc)
            .count()
        )

        template_refs = (
            db.query(models.PrintTemplate.id)
            .filter(sa_func.lower(sa_func.trim(models.PrintTemplate.substrate)) == material_name_lc)
            .count()
        )

        if substrate_refs > 0 or template_refs > 0:
            reasons = []
            if substrate_refs > 0:
                reasons.append(f"{substrate_refs} existing project(s)")
            if template_refs > 0:
                reasons.append(f"{template_refs} print template(s)")
            reason_text = " and ".join(reasons)
            raise ValueError(f"Material '{item.name}' is used as substrate in {reason_text}.")

        db.query(models.MaterialInventoryMovement).filter_by(material_item_id=item.id).delete()
        db.delete(item)
        db.commit()


def create_material_inventory_movement(
    db: Session,
    *,
    material_item_id: int,
    movement_type: str,
    quantity: float,
    project_id: int | None = None,
    notes: str = "",
    occurred_at: datetime | None = None,
) -> models.MaterialInventoryMovement:
    movement_kind = (movement_type or "").strip().lower()
    if movement_kind not in {"in", "out"}:
        raise ValueError("movement_type must be 'in' or 'out'")

    qty = float(quantity or 0.0)
    if qty <= 0:
        raise ValueError("quantity must be greater than zero")

    item = db.query(models.MaterialItem).filter_by(id=material_item_id).first()
    if not item:
        raise ValueError("material item not found")

    movement = models.MaterialInventoryMovement(
        material_item_id=material_item_id,
        project_id=project_id,
        movement_type=movement_kind,
        quantity=qty,
        occurred_at=occurred_at or datetime.utcnow(),
        notes=(notes or "").strip() or None,
    )
    db.add(movement)

    if movement_kind == "in":
        item.quantity_added_total = float(item.quantity_added_total or 0.0) + qty
    else:
        item.quantity_consumed_total = float(item.quantity_consumed_total or 0.0) + qty

    db.flush()
    return movement


def get_material_inventory_movements(db: Session, *, limit: int = 200) -> list:
    return (
        db.query(models.MaterialInventoryMovement)
        .order_by(models.MaterialInventoryMovement.occurred_at.desc(), models.MaterialInventoryMovement.id.desc())
        .limit(limit)
        .all()
    )


def get_material_inventory_balance(db: Session) -> list[dict]:
    items = get_material_items(db)
    out = []
    for item in items:
        added = float(item.quantity_added_total or 0.0)
        consumed = float(item.quantity_consumed_total or 0.0)
        out.append({
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "unit": item.unit,
            "unit_cost": float(item.unit_cost or 0.0),
            "quantity_added_total": added,
            "quantity_consumed_total": consumed,
            "quantity_available": round(added - consumed, 4),
        })
    return out


# ── Dashboard ─────────────────────────────────────────────────────────────────

def get_dashboard_kpis(db: Session) -> dict:
    projects = db.query(models.Project).all()
    machine  = get_machine_config(db)

    # Guard against legacy rows with null financial fields.
    total_revenue = sum((p.total_revenue or 0.0) for p in projects)
    total_profit  = sum((p.total_profit or 0.0) for p in projects)
    total_units   = sum((p.units or 0) for p in projects)

    commercial = [p for p in projects if (p.project_type or "commercial") == "commercial"]
    avg_margin = (sum((p.margin_pct or 0.0) for p in commercial) / len(commercial)) if commercial else 0.0

    machine_price = (machine.purchase_price or 0.0) if machine else 0.0
    break_even_pct = 0.0
    if machine_price > 0:
        break_even_pct = min(100.0, round(total_profit / machine_price * 100, 1))

    loss_projects      = [p for p in projects if p.margin_status == "Loss"]
    waste_loss_count   = len(loss_projects)
    waste_loss_total   = round(sum(abs(p.total_profit or 0.0) for p in loss_projects), 2)

    return {
        "revenue":          round(total_revenue, 2),
        "profit":           round(total_profit, 2),
        "units":            total_units,
        "margin":           round(avg_margin, 1),
        "project_count":    len(projects),
        "break_even_pct":   break_even_pct,
        "machine_price":    machine_price,
        "waste_loss_count": waste_loss_count,
        "waste_loss_total": waste_loss_total,
    }


def get_financials_data(db: Session, projects: list | None = None) -> dict:
    if projects is None:
        projects = db.query(models.Project).order_by(models.Project.created_at).all()
    else:
        projects = sorted(projects, key=lambda p: p.created_at)
    machine    = get_machine_config(db)
    margin_cfg = get_margin_config(db)

    empty = {
        "project_count": 0,
        "revenue":    {"total": 0.0, "top_projects": []},
        "profit":     {"total": 0.0, "avg_per_project": 0.0, "avg_per_unit": 0.0,
                       "per_print_hour": 0.0, "top_projects": [], "bottom_projects": []},
        "margin":     {"avg": 0.0, "median": 0.0, "avg_markup": 0, "below_min": 0,
                       "target": margin_cfg.retail_target if margin_cfg else 50,
                       "minimum": margin_cfg.retail_minimum if margin_cfg else 30,
                       "best": None, "worst": None},
        "break_even": {"purchase_price": machine.purchase_price if machine else 0,
                       "setup_cost": machine.setup_cost if machine else 0,
                       "total_investment": (machine.purchase_price + machine.setup_cost) if machine else 0,
                       "recovered": 0.0, "remaining": (machine.purchase_price + machine.setup_cost) if machine else 0,
                       "recovery_pct": 0.0, "avg_profit_per_project": 0.0, "projects_remaining": None},
        "waste_loss": {"loss_projects": [], "total_loss": 0.0, "loss_project_count": 0},
        "cost_breakdown": {
            "ink":       {"value": 0.0, "pct": 0.0},
            "materials": {"value": 0.0, "pct": 0.0},
            "machine":   {"value": 0.0, "pct": 0.0},
            "labor":     {"value": 0.0, "pct": 0.0},
            "overhead":  {"value": 0.0, "pct": 0.0},
            "cogs_total": 0.0,
            "profit":    {"value": 0.0, "pct": 0.0},
        },
        "cumulative_profit": [],
    }
    if not projects:
        return empty

    n             = len(projects)
    total_revenue = sum(p.total_revenue for p in projects)
    total_profit  = sum(p.total_profit  for p in projects)
    total_units   = sum(p.units         for p in projects)
    total_cogs    = sum(p.total_cogs    for p in projects)
    total_hours   = sum(p.print_time_hours for p in projects)
    total_ink_cost = sum(p.ink_cost for p in projects)
    total_material_cost = sum(p.bom_cost for p in projects)
    total_machine_cost = sum(p.machine_cost for p in projects)
    total_labor_cost = sum(p.labor_cost for p in projects)
    total_overhead_cost = sum(p.overhead_cost for p in projects)

    avg_profit_per_project = total_profit / n
    avg_profit_per_unit    = total_profit / total_units   if total_units  > 0 else 0.0
    profit_per_print_hour  = total_profit / total_hours   if total_hours  > 0 else 0.0
    avg_markup             = (total_revenue / total_cogs - 1) * 100 if total_cogs > 0 else 0.0

    margins = sorted(p.margin_pct for p in projects)
    avg_margin    = sum(margins) / n
    median_margin = margins[n // 2] if n % 2 != 0 else (margins[n // 2 - 1] + margins[n // 2]) / 2
    below_min     = sum(1 for m in margins if m < (margin_cfg.retail_minimum if margin_cfg else 30))

    best_p  = max(projects, key=lambda p: p.margin_pct)
    worst_p = min(projects, key=lambda p: p.margin_pct)

    total_investment = (machine.purchase_price + machine.setup_cost) if machine else 0.0
    recovery_pct     = min(100.0, round(total_profit / total_investment * 100, 1)) if total_investment > 0 else 0.0
    remaining        = max(0.0, total_investment - total_profit)
    projects_remaining = round(remaining / avg_profit_per_project) if avg_profit_per_project > 0 else None

    loss_projects = [p for p in projects if p.margin_status == "Loss"]
    total_loss    = sum(abs(p.total_profit) for p in loss_projects)
    top_loss_projects = sorted(loss_projects, key=lambda p: abs(p.total_profit), reverse=True)[:20]

    cumulative: list = []
    running = 0.0
    for p in projects:
        running += p.total_profit
        cumulative.append(round(running, 2))

    return {
        "project_count": n,
        "revenue": {
            "total": round(total_revenue, 2),
            "top_projects": [
                {"name": p.name, "id": p.id, "revenue": round(p.total_revenue, 2)}
                for p in sorted(projects, key=lambda p: p.total_revenue, reverse=True)[:5]
            ],
        },
        "profit": {
            "total":             round(total_profit, 2),
            "avg_per_project":   round(avg_profit_per_project, 2),
            "avg_per_unit":      round(avg_profit_per_unit, 2),
            "per_print_hour":    round(profit_per_print_hour, 2),
            "top_projects":    [{"name": p.name, "id": p.id, "profit": round(p.total_profit, 2)}
                                 for p in sorted(projects, key=lambda p: p.total_profit, reverse=True)[:5]],
            "bottom_projects": [{"name": p.name, "id": p.id, "profit": round(p.total_profit, 2)}
                                 for p in sorted(projects, key=lambda p: p.total_profit)[:5]],
        },
        "margin": {
            "avg":       round(avg_margin, 1),
            "median":    round(median_margin, 1),
            "avg_markup": round(avg_markup, 0),
            "below_min": below_min,
            "target":    margin_cfg.retail_target  if margin_cfg else 50,
            "minimum":   margin_cfg.retail_minimum if margin_cfg else 30,
            "best":  {"name": best_p.name,  "id": best_p.id,  "margin_pct": round(best_p.margin_pct, 1),  "revenue": round(best_p.total_revenue, 2)},
            "worst": {"name": worst_p.name, "id": worst_p.id, "margin_pct": round(worst_p.margin_pct, 1), "revenue": round(worst_p.total_revenue, 2)},
        },
        "break_even": {
            "purchase_price":        round(machine.purchase_price if machine else 0, 2),
            "setup_cost":            round(machine.setup_cost     if machine else 0, 2),
            "total_investment":      round(total_investment, 2),
            "recovered":             round(total_profit, 2),
            "remaining":             round(remaining, 2),
            "recovery_pct":          recovery_pct,
            "avg_profit_per_project": round(avg_profit_per_project, 2),
            "projects_remaining":    projects_remaining,
        },
        "cost_breakdown": {
            "ink": {
                "value": round(total_ink_cost, 2),
                "pct": round((total_ink_cost / total_revenue * 100), 1) if total_revenue > 0 else 0.0,
            },
            "materials": {
                "value": round(total_material_cost, 2),
                "pct": round((total_material_cost / total_revenue * 100), 1) if total_revenue > 0 else 0.0,
            },
            "machine": {
                "value": round(total_machine_cost, 2),
                "pct": round((total_machine_cost / total_revenue * 100), 1) if total_revenue > 0 else 0.0,
            },
            "labor": {
                "value": round(total_labor_cost, 2),
                "pct": round((total_labor_cost / total_revenue * 100), 1) if total_revenue > 0 else 0.0,
            },
            "overhead": {
                "value": round(total_overhead_cost, 2),
                "pct": round((total_overhead_cost / total_revenue * 100), 1) if total_revenue > 0 else 0.0,
            },
            "cogs_total": round(total_cogs, 2),
            "profit": {
                "value": round(total_profit, 2),
                "pct": round((total_profit / total_revenue * 100), 1) if total_revenue > 0 else 0.0,
            },
        },
        "waste_loss": {
            "loss_projects": [
                {"name": p.name, "id": p.id, "profit": round(p.total_profit, 2),
                 "margin_pct": round(p.margin_pct, 1), "revenue": round(p.total_revenue, 2)}
                for p in top_loss_projects
            ],
            "loss_project_count": len(loss_projects),
            "total_loss": round(total_loss, 2),
        },
        "cumulative_profit": cumulative,
    }


def get_ink_levels(db: Session) -> dict:
    ink_cfgs = get_ink_configs(db)
    result = {}
    for ch in SERVICE_CHANNELS:
        cfg = ink_cfgs.get(ch)
        capacity = cfg.cartridge_capacity_ml if cfg else INK_CHANNEL_DEFAULT_CAPACITY.get(ch, 100.0)
        pct = ink_level_pct(ch, capacity, db)
        result[ch] = {
            "pct":          pct,
            "status":       ink_level_status(pct),
            "remaining_ml": round(capacity * pct / 100, 1),
            "capacity_ml":  capacity,
        }
    return result


# ── Service ───────────────────────────────────────────────────────────────────

def log_cartridge_replacement(db: Session, channel: str, notes: str = "") -> models.CartridgeReplacement:
    rep = models.CartridgeReplacement(channel=channel, notes=notes or None)
    db.add(rep)
    db.commit()
    _invalidate_dashboard_analytics_cache()
    return rep


def get_cartridge_replacements(db: Session) -> list:
    return (
        db.query(models.CartridgeReplacement)
        .order_by(models.CartridgeReplacement.replaced_at.desc())
        .all()
    )


def get_cartridge_replacement_counts(db: Session) -> dict[str, int]:
    """Return a {channel: count} dict for all cartridge replacement events."""
    from sqlalchemy import func
    rows = (
        db.query(models.CartridgeReplacement.channel, func.count().label("cnt"))
        .group_by(models.CartridgeReplacement.channel)
        .all()
    )
    return {ch: cnt for ch, cnt in rows}


def create_cartridge_inventory_lot(
    db: Session,
    *,
    channel: str,
    quantity_ml: float,
    serial_number: str | None = None,
    expires_on: str | None = None,
    box_expires_on: str | None = None,
    notes: str = "",
    is_in_use: bool = False,
) -> models.CartridgeInventoryLot:
    lot = models.CartridgeInventoryLot(
        channel=(channel or "").strip().upper(),
        quantity_ml=max(float(quantity_ml or 0.0), 0.0),
        serial_number=(serial_number or "").strip() or None,
        expires_on=(expires_on or "").strip() or None,
        box_expires_on=(box_expires_on or "").strip() or None,
        notes=(notes or "").strip() or None,
        is_in_use=bool(is_in_use),
        installed_at=datetime.utcnow() if is_in_use else None,
    )
    db.add(lot)
    db.flush()
    if lot.is_in_use:
        _set_other_lots_not_in_use(db, lot.channel, excluded_lot=lot)
    db.commit()
    db.refresh(lot)
    return lot


def set_cartridge_lot_in_use(db: Session, lot_id: int, is_in_use: bool) -> models.CartridgeInventoryLot | None:
    lot = db.query(models.CartridgeInventoryLot).filter_by(id=lot_id).first()
    if not lot:
        return None
    lot.is_in_use = bool(is_in_use)
    lot.installed_at = datetime.utcnow() if lot.is_in_use else None
    if lot.is_in_use:
        _set_other_lots_not_in_use(db, lot.channel, excluded_lot=lot)
    db.commit()
    db.refresh(lot)
    return lot


def update_cartridge_lot_quantity(db: Session, lot_id: int, quantity_ml: float) -> models.CartridgeInventoryLot | None:
    lot = db.query(models.CartridgeInventoryLot).filter_by(id=lot_id).first()
    if not lot:
        return None
    lot.quantity_ml = max(float(quantity_ml or 0.0), 0.0)
    db.commit()
    db.refresh(lot)
    return lot


def update_cartridge_lot(
    db: Session,
    lot_id: int,
    *,
    channel: str | None = None,
    serial_number: str | None = None,
    expires_on: str | None = None,
    box_expires_on: str | None = None,
    notes: str | None = None,
) -> models.CartridgeInventoryLot | None:
    """Edit the descriptive fields of an existing cartridge lot.

    Pass ``None`` to leave a field unchanged. Pass an empty string to clear
    nullable string fields (serial_number, expires_on, box_expires_on, notes).
    """
    lot = db.query(models.CartridgeInventoryLot).filter_by(id=lot_id).first()
    if not lot:
        return None
    channel_changed = False
    if channel is not None:
        new_channel = (channel or "").strip().upper()
        if new_channel and new_channel != lot.channel:
            lot.channel = new_channel
            channel_changed = True
    if serial_number is not None:
        lot.serial_number = (serial_number or "").strip() or None
    if expires_on is not None:
        lot.expires_on = (expires_on or "").strip() or None
    if box_expires_on is not None:
        lot.box_expires_on = (box_expires_on or "").strip() or None
    if notes is not None:
        lot.notes = (notes or "").strip() or None
    db.flush()
    # If channel changed while this lot is in use, re-assert single-in-use on
    # the new channel so we never end up with two in-use lots in one slot.
    if channel_changed and lot.is_in_use:
        _set_other_lots_not_in_use(db, lot.channel, excluded_lot=lot)
    db.commit()
    db.refresh(lot)
    return lot


def delete_cartridge_lot(db: Session, lot_id: int) -> None:
    lot = db.query(models.CartridgeInventoryLot).filter_by(id=lot_id).first()
    if lot:
        db.delete(lot)
        db.commit()


def get_cartridge_inventory_lots(db: Session) -> list:
    return (
        db.query(models.CartridgeInventoryLot)
        .order_by(models.CartridgeInventoryLot.channel.asc(), models.CartridgeInventoryLot.created_at.desc())
        .all()
    )


def get_inventory_report_data(db: Session) -> dict:
    lots = get_cartridge_inventory_lots(db)
    materials = get_material_inventory_balance(db)
    movements = get_material_inventory_movements(db, limit=100)
    return {
        "generated_at": datetime.utcnow(),
        "cartridge_lots": lots,
        "materials": materials,
        "movements": movements,
    }


def _set_other_lots_not_in_use(db: Session, channel: str, excluded_lot: models.CartridgeInventoryLot) -> None:
    (
        db.query(models.CartridgeInventoryLot)
        .filter(models.CartridgeInventoryLot.channel == channel)
        .filter(models.CartridgeInventoryLot.id != excluded_lot.id)
        .update({"is_in_use": False, "installed_at": None})
    )


def _sync_project_substrate_inventory(
    db: Session,
    *,
    project: models.Project,
    old_substrate: str,
    old_units: int,
    notes: str,
) -> None:
    new_substrate = (project.substrate or "").strip()
    new_units = int(project.units or 0)
    delta_map: dict[int, float] = {}

    old_item = get_material_item_by_name(db, old_substrate)
    if old_item and old_units > 0:
        delta_map[old_item.id] = delta_map.get(old_item.id, 0.0) - float(old_units)

    new_item = get_material_item_by_name(db, new_substrate)
    if new_item and new_units > 0:
        delta_map[new_item.id] = delta_map.get(new_item.id, 0.0) + float(new_units)

    for item_id, delta in delta_map.items():
        if delta > 0:
            create_material_inventory_movement(
                db,
                material_item_id=item_id,
                movement_type="out",
                quantity=abs(delta),
                project_id=project.id,
                notes=notes,
            )
        elif delta < 0:
            create_material_inventory_movement(
                db,
                material_item_id=item_id,
                movement_type="in",
                quantity=abs(delta),
                project_id=project.id,
                notes=f"Inventory rollback from project change #{project.id}: {project.name}",
            )


# ── Maintenance Presets ───────────────────────────────────────────────────────

DEFAULT_PRESETS = [
    # Quick Actions
    {
        "name": "Ink Injection", "kind": models.PRESET_KIND_QUICK,
        "icon": "syringe", "color": "indigo", "is_system": True, "tracks_ink": True,
        "sort_order": 10,
        "volumes_json": json.dumps({"C":1.5,"M":1.5,"Y":1.5,"K":1.5,"W":1.5,"GL":1.5,"FW":1.5,"CLN":1.5}),
    },
    {
        "name": "Flash Clean", "kind": models.PRESET_KIND_QUICK,
        "icon": "bolt", "color": "amber", "is_system": True, "tracks_ink": True,
        "sort_order": 20,
        "volumes_json": json.dumps({c: 0.0002 for c in ["C","M","Y","K","W","GL","FW"]}),
    },
    {
        "name": "Automatic Flash Clean", "kind": models.PRESET_KIND_QUICK,
        "icon": "bolt", "color": "amber", "is_system": True, "tracks_ink": True,
        "sort_order": 25,
        "volumes_json": json.dumps({c: 0.0002 for c in ["C","M","Y","K","W","GL","FW"]}),
    },
    {
        "name": "Medium Clean", "kind": models.PRESET_KIND_QUICK,
        "icon": "spray", "color": "amber", "is_system": True, "tracks_ink": True,
        "sort_order": 30,
        "volumes_json": json.dumps({c: 0.2 for c in ["C","M","Y","K","W","GL","FW"]}),
    },
    {
        "name": "Deep Clean", "kind": models.PRESET_KIND_QUICK,
        "icon": "droplet", "color": "orange", "is_system": True, "tracks_ink": True,
        "sort_order": 40,
        "volumes_json": json.dumps({"C":1.5,"M":1.5,"Y":1.5,"K":1.5,"W":1.5,"GL":1.5,"FW":1.5,"CLN":1.83}),
    },
    {
        "name": "Automatic Deep Clean", "kind": models.PRESET_KIND_QUICK,
        "icon": "droplet", "color": "orange", "is_system": True, "tracks_ink": True,
        "sort_order": 45,
        "volumes_json": json.dumps({"CLN": 1.5}),
    },
    # Hardware Events
    {
        "name": "Initial Startup", "kind": models.PRESET_KIND_HARDWARE,
        "icon": "bolt", "color": "emerald", "is_system": True, "tracks_ink": True,
        "sort_order": 110,
        "volumes_json": json.dumps({"C":15,"M":15,"Y":15,"K":15,"W":15,"GL":15,"FW":0,"CLN":0}),
    },
    {
        "name": "Print Head Replacement", "kind": models.PRESET_KIND_HARDWARE,
        "icon": "wrench", "color": "rose", "is_system": True, "tracks_ink": True,
        "sort_order": 120,
        "volumes_json": json.dumps({"C":15,"M":15,"Y":15,"K":15,"W":15,"GL":15,"FW":0,"CLN":0}),
    },
    {
        "name": "Extended Shutdown Restart", "kind": models.PRESET_KIND_HARDWARE,
        "icon": "power", "color": "violet", "is_system": True, "tracks_ink": True,
        "sort_order": 130,
        "volumes_json": json.dumps({"C":15,"M":15,"Y":15,"K":15,"W":15,"GL":15,"FW":0,"CLN":0}),
    },
    {
        "name": "Cleaning Cartridge Replacement", "kind": models.PRESET_KIND_HARDWARE,
        "icon": "droplet", "color": "teal", "is_system": True, "tracks_ink": False,
        "sort_order": 140,
        "volumes_json": "{}",
    },
    # Moisturizing Liquid
    {
        "name": "Automatic Moisturizing", "kind": models.PRESET_KIND_QUICK,
        "icon": "droplet", "color": "emerald", "is_system": True, "tracks_ink": True,
        "sort_order": 50,
        "volumes_json": json.dumps({"CLN": 1.83, "ML": 1.33}),
    },
    {
        "name": "Safe Shutdown Moisturizing", "kind": models.PRESET_KIND_QUICK,
        "icon": "power", "color": "emerald", "is_system": True, "tracks_ink": True,
        "sort_order": 60,
        "volumes_json": json.dumps({"CLN": 1.83, "ML": 1.33}),
    },
]


def seed_default_presets(db: Session) -> None:
    """Seed missing system presets (idempotent by preset name)."""
    existing_names = {name for (name,) in db.query(models.MaintenancePreset.name).all()}
    added = False
    for spec in DEFAULT_PRESETS:
        if spec["name"] in existing_names:
            continue
        db.add(models.MaintenancePreset(**spec))
        added = True
    if added:
        db.commit()


def reset_default_presets(db: Session) -> None:
    """Delete all system presets and re-seed defaults. Custom presets are preserved."""
    db.query(models.MaintenancePreset).filter(
        models.MaintenancePreset.is_system == True  # noqa: E712
    ).delete(synchronize_session=False)
    db.commit()
    for spec in DEFAULT_PRESETS:
        db.add(models.MaintenancePreset(**spec))
    db.commit()
    _invalidate_dashboard_analytics_cache()


def get_presets(db: Session, kind: str | None = None) -> list:
    q = db.query(models.MaintenancePreset).filter(models.MaintenancePreset.is_active == True)  # noqa: E712
    if kind:
        q = q.filter(models.MaintenancePreset.kind == kind)
    return q.order_by(models.MaintenancePreset.sort_order.asc(), models.MaintenancePreset.id.asc()).all()


def get_preset(db: Session, preset_id: int) -> models.MaintenancePreset | None:
    return db.query(models.MaintenancePreset).filter_by(id=preset_id).first()


def create_preset(
    db: Session, name: str, kind: str, volumes: dict, color: str = "indigo",
    icon: str = "droplet", tracks_ink: bool = True,
) -> models.MaintenancePreset:
    sort_max = db.query(models.MaintenancePreset).order_by(
        models.MaintenancePreset.sort_order.desc()
    ).first()
    sort_order = (sort_max.sort_order + 10) if sort_max else 10
    preset = models.MaintenancePreset(
        name=name.strip(), kind=kind, color=color, icon=icon,
        is_system=False, is_active=True, tracks_ink=tracks_ink,
        sort_order=sort_order,
        volumes_json=json.dumps({k: float(v) for k, v in volumes.items() if v is not None}),
    )
    db.add(preset)
    db.commit()
    return preset


def update_preset(db: Session, preset_id: int, *, name: str | None = None, volumes: dict | None = None) -> None:
    preset = get_preset(db, preset_id)
    if not preset:
        return
    if name is not None and name.strip():
        preset.name = name.strip()
    if volumes is not None:
        preset.volumes_json = json.dumps({k: float(v) for k, v in volumes.items() if v is not None})
    db.commit()


def delete_preset(db: Session, preset_id: int) -> bool:
    preset = get_preset(db, preset_id)
    if not preset or preset.is_system:
        return False
    db.delete(preset)
    db.commit()
    return True


# ── Service Actions (log of executed presets / hardware events) ───────────────

def log_service_action(
    db: Session, preset_id: int | None, kind: str, name: str,
    volumes: dict, notes: str = "", occurred_at: datetime | None = None,
) -> models.ServiceAction:
    vols = {k: float(v) for k, v in (volumes or {}).items() if v is not None}
    total = round(sum(vols.values()), 4)
    action = models.ServiceAction(
        preset_id=preset_id, kind=kind, name_snapshot=name,
        volumes_json=json.dumps(vols),
        total_ml=total,
        notes=notes or None,
    )
    if occurred_at is not None:
        action.occurred_at = occurred_at
    db.add(action)
    db.commit()
    _invalidate_dashboard_analytics_cache()
    return action


def get_service_actions(db: Session, limit: int = 100) -> list:
    return (
        db.query(models.ServiceAction)
        .order_by(models.ServiceAction.occurred_at.desc())
        .limit(limit)
        .all()
    )


def get_latest_auto_maintenance_sync(db: Session) -> dict | None:
    row = (
        db.query(models.ServiceAction)
        .filter(models.ServiceAction.notes.contains("[AUTO_SCHED "))
        .order_by(models.ServiceAction.occurred_at.desc())
        .first()
    )
    if not row:
        return None

    trigger = "unknown"
    notes = row.notes or ""
    if "trigger=" in notes:
        trigger = notes.split("trigger=", 1)[1].strip().split("|", 1)[0].strip()

    trigger_labels = {
        "idle>1d": "Idle for over 1 day",
        "no_deep_or_moist>=3d": "No deep/moisturizing run in 3+ days",
        "unknown": "Rule not detected",
    }

    return {
        "occurred_at": row.occurred_at,
        "name": row.name_snapshot,
        "trigger": trigger,
        "trigger_label": trigger_labels.get(trigger, trigger),
    }


def delete_service_action(db: Session, action_id: int) -> None:
    row = db.query(models.ServiceAction).filter_by(id=action_id).first()
    if row:
        db.delete(row)
        db.commit()
        _invalidate_dashboard_analytics_cache()


# ── Analytics ─────────────────────────────────────────────────────────────────

def get_analytics_data(db: Session, projects: list | None = None) -> dict:
    if projects is None:
        projects = db.query(models.Project).order_by(models.Project.created_at).all()
    else:
        projects = sorted(projects, key=lambda p: p.created_at)

    monthly: dict = defaultdict(lambda: {"revenue": 0.0, "profit": 0.0, "cogs": 0.0, "count": 0})
    for p in projects:
        key = p.created_at.strftime("%Y-%m")
        monthly[key]["revenue"] += p.total_revenue
        monthly[key]["profit"]  += p.total_profit
        monthly[key]["cogs"]    += p.total_cogs
        monthly[key]["count"]   += 1

    margin_dist = {"Strong": 0, "Target": 0, "Minimum": 0, "Loss": 0}
    for p in projects:
        margin_dist[p.margin_status] = margin_dist.get(p.margin_status, 0) + 1

    ink_monthly: dict = defaultdict(lambda: defaultdict(float))
    for usage in (
        db.query(models.ProjectInkUsage)
        .join(models.Project, models.ProjectInkUsage.project_id == models.Project.id)
        .all()
    ):
        key = usage.project.created_at.strftime("%Y-%m")
        ink_monthly[key][usage.channel] += usage.ml_used

    ink_levels = get_ink_levels(db)

    return {
        "monthly":      {k: dict(v) for k, v in sorted(monthly.items())},
        "margin_dist":  margin_dist,
        "ink_monthly":  {k: dict(v) for k, v in sorted(ink_monthly.items())},
        "ink_levels":   ink_levels,
        "project_count":len(projects),
    }
