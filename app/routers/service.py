import json
import math
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..cache import invalidate_dashboard_analytics_cache
from .. import crud, models, cogs
from ..models import (
    INK_CHANNELS, SERVICE_CHANNELS, INK_CHANNEL_NAMES,
    INK_CHANNEL_DEFAULT_CAPACITY,
    PRESET_KIND_QUICK, PRESET_KIND_HARDWARE, PRESET_KINDS,
)
from ..templates_config import templates

router = APIRouter()


# ── Helpers ─────────────────────────────────────────────────────

def _parse_volumes_from_form(form_data: dict) -> dict:
    """Pulls ml_<CHANNEL> form fields into a {channel: ml} dict, omitting blanks."""
    volumes: dict[str, float] = {}
    for ch in SERVICE_CHANNELS:
        raw = form_data.get(f"ml_{ch}")
        if raw is None or raw == "":
            continue
        try:
            volumes[ch] = float(raw)
        except (TypeError, ValueError):
            continue
    return volumes


def _preset_volume_map(presets: list) -> dict:
    out: dict[int, dict] = {}
    for p in presets:
        try:
            out[p.id] = json.loads(p.volumes_json or "{}")
        except (ValueError, TypeError):
            out[p.id] = {}
    return out

def _parse_occurred_at(raw: str | None) -> datetime | None:
    """Parse an HTML datetime-local string ('YYYY-MM-DDTHH:MM') into a naive datetime."""
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _parse_ink_correction_targets(form_data: dict) -> dict[str, float]:
    """Parses the absolute target remaining-ml for each printable channel the user filled in.

    Only channels with a value present (non-blank) are returned; a value of 0 is a valid
    target ("set to empty"), so unlike a delta, zero is kept. The handler converts each
    absolute target into the consumption delta that makes the derived level equal it.
    """
    out: dict[str, float] = {}
    for ch in INK_CHANNELS:
        raw = form_data.get(f"corr_{ch}")
        if raw is None or str(raw).strip() == "":
            continue
        try:
            out[ch] = float(raw)
        except (TypeError, ValueError):
            continue
    return out

