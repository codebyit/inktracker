from datetime import datetime
from io import BytesIO
import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..models import INK_CHANNEL_NAMES, SERVICE_CHANNELS
from ..templates_config import templates

router = APIRouter()


@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request, db: Session = Depends(get_db)):
    materials = crud.get_material_items(db)
    categories = crud.get_material_categories(db)
    ink_global = crud.get_ink_global_config(db)
    return templates.TemplateResponse(
        request,
        "inventory.html",
        {
            "active": "/inventory",
            "service_channels": SERVICE_CHANNELS,
            "ink_channel_names": INK_CHANNEL_NAMES,
            "cartridge_capacity_ml": float(ink_global.cartridge_capacity_ml or 100.0),
            "materials": materials,
            "material_categories": categories,
        },
    )


def _lot_json(lot):
    return {
        "id": lot.id,
        "channel": lot.channel,
        "channel_name": INK_CHANNEL_NAMES.get(lot.channel, lot.channel),
        "quantity_ml": float(lot.quantity_ml or 0.0),
        "serial_number": lot.serial_number or "",
        "expires_on": lot.expires_on,
        "box_expires_on": lot.box_expires_on,
        "is_in_use": bool(lot.is_in_use),
        "installed_at": lot.installed_at.isoformat() if lot.installed_at else None,
        "created_at": lot.created_at.isoformat() if lot.created_at else None,
        "notes": lot.notes or "",
    }


def _movement_json(movement):
    return {
        "id": movement.id,
        "material_item_id": movement.material_item_id,
        "material_name": movement.material_item.name if movement.material_item else "",
        "project_id": movement.project_id,
        "project_name": movement.project.name if movement.project else "",
        "movement_type": movement.movement_type,
        "quantity": float(movement.quantity or 0.0),
        "occurred_at": movement.occurred_at.isoformat() if movement.occurred_at else None,
        "notes": movement.notes or "",
    }


@router.get("/inventory/data")
def inventory_data(db: Session = Depends(get_db)):
    lots = crud.get_cartridge_inventory_lots(db)
    materials = crud.get_material_inventory_balance(db)
    movements = crud.get_material_inventory_movements(db, limit=200)
    ink_global = crud.get_ink_global_config(db)

    lots_by_channel = {ch: [] for ch in SERVICE_CHANNELS}
    for lot in lots:
        lots_by_channel.setdefault(lot.channel, []).append(_lot_json(lot))

    return JSONResponse({
        "cartridges": lots_by_channel,
        "materials": materials,
        "movements": [_movement_json(m) for m in movements],
        "cartridge_capacity_ml": float(ink_global.cartridge_capacity_ml or 100.0),
    })


@router.post("/inventory/materials/items")
async def create_material_item(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    name = str(data.get("name", "")).strip()
    if not name:
        return JSONResponse({"error": "Name is required"}, status_code=422)

    category = str(data.get("category", "Other")).strip() or "Other"
    unit = str(data.get("unit", "pcs")).strip() or "pcs"
    unit_cost = float(data.get("unit_cost", 0) or 0)
    initial_qty = float(data.get("initial_qty", 0) or 0)

    item = crud.create_material_item(
        db,
        name=name,
        category=category,
        unit_cost=unit_cost,
        unit=unit,
    )

    if initial_qty > 0:
        try:
            crud.create_material_inventory_movement(
                db,
                material_item_id=item.id,
                movement_type="in",
                quantity=initial_qty,
                notes="Initial stock",
            )
        except ValueError:
            db.rollback()
            return JSONResponse({"error": "Could not register initial stock"}, status_code=422)

    db.commit()
    db.refresh(item)
    return JSONResponse(
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "unit": item.unit,
            "unit_cost": float(item.unit_cost or 0.0),
            "quantity_added_total": float(item.quantity_added_total or 0.0),
            "quantity_consumed_total": float(item.quantity_consumed_total or 0.0),
            "quantity_available": float(item.quantity_added_total or 0.0) - float(item.quantity_consumed_total or 0.0),
        }
    )


