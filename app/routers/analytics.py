from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud
from ..cache import get_or_set_json
from ..templates_config import templates

router = APIRouter()


@router.get("/analytics", response_class=HTMLResponse)
def analytics_page(request: Request, db: Session = Depends(get_db)):
    combined = get_or_set_json(
        "analytics:page_data",
        60,
        lambda: {
            "data": crud.get_analytics_data(db),
            "financials": crud.get_financials_data(db),
        },
    )
    return templates.TemplateResponse(request, "analytics.html", {
        "data":       combined["data"],
        "financials": combined["financials"],
        "active":     "/analytics",
    })


@router.get("/api/analytics")
def analytics_api(db: Session = Depends(get_db)):
    data = get_or_set_json("analytics:api_data", 60, lambda: crud.get_analytics_data(db))
    return JSONResponse(data)