def _finite(value, default: float = 0.0) -> float:
    """Coerce to a finite float, mapping None/NaN/Infinity to a safe default."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def _service_actions_json(actions) -> str:
    """Build the Service Action Log payload as a guaranteed-valid JSON string.

    Rendering the rows inline with Jinja raw-injected total_ml/volumes_json, so a
    single legacy row with a non-finite float (Infinity/NaN, which json.dumps emits
    verbatim) broke JSON.parse for the WHOLE array and hid every entry client-side.
    Sanitising here (coerce non-finite -> 0, re-serialise per-channel volumes) keeps
    one bad row from taking down the entire log.
    """
    rows = []
    for a in actions:
        try:
            raw_vols = json.loads(a.volumes_json or "{}")
            if not isinstance(raw_vols, dict):
                raw_vols = {}
        except (ValueError, TypeError):
            raw_vols = {}
        vols = {str(k): _finite(v) for k, v in raw_vols.items()}
        rows.append({
            "id": a.id,
            "name": a.name_snapshot,
            "date": a.occurred_at.strftime("%Y-%m-%d"),
            "display": a.occurred_at.strftime("%d %b %Y %H:%M"),
            "ml": _finite(a.total_ml),
            "notes": a.notes or "",
            "vols": vols,
            "corr": a.name_snapshot == "Ink Correction",
        })
    # allow_nan=False is a belt-and-suspenders guard; values are already finite.
    payload = json.dumps(rows, allow_nan=False)
    # Escape characters that could terminate the <script> tag or be mis-parsed as
    # HTML when the payload is embedded inline (matches Jinja's |tojson behaviour).
    return (
        payload.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


# ── Page ─────────────────────────────────────────────────────────

@router.get("/service", response_class=HTMLResponse)
def service_page(request: Request, db: Session = Depends(get_db)):
    quick_presets    = crud.get_presets(db, kind=PRESET_KIND_QUICK)
    hardware_presets = crud.get_presets(db, kind=PRESET_KIND_HARDWARE)
    replacements     = crud.get_cartridge_replacements(db)
    replacement_counts = crud.get_cartridge_replacement_counts(db)
    # Load a wider window so archived (older) entries can be revealed via the
    # "Show archived" filter without a round-trip.
    actions          = crud.get_service_actions(db, limit=500)
    ink_levels       = crud.get_ink_levels(db)
    auto_sync_status = crud.get_latest_auto_maintenance_sync(db)
    auto_cfg         = crud.get_automation_config(db)
    ink_cfgs         = crud.get_ink_configs(db)
    ink_global       = crud.get_ink_global_config(db)
    cartridge_tare_g = float(ink_global.cartridge_tare_g) if ink_global and ink_global.cartridge_tare_g is not None else 75.0
    cartridge_capacity_ml = float(ink_global.cartridge_capacity_ml) if ink_global and ink_global.cartridge_capacity_ml else 100.0
    white_loaded = (ink_global.white_loaded if ink_global and ink_global.white_loaded else "W")
    archive_days = int(getattr(auto_cfg, "service_log_archive_days", 60) or 60) if auto_cfg else 60
    from datetime import timedelta as _timedelta
    archive_before_iso = (datetime.now() - _timedelta(days=archive_days)).strftime("%Y-%m-%d")
    ink_density_by_channel = {
        ch: float(cfg.ink_density_g_per_ml) if cfg.ink_density_g_per_ml else 1.0
        for ch, cfg in ink_cfgs.items()
    }
    correction_error = (request.query_params.get("corr_error") or "").strip()
    correction_saved = (request.query_params.get("corr_saved") or "") == "1"
    correction_nochange = (request.query_params.get("corr_nochange") or "") == "1"
    correction_undo_action_id = None
    if correction_saved:
        undo_raw = request.query_params.get("corr_undo")
        try:
            correction_undo_action_id = int(undo_raw) if undo_raw else None
        except (TypeError, ValueError):
            correction_undo_action_id = None

    next_auto_run = None
    if auto_cfg and auto_cfg.auto_maintenance_log_enabled:
        try:
            hh, mm = str(auto_cfg.auto_maintenance_log_time or "03:00").split(":", 1)
            now = datetime.now()
            candidate = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            if candidate <= now:
                from datetime import timedelta
                candidate = candidate + timedelta(days=1)
            next_auto_run = candidate
        except Exception:
            next_auto_run = None

    return templates.TemplateResponse(request, "service.html", {
        "quick_presets":      quick_presets,
        "hardware_presets":   hardware_presets,
        "quick_volumes":      _preset_volume_map(quick_presets),
        "hardware_volumes":   _preset_volume_map(hardware_presets),
        "replacements":       replacements,
        "replacement_counts": replacement_counts,
        "actions":            actions,
        "actions_json":       _service_actions_json(actions),
        "ink_levels":         ink_levels,
        "auto_sync_status":   auto_sync_status,
        "next_auto_run":      next_auto_run,
        "ink_channels":       INK_CHANNELS,
        "service_channels":   SERVICE_CHANNELS,
        "ink_channel_names":  INK_CHANNEL_NAMES,
        "ink_density_by_channel": ink_density_by_channel,
        "cartridge_tare_g":   cartridge_tare_g,
        "cartridge_capacity_ml": cartridge_capacity_ml,
        "white_loaded":       white_loaded,
        "archive_days":       archive_days,
        "archive_before_iso": archive_before_iso,
        "correction_error":    correction_error,
        "correction_saved":    correction_saved,
        "correction_nochange": correction_nochange,
        "correction_undo_action_id": correction_undo_action_id,
        "active":             "/service",
    })


# ── Cartridge replacements ─────────────────────────────────────────────

@router.post("/service/cartridge")
def log_cartridge(
    channel: str = Form(...),
    notes:   str = Form(""),
    db: Session = Depends(get_db),
):
    if channel == "CLEANING":
        # Cleaning + Moisturizing Liquid are two compartments of one physical UV
        # Cleaning Cartridge, so a single replacement resets both channels to full
        # and counts as one physical swap.
        crud.log_cartridge_replacement(db, channel="CLN", notes=notes)
        crud.log_cartridge_replacement(db, channel="ML", notes=notes)
    elif channel in SERVICE_CHANNELS:
        crud.log_cartridge_replacement(db, channel=channel, notes=notes)
    return RedirectResponse("/service", status_code=303)


@router.post("/service/cartridge/{rid}/delete")
def delete_cartridge_log(rid: int, db: Session = Depends(get_db)):
    row = db.query(models.CartridgeReplacement).filter_by(id=rid).first()
    if row:
        db.delete(row)
        db.commit()
        invalidate_dashboard_analytics_cache()
    return RedirectResponse("/service", status_code=303)


# ── Quick actions (preset-based) ──────────────────────────────────────

@router.post("/service/preset/{preset_id}/log")
async def log_quick_action(preset_id: int, request: Request, db: Session = Depends(get_db)):
    preset = crud.get_preset(db, preset_id)
    if not preset:
        return RedirectResponse("/service", status_code=303)
    try:
        volumes = json.loads(preset.volumes_json or "{}")
    except (ValueError, TypeError):
        volumes = {}
    form = await request.form()
    notes = (form.get("notes") or "").strip()
    occurred_at = _parse_occurred_at(form.get("occurred_at"))
    crud.log_service_action(
        db, preset_id=preset.id, kind=preset.kind,
        name=preset.name, volumes=volumes, notes=notes,
        occurred_at=occurred_at,
    )
    return RedirectResponse("/service", status_code=303)


@router.post("/service/preset/create")
async def create_preset(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    name = (form.get("name") or "").strip()
    kind = form.get("kind") or PRESET_KIND_QUICK
    if not name or kind not in PRESET_KINDS:
        return RedirectResponse("/service", status_code=303)
    volumes = _parse_volumes_from_form(dict(form))
    color = form.get("color") or "indigo"
    crud.create_preset(db, name=name, kind=kind, volumes=volumes, color=color, icon="droplet")
    return RedirectResponse("/service", status_code=303)


@router.post("/service/preset/{preset_id}/edit")
async def edit_preset(preset_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    name = (form.get("name") or "").strip() or None
    volumes = _parse_volumes_from_form(dict(form))
    crud.update_preset(db, preset_id, name=name, volumes=volumes)
    return RedirectResponse("/service", status_code=303)


@router.post("/service/preset/{preset_id}/delete")
def delete_preset(preset_id: int, db: Session = Depends(get_db)):
    crud.delete_preset(db, preset_id)
    return RedirectResponse("/service", status_code=303)


@router.post("/service/presets/reset-defaults")
def reset_presets(db: Session = Depends(get_db)):
    crud.reset_default_presets(db)
    return RedirectResponse("/service", status_code=303)


# ── Hardware events (custom volumes per submission) ──────────────────────────

@router.post("/service/hardware-event")
async def log_hardware_event(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    preset_id_raw = form.get("preset_id")
    notes = (form.get("notes") or "").strip()
    try:
        preset_id = int(preset_id_raw) if preset_id_raw else None
    except (TypeError, ValueError):
        preset_id = None

    preset = crud.get_preset(db, preset_id) if preset_id else None
    if not preset:
        return RedirectResponse("/service", status_code=303)

    if preset.tracks_ink:
        volumes = _parse_volumes_from_form(dict(form))
    else:
        volumes = {}

    occurred_at = _parse_occurred_at(form.get("occurred_at"))
    crud.log_service_action(
        db, preset_id=preset.id, kind=preset.kind,
        name=preset.name, volumes=volumes, notes=notes,
        occurred_at=occurred_at,
    )
    return RedirectResponse("/service", status_code=303)


@router.post("/service/action/{action_id}/delete")
def delete_action(action_id: int, db: Session = Depends(get_db)):
    crud.delete_service_action(db, action_id)
    return RedirectResponse("/service", status_code=303)


@router.post("/service/ink-correction")
async def log_ink_correction(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    targets = _parse_ink_correction_targets(dict(form))
    reason = (form.get("reason") or "").strip()

    if not targets:
        return RedirectResponse("/service?corr_error=nonzero_required", status_code=303)
    if not reason:
        return RedirectResponse("/service?corr_error=reason_required", status_code=303)

    # Each field is the desired *current remaining ml* for that channel. Convert it into
    # the consumption delta that makes the derived level equal the target:
    #   remaining = capacity - (existing_used + delta)  ->  delta = capacity - target - used
    # Using the uncapped used total means a channel that silently over-consumed (shown as
    # 0%) is corrected to exactly the entered level, with no surprise jump.
    ink_cfgs = crud.get_ink_configs(db)
    volumes: dict[str, float] = {}
    for ch, raw_target in targets.items():
        cfg = ink_cfgs.get(ch)
        capacity = (
            float(cfg.cartridge_capacity_ml)
            if cfg and cfg.cartridge_capacity_ml
            else INK_CHANNEL_DEFAULT_CAPACITY.get(ch, 100.0)
        )
        target = max(0.0, min(capacity, raw_target))
        used = cogs.ink_channel_used_ml(ch, db)
        delta = round(capacity - target - used, 4)
        if abs(delta) > 1e-9:
            volumes[ch] = delta

    if not volumes:
        # Every entered level already matches the current level — nothing to change.
        return RedirectResponse("/service?corr_nochange=1", status_code=303)

    action = crud.log_service_action(
        db,
        preset_id=None,
        kind=PRESET_KIND_QUICK,
        name="Ink Correction",
        volumes=volumes,
        notes=f"[INK_CORRECTION] {reason}",
    )
    return RedirectResponse(f"/service?corr_saved=1&corr_undo={action.id}", status_code=303)


@router.post("/service/ink-correction/{action_id}/undo")
def undo_ink_correction(action_id: int, db: Session = Depends(get_db)):
    row = db.query(models.ServiceAction).filter_by(id=action_id).first()
    if row and row.name_snapshot == "Ink Correction":
        db.delete(row)
        db.commit()
        invalidate_dashboard_analytics_cache()
    return RedirectResponse("/service", status_code=303)


# ── Changelog ──────────────────────────────────

@router.get("/changelog", response_class=HTMLResponse)
def changelog():
    """Render the application changelog."""
    return templates.get_template("changelog.html").render()
