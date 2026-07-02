"""First-time setup wizard.

A guided onboarding flow (Currency -> Printer -> Machine -> Ink -> optional
Labor & Margins) that pre-fills the current defaults and lets a new user confirm
or adjust them. Works identically on the Docker/self-hosted web app and the
Windows desktop build (same ``app.main:app``).

The wizard reuses the existing settings CRUD functions; it does not introduce a
parallel persistence path. Completion (or dismissal) is recorded on
``feature_config.setup_completed`` so the dashboard prompt only appears until the
user has onboarded once.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud
from ..models import INK_CHANNELS
from ..printer_presets import (
    CURRENCIES,
    DEFAULT_CURRENCY_CODE,
    DEFAULT_PRESET,
    get_preset,
    presets_json,
    symbol_for,
    code_for,
    default_ink_price,
)
from ..templates_config import templates
from ..cache import invalidate_dashboard_analytics_cache

router = APIRouter()

# Color ink channels the single wizard price applies to (all inks + Gloss).
# CLN/ML are consumables handled separately and left at their seeded price (0).
_WIZARD_PRICED_CHANNELS = [ch for ch in INK_CHANNELS]  # C,M,Y,K,W,GL,FW


def _f(form, key, default=0.0):
    try:
        return float(form.get(key, default))
    except (TypeError, ValueError):
        return float(default)


@router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request, db: Session = Depends(get_db)):
    ink_global = crud.get_ink_global_config(db)
    machine    = crud.get_machine_config(db)
    labor      = crud.get_labor_config(db)
    margins    = crud.get_margin_config(db)

    # Fall back to the default printer preset for any config not yet seeded
    # (the app seeds at startup, but stay resilient on a partially-seeded DB).
    preset = get_preset(DEFAULT_PRESET)
    pm, pi = preset["machine"], preset["ink"]

    current_symbol = ink_global.currency if ink_global else symbol_for(DEFAULT_CURRENCY_CODE)
    current_code   = code_for(current_symbol)

    context_json = {
        "currencies":       CURRENCIES,
        "presets":          presets_json(),
        "default_preset":   DEFAULT_PRESET,
        "current_currency": current_code,
        "machine": {
            "purchase_price":     machine.purchase_price if machine else pm["purchase_price"],
            "setup_cost":         machine.setup_cost if machine else pm["setup_cost"],
            "lifespan_hours":     machine.lifespan_hours if machine else pm["lifespan_hours"],
            "annual_hours":       machine.annual_hours if machine else pm["annual_hours"],
            "power_watts":        machine.power_watts if machine else pm["power_watts"],
            "electricity_rate":   machine.electricity_rate if machine else pm["electricity_rate"],
            "annual_maintenance": machine.annual_maintenance if machine else pm["annual_maintenance"],
        },
        "ink": {
            "cartridge_capacity_ml": ink_global.cartridge_capacity_ml if ink_global else pi["cartridge_capacity_ml"],
            "cartridge_tare_g":      ink_global.cartridge_tare_g if ink_global else pi["cartridge_tare_g"],
            "white_loaded":          ink_global.white_loaded if ink_global else pi["white_loaded"],
        },
        "labor": {
            "hourly_rate":  labor.hourly_rate if labor else 15.0,
            "overhead_pct": labor.overhead_pct if labor else 25.0,
        },
        "margins": {
            "retail_minimum": margins.retail_minimum if margins else 30.0,
            "retail_target":  margins.retail_target if margins else 50.0,
            "retail_strong":  margins.retail_strong if margins else 65.0,
        },
    }
    return templates.TemplateResponse(request, "setup.html", {
        "setup_json": json.dumps(context_json),
        "app_active": None,
    })


@router.post("/setup")
async def setup_save(request: Request, db: Session = Depends(get_db)):
    form = await request.form()

    # Currency (stored as symbol).
    currency_code   = str(form.get("currency_code", DEFAULT_CURRENCY_CODE)).upper()
    currency_symbol = symbol_for(currency_code)

    # Machine.
    crud.update_machine_config(
        db,
        purchase_price=_f(form, "purchase_price", 2500.0),
        setup_cost=_f(form, "setup_cost", 0.0),
        lifespan_hours=_f(form, "lifespan_hours", 10000.0),
        annual_hours=_f(form, "annual_hours", 500.0),
        power_watts=_f(form, "power_watts", 250.0),
        electricity_rate=_f(form, "electricity_rate", 0.13),
        annual_maintenance=_f(form, "annual_maintenance", 499.0),
    )

    # Ink globals (capacity, tare, white choice) + currency.
    crud.update_ink_global_config(
        db,
        cartridge_capacity_ml=_f(form, "cartridge_capacity_ml", 100.0),
        white_loaded=str(form.get("white_loaded", "W")),
        low_ink_pct=float(crud.get_ink_global_config(db).low_ink_pct or 20.0),
        currency=currency_symbol,
        cartridge_tare_g=_f(form, "cartridge_tare_g", 75.0),
    )

    # Single price-per-cartridge applied to all color inks + Gloss.
    price = _f(form, "price_per_cartridge", default_ink_price(DEFAULT_PRESET, currency_code))
    for ch in _WIZARD_PRICED_CHANNELS:
        existing = crud.get_ink_configs(db).get(ch)
        preprime = existing.preprime_ml if existing else 0.0
        density  = existing.ink_density_g_per_ml if existing else 1.0
        crud.update_ink_config(db, channel=ch, price=price, preprime_ml=preprime,
                               density_g_per_ml=density)

    # Optional Labor & Margins (only when the user filled that step in).
    if str(form.get("configure_labor", "")).strip().lower() in {"1", "true", "on", "yes"}:
        crud.update_labor_config(
            db,
            hourly_rate=_f(form, "hourly_rate", 15.0),
            overhead_pct=_f(form, "overhead_pct", 25.0),
        )
        m = crud.get_margin_config(db)
        crud.update_margin_config(
            db,
            retail_minimum=_f(form, "retail_minimum", m.retail_minimum),
            retail_target=_f(form, "retail_target", m.retail_target),
            retail_strong=_f(form, "retail_strong", m.retail_strong),
            wholesale_minimum=m.wholesale_minimum,
            wholesale_target=m.wholesale_target,
            wholesale_strong=m.wholesale_strong,
        )

    crud.mark_setup_completed(db)
    templates.env.globals["currency"] = currency_symbol
    invalidate_dashboard_analytics_cache()
    return RedirectResponse("/?welcome=1", status_code=303)


@router.post("/setup/dismiss")
def setup_dismiss(db: Session = Depends(get_db)):
    """Acknowledge the defaults and stop prompting (banner X / Skip)."""
    crud.mark_setup_completed(db)
    return RedirectResponse("/", status_code=303)