@router.put("/inventory/materials/items/{item_id}")
async def update_material_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    name = str(data.get("name", "")).strip()
    if not name:
        return JSONResponse({"error": "Name is required"}, status_code=422)

    category = str(data.get("category", "Other")).strip() or "Other"
    unit = str(data.get("unit", "pcs")).strip() or "pcs"
    unit_cost = float(data.get("unit_cost", 0) or 0)

    item = crud.update_material_item(
        db,
        item_id=item_id,
        name=name,
        category=category,
        unit_cost=unit_cost,
        unit=unit,
    )
    if not item:
        return JSONResponse({"error": "Material not found"}, status_code=404)

    return JSONResponse(
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "unit": item.unit,
            "unit_cost": float(item.unit_cost or 0.0),
            "quantity_added_total": float(item.quantity_added_total or 0.0),
            "quantity_consumed_total": float(item.quantity_consumed_total or 0.0),
            "quantity_available": float(item.quantity_added_total or 0.0) - float(item.quantity_consumed_total or 0.0),
        }
    )


@router.delete("/inventory/materials/items/{item_id}")
def remove_material_item(item_id: int, db: Session = Depends(get_db)):
    item = next((m for m in crud.get_material_items(db) if m.id == item_id), None)
    if not item:
        return JSONResponse({"error": "Material not found"}, status_code=404)

    try:
        crud.delete_material_item(db, item_id=item_id)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)

    return JSONResponse({"ok": True})


