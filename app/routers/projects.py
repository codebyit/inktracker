import json
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
import csv
import io
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud
from ..models import INK_MODES, PRINT_QUALITIES, INK_CHANNELS, INK_CHANNEL_HEX
from ..templates_config import templates

router = APIRouter()
_UPLOAD_DIR = Path(__file__).parent.parent.parent / "static" / "uploads"


@router.get("/projects", response_class=HTMLResponse)
def project_list(
    request: Request, db: Session = Depends(get_db),
    tab: str = "pipeline", search: str = "", sort: str = "newest",
):
    if tab == "completed":
        projects = crud.get_completed_projects(db, search=search, sort=sort)
    elif tab == "archived":
        projects = crud.get_archived_projects(db, search=search, sort=sort)
    elif tab == "trash":
        projects = crud.get_trash_projects(db)
    else:
        projects = crud.get_pipeline_projects(db, search=search, sort=sort)
    return templates.TemplateResponse(request, "projects/list.html", {
        "projects": projects,
        "tab":      tab,
        "search":   search,
        "sort":     sort,
        "active":   "/projects",
    })


@router.get("/projects/new", response_class=HTMLResponse)
def project_new(request: Request, db: Session = Depends(get_db)):
    settings_json = crud.get_settings_json(db)
    return templates.TemplateResponse(request, "projects/wizard.html", {
        "ink_modes":       INK_MODES,
        "print_qualities": PRINT_QUALITIES,
        "settings_json":   json.dumps(settings_json),
        "INK_CHANNEL_HEX": INK_CHANNEL_HEX,
        "active":          "/projects/new",
    })


