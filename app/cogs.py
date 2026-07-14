# Usage: imported by crud.py — COGS calculation engine
# Schema: see project docs — Data Schema and InkTrack section

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


def _ink_cost_for_usage(ink_usage: dict, ink_cfgs: dict) -> float:
    """Ink cost for a {channel: ml} usage map using per-channel cartridge pricing.

    Shared by calculate_cogs (project total) and craft_variant_breakdown
    (per-variant) so both always use the identical pricing formula. For a
    single-craft project the variant ink_cost therefore equals the project total.
    """
    cost = 0.0
    for channel, ml in (ink_usage or {}).items():
        cfg = ink_cfgs.get(channel)
        if cfg and cfg.cartridge_capacity_ml > 0:
            cost += float(ml) * (cfg.price_per_cartridge / cfg.cartridge_capacity_ml)
    return cost


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
    ink_cost = _ink_cost_for_usage(ink_usage, ink_cfgs)

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


def craft_variant_breakdown(crafts, ink_cfgs: dict) -> list:
    """Per-variant cost breakdown for display (project detail view).

    ``crafts`` is a list of schemas.CraftVariant. Each variant's ink_cost uses
    _ink_cost_for_usage, the same formula as the project total, so the sum of
    variant ink costs equals the project ink_cost (regression invariant).
    """
    rows = []
    for c in crafts:
        usage = getattr(c, "ink_usage", {}) or {}
        rows.append({
            "variant_name":     getattr(c, "variant_name", "Primary"),
            "craft_mode":       getattr(c, "craft_mode", "Flat"),
            "craft_ink_mode":   getattr(c, "craft_ink_mode", ""),
            "ink_mode":         getattr(c, "ink_mode", "CMYK"),
            "ink_ml":           round(sum(float(v) for v in usage.values()), 2),
            "ink_cost":         round(_ink_cost_for_usage(usage, ink_cfgs), 4),
            "print_time_hours": round(float(getattr(c, "print_time_hours", 0.0) or 0.0), 4),
        })
    return rows


def margin_status(margin_pct: float, margin_cfg: models.MarginConfig) -> str:
    if margin_pct >= margin_cfg.strong_threshold:
        return "Strong"
    if margin_pct >= margin_cfg.target_threshold:
        return "Target"
    if margin_pct >= 0:
        return "Minimum"
    return "Loss"


def ink_channel_used_ml(channel: str, db: Session) -> float:
    """Total ml consumed for a channel since the last cartridge replacement.

    Sums project ink usage and service-action ink usage (quick-action presets,
    hardware events, and ink corrections). This value is *uncapped*: it can exceed
    the cartridge capacity (over-consumed) or go negative (net negative corrections),
    which is exactly what the absolute "set current level" correction needs so it can
    compute the right adjustment without the display floor hiding the true total.
    """
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

    return project_used + service_used


def ink_level_pct(channel: str, capacity_ml: float, db: Session) -> float:
    """Remaining ink % based on usage since last cartridge replacement.

    Includes both project ink usage and service-action ink usage
    (quick-action presets and hardware events). The result is clamped to
    0–100%: the lower clamp floors an over-consumed channel at 0%, and the
    upper clamp prevents a net-negative correction from reporting >100%.
    """
    if capacity_ml <= 0:
        return 0.0

    total_used = ink_channel_used_ml(channel, db)
    remaining = min(capacity_ml, max(0.0, capacity_ml - total_used))
    return round(remaining / capacity_ml * 100, 1)


def ink_level_status(pct: float) -> str:
    if pct >= 60:
        return "good"
    if pct >= 20:
        return "caution"
    return "low"
