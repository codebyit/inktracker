from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud

router = APIRouter()


def _cat_json(c):
    return {"id": c.id, "name": c.name, "sort_order": c.sort_order}


def _item_json(i):
    return {
        "id": i.id, "name": i.name, "category": i.category,
        "unit_cost": i.unit_cost, "unit": i.unit,
        "quantity_added_total": float(i.quantity_added_total or 0.0),
        "quantity_consumed_total": float(i.quantity_consumed_total or 0.0),
        "quantity_available": float(i.quantity_added_total or 0.0) - float(i.quantity_consumed_total or 0.0),
    }


@router.get("/materials/data")
def materials_data(db: Session = Depends(get_db)):
    cats  = crud.get_material_categories(db)
    items = crud.get_material_items(db)
    return JSONResponse({
        "categories": [_cat_json(c) for c in cats],
        "items":      [_item_json(i) for i in items],
    })


@router.post("/materials/categories")
async def category_create(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    name = data.get("name", "").strip()
    if not name:
        return JSONResponse({"error": "Name required"}, status_code=422)
    existing = [c.name.lower() for c in crud.get_material_categories(db)]
    if name.lower() in existing:
        return JSONResponse({"error": "Already exists"}, status_code=409)
    cat = crud.create_material_category(db, name)
    return JSONResponse(_cat_json(cat))


@router.delete("/materials/categories/{name}")
def category_delete(name: str, db: Session = Depends(get_db)):
    crud.delete_material_category(db, name)
    return JSONResponse({"ok": True})


@router.post("/materials/items")
async def item_create(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    item = crud.create_material_item(
        db,
        name=data.get("name", ""),
        category=data.get("category", "Other"),
        unit_cost=float(data.get("unit_cost", 0)),
        unit=data.get("unit", "pcs"),
    )
    return JSONResponse(_item_json(item))


@router.put("/materials/items/{item_id}")
async def item_update(item_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    item = crud.update_material_item(
        db, item_id,
        name=data.get("name", ""),
        category=data.get("category", "Other"),
        unit_cost=float(data.get("unit_cost", 0)),
        unit=data.get("unit", "pcs"),
    )
    return JSONResponse(_item_json(item) if item else {"error": "Not found"})


@router.delete("/materials/items/{item_id}")
def item_delete(item_id: int, db: Session = Depends(get_db)):
    try:
        crud.delete_material_item(db, item_id)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)
    return JSONResponse({"ok": True})