@router.post("/projects/new")
async def project_create(
    request: Request,
    db: Session = Depends(get_db),
    name:                str   = Form(...),
    units:               int   = Form(1),
    sell_price_per_unit: float = Form(0.0),
    print_time_hours:    float = Form(0.0),
    hands_on_hours:      float = Form(0.0),
    ink_mode:            str   = Form("CMYK"),
    print_quality:       str   = Form("Standard"),
    material:            str   = Form("Ceramics"),
    notes:               str   = Form(""),
    ink_usage_json:      str   = Form("{}"),
    bom_json:            str   = Form("[]"),
    photo: UploadFile = File(None),
    print_bed:           str   = Form("Standard"),
    alignment:           str   = Form("Photo"),
    craft_mode:          str   = Form("Flat"),
    craft_ink_mode:      str   = Form(""),
    craft_mode_params_json: str = Form("{}"),
    substrate:           str   = Form(""),
    white_choke_mm:      float = Form(0.20),
    layer_stack_json:    str   = Form("[]"),
    status:              str   = Form("Draft"),
    project_type:        str   = Form("commercial"),
):
    ink_usage = json.loads(ink_usage_json)
    bom_items = json.loads(bom_json)

    # Sanitise: only keep channels that have ml > 0
    ink_usage = {ch: float(ml) for ch, ml in ink_usage.items() if float(ml) > 0}

    photo_path = None
    if photo and photo.filename:
        _UPLOAD_DIR.mkdir(exist_ok=True)
        ext = Path(photo.filename).suffix.lower()
        if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            filename = f"{uuid.uuid4()}{ext}"
            content = await photo.read()
            (_UPLOAD_DIR / filename).write_bytes(content)
            photo_path = f"/static/uploads/{filename}"

    project = crud.create_project(
        db=db,
        name=name, units=units,
        sell_price_per_unit=sell_price_per_unit,
        print_time_hours=print_time_hours,
        hands_on_hours=hands_on_hours,
        ink_mode=ink_mode, print_quality=print_quality,
        material=material,
        ink_usage=ink_usage, bom_items=bom_items,
        notes=notes, photo_path=photo_path,
        print_bed=print_bed, alignment=alignment,
        craft_mode=craft_mode, craft_ink_mode=craft_ink_mode,
        craft_mode_params_json=craft_mode_params_json, substrate=substrate,
        white_choke_mm=white_choke_mm, layer_stack_json=layer_stack_json,
        status=status,
        project_type=project_type,
    )
    return RedirectResponse(f"/projects/{project.id}", status_code=303)


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(project_id: int, request: Request, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        return RedirectResponse("/projects", status_code=302)
    return templates.TemplateResponse(request, "projects/detail.html", {
        "project": project,
        "active":  "/projects",
    })


@router.get("/projects/{project_id}/edit", response_class=HTMLResponse)
def project_edit_form(project_id: int, request: Request, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        return RedirectResponse("/projects", status_code=302)
    settings_json = crud.get_settings_json(db)
    ink_usage = {u.channel: u.ml_used for u in project.ink_usage}
    bom_items = [
        {"name": b.name, "qty": b.quantity, "unit": b.unit, "unitCost": b.unit_cost}
        for b in project.bom_items
    ]
    project_data = {
        "id":                  project.id,
        "name":                project.name,
        "units":               project.units,
        "sell_price_per_unit": project.sell_price_per_unit,
        "print_time_hours":    project.print_time_hours,
        "hands_on_hours":      project.hands_on_hours,
        "ink_mode":            project.ink_mode,
        "print_quality":       project.print_quality,
        "material":            project.material or "Ceramics",
        "notes":               project.notes or "",
        "print_bed":           project.print_bed or "Standard",
        "alignment":           project.alignment or "Photo",
        "craft_mode":          project.craft_mode or "Flat",
        "craft_ink_mode":      project.craft_ink_mode or "",
        "craft_mode_params_json": project.craft_mode_params_json or "{}",
        "substrate":           project.substrate or "",
        "white_choke_mm":      project.white_choke_mm or 0.20,
        "layer_stack_json":    project.layer_stack_json or "[]",
        "ink_usage":           ink_usage,
        "bom_items":           bom_items,
        "photo_path":          project.photo_path or "",
        "status":              project.status or "Draft",
        "project_type":        project.project_type or "commercial",
    }
    return templates.TemplateResponse(request, "projects/wizard.html", {
        "ink_modes":       INK_MODES,
        "print_qualities": PRINT_QUALITIES,
        "settings_json":   json.dumps(settings_json),
        "INK_CHANNEL_HEX": INK_CHANNEL_HEX,
        "active":          "/projects",
        "project_json":    json.dumps(project_data),
        "edit_id":         project.id,
    })


@router.post("/projects/{project_id}/edit")
async def project_update(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    name:                str   = Form(...),
    units:               int   = Form(1),
    sell_price_per_unit: float = Form(0.0),
    print_time_hours:    float = Form(0.0),
    hands_on_hours:      float = Form(0.0),
    ink_mode:            str   = Form("CMYK"),
    print_quality:       str   = Form("Standard"),
    material:            str   = Form("Ceramics"),
    notes:               str   = Form(""),
    ink_usage_json:      str   = Form("{}"),
    bom_json:            str   = Form("[]"),
    photo: UploadFile = File(None),
    print_bed:           str   = Form("Standard"),
    alignment:           str   = Form("Photo"),
    craft_mode:          str   = Form("Flat"),
    craft_ink_mode:      str   = Form(""),
    craft_mode_params_json: str = Form("{}"),
    substrate:           str   = Form(""),
    white_choke_mm:      float = Form(0.20),
    layer_stack_json:    str   = Form("[]"),
    status:              str   = Form("Draft"),
    project_type:        str   = Form("commercial"),
):
    ink_usage = json.loads(ink_usage_json)
    bom_items = json.loads(bom_json)
    ink_usage = {ch: float(ml) for ch, ml in ink_usage.items() if float(ml) > 0}

    photo_path = None
    if photo and photo.filename:
        _UPLOAD_DIR.mkdir(exist_ok=True)
        ext = Path(photo.filename).suffix.lower()
        if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            filename = f"{uuid.uuid4()}{ext}"
            content = await photo.read()
            (_UPLOAD_DIR / filename).write_bytes(content)
            photo_path = f"/static/uploads/{filename}"

    crud.update_project(
        db=db,
        project_id=project_id,
        name=name, units=units,
        sell_price_per_unit=sell_price_per_unit,
        print_time_hours=print_time_hours,
        hands_on_hours=hands_on_hours,
        ink_mode=ink_mode, print_quality=print_quality,
        material=material,
        ink_usage=ink_usage, bom_items=bom_items,
        notes=notes, photo_path=photo_path,
        print_bed=print_bed, alignment=alignment,
        craft_mode=craft_mode, craft_ink_mode=craft_ink_mode,
        craft_mode_params_json=craft_mode_params_json, substrate=substrate,
        white_choke_mm=white_choke_mm, layer_stack_json=layer_stack_json,
        status=status,
        project_type=project_type,
    )
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.post("/projects/{project_id}/delete")
def project_delete(project_id: int, db: Session = Depends(get_db)):
    crud.delete_project(db, project_id)
    return RedirectResponse("/projects", status_code=303)

@router.post("/projects/{project_id}/restore")
def project_restore(project_id: int, db: Session = Depends(get_db)):
    crud.restore_project(db, project_id)
    return RedirectResponse("/projects?tab=trash", status_code=303)


@router.post("/projects/{project_id}/permanent-delete")
def project_permanent_delete(project_id: int, db: Session = Depends(get_db)):
    crud.permanent_delete_project(db, project_id)
    return RedirectResponse("/projects?tab=trash", status_code=303)


@router.post("/projects/{project_id}/archive")
def project_archive(project_id: int, db: Session = Depends(get_db)):
    crud.archive_project(db, project_id)
    return RedirectResponse("/projects?tab=archived", status_code=303)


@router.post("/projects/{project_id}/unarchive")
def project_unarchive(project_id: int, db: Session = Depends(get_db)):
    crud.unarchive_project(db, project_id)
    return RedirectResponse("/projects?tab=archived", status_code=303)


@router.post("/projects/{project_id}/duplicate")
def project_duplicate(project_id: int, db: Session = Depends(get_db)):
    new_p = crud.duplicate_project(db, project_id)
    if new_p:
        return RedirectResponse(f"/projects/{new_p.id}/edit", status_code=303)
    return RedirectResponse("/projects", status_code=303)


@router.post("/projects/{project_id}/status")
async def project_set_status(project_id: int, request: Request, db: Session = Depends(get_db)):
    data   = await request.json()
    status = data.get("status", "Draft")
    crud.set_project_status(db, project_id, status)
    return JSONResponse({"ok": True})


@router.get("/projects/export/csv")
def projects_export_csv(
    db: Session = Depends(get_db),
    tab: str = "completed",
    search: str = "",
):
    if tab == "completed":
        rows = crud.get_completed_projects(db, search=search)
    elif tab == "archived":
        rows = crud.get_archived_projects(db, search=search)
    else:
        rows = crud.get_pipeline_projects(db, search=search)
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow([
        "ID", "Name", "Status", "Date", "Units", "Ink Mode",
        "Sell/u", "COGS/u", "Revenue", "COGS", "Profit", "Margin%",
        "Ink ml", "Print Time h",
    ])
    for p in rows:
        w.writerow([
            p.id, p.name, p.status or "Draft",
            p.created_at.strftime("%Y-%m-%d"),
            p.units, p.ink_mode,
            round(p.sell_price_per_unit, 4),
            round(p.cogs_per_unit, 4),
            round(p.total_revenue, 4),
            round(p.total_cogs, 4),
            round(p.total_profit, 4),
            round(p.margin_pct, 2),
            p.total_ink_ml,
            round(p.print_time_hours, 4),
        ])
    buf.seek(0)
    filename = "inktracker-export.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

# ── Print Templates API ───────────────────────────────────────────────────────

@router.get("/templates/list")
def template_list_api(db: Session = Depends(get_db)):
    ts = crud.get_templates(db)
    return JSONResponse([{
        "id": t.id, "name": t.name,
        "print_bed": t.print_bed, "alignment": t.alignment,
        "material": t.material, "substrate": t.substrate,
        "print_quality": t.print_quality, "white_choke_mm": t.white_choke_mm,
        "craft_mode": t.craft_mode, "ink_mode": t.ink_mode,
        "craft_ink_mode": t.craft_ink_mode,
        "craft_mode_params_json": t.craft_mode_params_json,
        "layer_stack_json": t.layer_stack_json,
    } for t in ts])


@router.post("/templates")
async def template_create_api(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    crud.create_template(
        db, name=data.get("name", "Untitled"),
        print_bed=data.get("print_bed", "Standard"),
        alignment=data.get("alignment", "Photo"),
        material=data.get("material", "Ceramics"),
        substrate=data.get("substrate", ""),
        print_quality=data.get("print_quality", "Standard"),
        white_choke_mm=float(data.get("white_choke_mm", 0.20)),
        craft_mode=data.get("craft_mode", "Flat"),
        ink_mode=data.get("ink_mode", "CMYK"),
        craft_ink_mode=data.get("craft_ink_mode", ""),
        craft_mode_params_json=data.get("craft_mode_params_json", "{}"),
        layer_stack_json=data.get("layer_stack_json", "[]"),
    )
    return JSONResponse({"ok": True})


@router.delete("/templates/{template_id}")
def template_delete_api(template_id: int, db: Session = Depends(get_db)):
    crud.delete_template(db, template_id)
    return JSONResponse({"ok": True})