@router.post("/inventory/cartridges/lots")
async def create_cartridge_lot(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    channel = str(data.get("channel", "")).strip().upper()
    serial_number = str(data.get("serial_number", "")).strip().upper()

    if channel not in SERVICE_CHANNELS:
        return JSONResponse({"error": "Invalid channel"}, status_code=422)
    if serial_number and not re.fullmatch(r"[A-Za-z0-9]+", serial_number):
        return JSONResponse({"error": "Serial number must be alphanumeric"}, status_code=422)

    # Every lot row represents one full cartridge unit.
    ink_global = crud.get_ink_global_config(db)
    quantity_ml = float((ink_global.cartridge_capacity_ml if ink_global else 100.0) or 100.0)

    try:
        lot = crud.create_cartridge_inventory_lot(
            db,
            channel=channel,
            quantity_ml=quantity_ml,
            serial_number=serial_number or None,
            expires_on=(data.get("expires_on") or None),
            box_expires_on=(data.get("box_expires_on") or None),
            notes=(data.get("notes") or ""),
            is_in_use=bool(data.get("is_in_use", False)),
        )
    except IntegrityError:
        db.rollback()
        return JSONResponse({"error": "A lot with this serial number already exists."}, status_code=409)
    return JSONResponse(_lot_json(lot))


@router.post("/inventory/cartridges/lots/{lot_id}/in-use")
async def set_cartridge_lot_in_use(lot_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    lot = crud.set_cartridge_lot_in_use(db, lot_id=lot_id, is_in_use=bool(data.get("is_in_use", True)))
    if not lot:
        return JSONResponse({"error": "Lot not found"}, status_code=404)
    return JSONResponse(_lot_json(lot))


@router.post("/inventory/cartridges/lots/{lot_id}/quantity")
async def set_cartridge_lot_quantity(lot_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    lot = crud.update_cartridge_lot_quantity(db, lot_id=lot_id, quantity_ml=float(data.get("quantity_ml", 0) or 0))
    if not lot:
        return JSONResponse({"error": "Lot not found"}, status_code=404)
    return JSONResponse(_lot_json(lot))


@router.put("/inventory/cartridges/lots/{lot_id}")
async def update_cartridge_lot(lot_id: int, request: Request, db: Session = Depends(get_db)):
    """Edit descriptive fields on an existing cartridge lot.

    Use case: the chip expiration date is only printed on the cartridge label
    and is typically discovered when the cartridge is actually installed in
    the printer — after the lot was already created. This endpoint lets the
    user backfill / correct those fields without deleting and re-creating
    the lot.
    """
    data = await request.json()

    # Validate channel (if provided) and serial (if provided).
    payload = {}
    if "channel" in data:
        channel = str(data.get("channel") or "").strip().upper()
        if channel not in SERVICE_CHANNELS:
            return JSONResponse({"error": "Invalid channel"}, status_code=422)
        payload["channel"] = channel
    if "serial_number" in data:
        serial_number = str(data.get("serial_number") or "").strip().upper()
        if serial_number and not re.fullmatch(r"[A-Za-z0-9]+", serial_number):
            return JSONResponse({"error": "Serial number must be alphanumeric"}, status_code=422)
        payload["serial_number"] = serial_number
    if "expires_on" in data:
        payload["expires_on"] = data.get("expires_on") or ""
    if "box_expires_on" in data:
        payload["box_expires_on"] = data.get("box_expires_on") or ""
    if "notes" in data:
        payload["notes"] = data.get("notes") or ""

    try:
        lot = crud.update_cartridge_lot(db, lot_id=lot_id, **payload)
    except IntegrityError:
        db.rollback()
        return JSONResponse({"error": "A lot with this serial number already exists."}, status_code=409)
    if not lot:
        return JSONResponse({"error": "Lot not found"}, status_code=404)
    return JSONResponse(_lot_json(lot))


@router.delete("/inventory/cartridges/lots/{lot_id}")
def remove_cartridge_lot(lot_id: int, db: Session = Depends(get_db)):
    crud.delete_cartridge_lot(db, lot_id=lot_id)
    return JSONResponse({"ok": True})


@router.post("/inventory/materials/movements")
async def create_material_movement(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    occurred_at = None
    if data.get("occurred_at"):
        try:
            occurred_at = datetime.fromisoformat(str(data.get("occurred_at")))
        except ValueError:
            return JSONResponse({"error": "Invalid occurred_at format"}, status_code=422)

    try:
        movement = crud.create_material_inventory_movement(
            db,
            material_item_id=int(data.get("material_item_id", 0)),
            movement_type=str(data.get("movement_type", "")).strip().lower(),
            quantity=float(data.get("quantity", 0) or 0),
            project_id=int(data["project_id"]) if data.get("project_id") is not None else None,
            notes=str(data.get("notes", "")),
            occurred_at=occurred_at,
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=422)

    db.commit()
    db.refresh(movement)
    return JSONResponse(_movement_json(movement))


@router.get("/inventory/report.pdf")
def inventory_report_pdf(db: Session = Depends(get_db)):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception:
        return JSONResponse(
            {"error": "PDF dependency missing. Install reportlab to enable this endpoint."},
            status_code=500,
        )

    report = crud.get_inventory_report_data(db)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    def line(text: str, *, spacer: int = 16):
        nonlocal y
        if y <= 40:
            pdf.showPage()
            y = height - 40
        pdf.drawString(40, y, text)
        y -= spacer

    pdf.setFont("Helvetica-Bold", 12)
    line("Inventory Check Report")
    pdf.setFont("Helvetica", 10)
    line(f"Generated at: {report['generated_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}", spacer=20)

    pdf.setFont("Helvetica-Bold", 11)
    line("Cartridge Lots")
    pdf.setFont("Helvetica", 9)
    if not report["cartridge_lots"]:
        line("- No cartridge lots registered.")
    else:
        for lot in report["cartridge_lots"]:
            status = "IN USE" if lot.is_in_use else "available"
            chip_expiry = lot.expires_on or "n/a"
            box_expiry = lot.box_expires_on or "n/a"
            serial = lot.serial_number or "n/a"
            line(f"- {lot.channel}: SN {serial} | chip exp {chip_expiry} | box exp {box_expiry} | {status}")

    line("", spacer=10)
    pdf.setFont("Helvetica-Bold", 11)
    line("Material Balances")
    pdf.setFont("Helvetica", 9)
    if not report["materials"]:
        line("- No materials registered.")
    else:
        for item in report["materials"]:
            line(
                f"- {item['name']} ({item['category']}): +{item['quantity_added_total']:.2f} "
                f"- {item['quantity_consumed_total']:.2f} = {item['quantity_available']:.2f} {item['unit']}"
            )

    line("", spacer=10)
    pdf.setFont("Helvetica-Bold", 11)
    line("Recent Material Movements")
    pdf.setFont("Helvetica", 9)
    for mv in report["movements"][:40]:
        when = mv.occurred_at.strftime("%Y-%m-%d") if mv.occurred_at else "n/a"
        proj = mv.project.name if mv.project else "-"
        line(f"- {when} | {mv.movement_type.upper()} {mv.quantity:.2f} | {mv.material_item.name} | project: {proj}")

    pdf.save()
    buffer.seek(0)

    filename = f"inventory-check-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
