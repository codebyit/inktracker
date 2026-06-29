from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..database import get_db
from .. import crud, models
from ..cache import get_or_set_json
from ..templates_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    kpis = get_or_set_json("dashboard:kpis", 30, lambda: crud.get_dashboard_kpis(db))
    ink_levels = get_or_set_json("dashboard:ink_levels", 30, lambda: crud.get_ink_levels(db))
    recent     = crud.get_projects(db, limit=6)

    active_q = db.query(models.Project).filter(
        models.Project.deleted_at == None,  # noqa: E711
        models.Project.archived == False,   # noqa: E712
    )
    pipeline = active_q.filter(models.Project.status.in_(["Draft", "Queued", "Printing"]))
    completed = active_q.filter(models.Project.status == "Completed")

    all_live_q = db.query(models.Project).filter(
        models.Project.deleted_at == None,  # noqa: E711
    )

    gauge_channels = models.INK_CHANNELS
    gauge_levels = [ink_levels[ch] for ch in gauge_channels if ch in ink_levels]
    low_ink_count = sum(1 for lv in gauge_levels if lv.get("status") == "low")
    avg_used_pct = round(sum((100 - (lv.get("pct") or 0)) for lv in gauge_levels) / len(gauge_levels), 1) if gauge_levels else 0.0
    remaining_ml = round(sum((lv.get("remaining_ml") or 0.0) for lv in gauge_levels), 1)
    used_ml = round(sum(((lv.get("capacity_ml") or 0.0) - (lv.get("remaining_ml") or 0.0)) for lv in gauge_levels), 1)
    total_capacity_ml = round(sum((lv.get("capacity_ml") or 0.0) for lv in gauge_levels), 1)

    active_projects = pipeline.count()
    all_projects = all_live_q.count()

    active_print_hours = sum((p.print_time_hours or 0.0) for p in pipeline.all())
    all_print_hours = sum((p.print_time_hours or 0.0) for p in all_live_q.all())

    def _fmt_hhmm(hours: float) -> str:
        total_minutes = int(round((hours or 0.0) * 60))
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}:{m:02d}"

    dashboard_stats = {
        "pipeline_total": pipeline.count(),
        "draft_count": pipeline.filter(models.Project.status == "Draft").count(),
        "queued_count": pipeline.filter(models.Project.status == "Queued").count(),
        "printing_count": pipeline.filter(models.Project.status == "Printing").count(),
        "completed_count": completed.count(),
        "active_colors": len(gauge_levels),
        "low_ink_count": low_ink_count,
        "avg_used_pct": avg_used_pct,
        "remaining_ml": remaining_ml,
        "used_ml": used_ml,
        "total_capacity_ml": total_capacity_ml,
        "active_projects": active_projects,
        "all_projects": all_projects,
        "active_print_time": _fmt_hhmm(active_print_hours),
        "all_print_time": _fmt_hhmm(all_print_hours),
    }

    lots = crud.get_cartridge_inventory_lots(db)
    materials_balance = crud.get_material_inventory_balance(db)
    ink_global = crud.get_ink_global_config(db)
    cap_ml = float((ink_global.cartridge_capacity_ml) or 100.0)
    low_lot_threshold_pct = float((ink_global.low_inventory_lot_pct) if ink_global and ink_global.low_inventory_lot_pct is not None else 25.0)
    low_lot_threshold_ml = cap_ml * (max(0.0, min(100.0, low_lot_threshold_pct)) / 100.0)

    today = datetime.utcnow().date()
    in_30_days = today + timedelta(days=30)
    expiring_soon = 0
    expired = 0
    low_stock_lots = 0

    for lot in lots:
        if float(lot.quantity_ml or 0.0) <= low_lot_threshold_ml:
            low_stock_lots += 1
        if lot.expires_on:
            try:
                expiry_date = datetime.strptime(lot.expires_on, "%Y-%m-%d").date()
                if expiry_date < today:
                    expired += 1
                elif expiry_date <= in_30_days:
                    expiring_soon += 1
            except ValueError:
                pass

    low_materials = sum(1 for item in materials_balance if float(item.get("quantity_available") or 0.0) <= 0.0)

    inventory_alerts = {
        "expired_lots": expired,
        "expiring_soon_lots": expiring_soon,
        "low_stock_lots": low_stock_lots,
        "low_materials": low_materials,
        "low_lot_threshold_pct": low_lot_threshold_pct,
    }

    return templates.TemplateResponse(request, "dashboard.html", {
        "kpis":       kpis,
        "ink_levels": ink_levels,
        "recent":     recent,
        "dashboard_stats": dashboard_stats,
        "inventory_alerts": inventory_alerts,
        "active":     "/",
    })
