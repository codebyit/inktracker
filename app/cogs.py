# Usage: imported by crud.py — COGS calculation engine
# Schema: see AGENTS.md — Data Schema and InkTracker section

import json

from sqlalchemy.orm import Session
from . import models


def machine_cost_per_hour(cfg: models.MachineConfig) -> float:
    """Depreciation + electricity + maintenance cost per operating hour."""
    if not cfg or cfg.lifespan_hours <= 0:
        return 0.0
    total_investment = cfg.purchase_price + (cfg.setup_cost or 0.0)
    depreciation = total_investment / cfg.lifespan_hours
    electricity  = (cfg.power_watts / 1000.0) * cfg.electricity_rate
    annual_hours = cfg.annual_hours if cfg.annual_hours > 0 else 1.0
    maintenance  = cfg.annual_maintenance / annual_hours
    return depreciation + electricity + maintenance


def machine_cost_breakdown(cfg: models.MachineConfig) -> dict:
    """Returns per-bucket cost/hr for display in Machine settings."""
    if not cfg or cfg.lifespan_hours <= 0:
        return {"depreciation": 0.0, "electricity": 0.0, "maintenance": 0.0, "total": 0.0}
    total_investment = cfg.purchase_price + (cfg.setup_cost or 0.0)
    depreciation = total_investment / cfg.lifespan_hours
    electricity  = (cfg.power_watts / 1000.0) * cfg.electricity_rate
    annual_hours = cfg.annual_hours if cfg.annual_hours > 0 else 1.0
    maintenance  = cfg.annual_maintenance / annual_hours
    total = depreciation + electricity + maintenance
    return {
        "depreciation": round(depreciation, 4),
        "electricity":  round(electricity, 4),
        "maintenance":  round(maintenance, 4),
        "total":        round(total, 4),
    }


def calculate_cogs(
    ink_usage: dict,        # {channel: ml_used} — total for the batch
    bom_total: float,       # total BOM cost for the batch
    machine_cfg: models.MachineConfig,
    ink_cfgs: dict,         # {channel: InkChannelConfig}
    labor_cfg: models.LaborConfig,
    print_time_hours: float,
    hands_on_hours: float,
    units: int,
) -> dict:
    # Ink cost (batch)
    ink_cost = 0.0
    for channel, ml in ink_usage.items():
        cfg = ink_cfgs.get(channel)
        if cfg and cfg.cartridge_capacity_ml > 0:
            ink_cost += float(ml) * (cfg.price_per_cartridge / cfg.cartridge_capacity_ml)

    # Machine cost (batch)
    cost_per_hr = machine_cost_per_hour(machine_cfg)
    machine_cost = cost_per_hr * float(print_time_hours)

    # Labor cost (batch)
    labor_cost = labor_cfg.hourly_rate * float(hands_on_hours)

    # Direct cost
    direct_cost = ink_cost + float(bom_total) + machine_cost + labor_cost

    # Overhead applied to direct cost
    overhead_cost = direct_cost * (labor_cfg.overhead_pct / 100.0)

    total_cogs = direct_cost + overhead_cost
    cogs_per_unit = total_cogs / units if units > 0 else 0.0

    return {
        "ink_cost":      round(ink_cost, 4),
        "bom_cost":      round(float(bom_total), 4),
        "machine_cost":  round(machine_cost, 4),
        "labor_cost":    round(labor_cost, 4),
        "overhead_cost": round(overhead_cost, 4),
        "total_cogs":    round(total_cogs, 4),
        "cogs_per_unit": round(cogs_per_unit, 4),
    }


def margin_status(margin_pct: float, margin_cfg: models.MarginConfig) -> str:
    if margin_pct >= margin_cfg.strong_threshold:
        return "Strong"
    if margin_pct >= margin_cfg.target_threshold:
        return "Target"
    if margin_pct >= 0:
        return "Minimum"
    return "Loss"


def ink_level_pct(channel: str, capacity_ml: float, db: Session) -> float:
    """Remaining ink % based on usage since last cartridge replacement.

    Includes both project ink usage and service-action ink usage
    (quick-action presets and hardware events).
    """
    if capacity_ml <= 0:
        return 0.0

    last_rep = (
        db.query(models.CartridgeReplacement)
        .filter(models.CartridgeReplacement.channel == channel)
        .order_by(models.CartridgeReplacement.replaced_at.desc())
        .first()
    )

    # Project ink usage since last replacement
    proj_q = (
        db.query(models.ProjectInkUsage)
        .join(models.Project, models.ProjectInkUsage.project_id == models.Project.id)
        .filter(models.ProjectInkUsage.channel == channel)
    )
    if last_rep:
        proj_q = proj_q.filter(models.Project.created_at >= last_rep.replaced_at)
    project_used = sum(u.ml_used for u in proj_q.all())

    # Service action ink usage since last replacement
    svc_q = db.query(models.ServiceAction)
    if last_rep:
        svc_q = svc_q.filter(models.ServiceAction.occurred_at >= last_rep.replaced_at)
    service_used = 0.0
    for action in svc_q.all():
        try:
            vols = json.loads(action.volumes_json or "{}")
            service_used += float(vols.get(channel, 0.0) or 0.0)
        except (ValueError, TypeError):
            continue

    total_used = project_used + service_used
    remaining = max(0.0, capacity_ml - total_used)
    return round(remaining / capacity_ml * 100, 1)


def ink_level_status(pct: float) -> str:
    if pct >= 60:
        return "good"
    if pct >= 20:
        return "caution"
    return "low"
