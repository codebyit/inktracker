from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..templates_config import templates

router = APIRouter()

_DOCS_FILE = Path(__file__).parent.parent / "docs_links.yaml"


def _normalize_document_date(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""

    for fmt in ("%d/%m/%Y", "%d%m%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue

    return raw


def _load_docs() -> list[dict]:
    if not _DOCS_FILE.exists():
        return []
    try:
        data = yaml.safe_load(_DOCS_FILE.read_text(encoding="utf-8")) or []
        docs = [d for d in data if isinstance(d, dict)]
        for doc in docs:
            doc["document_date"] = _normalize_document_date(doc.get("document_date", ""))
        return docs
    except Exception:
        return []


def _save_docs(docs: list[dict]) -> None:
    _DOCS_FILE.write_text(
        yaml.dump(docs, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


@router.get("/documentation", response_class=HTMLResponse)
def docs_page(request: Request, db: Session = Depends(get_db), saved: str = ""):
    return templates.TemplateResponse(request, "docs.html", {
        "docs":   _load_docs(),
        "active": "/documentation",
        "saved":  saved,
    })


@router.post("/documentation/add")
async def add_doc(
    request: Request,
    name: str = Form(...),
    url: str = Form(...),
    document_date: str = Form(""),
):
    docs = _load_docs()
    docs.append({
        "name":          name.strip(),
        "url":           url.strip(),
        "document_date": _normalize_document_date(document_date),
    })
    _save_docs(docs)
    return RedirectResponse("/documentation?saved=1", status_code=303)


@router.post("/documentation/{index}/delete")
async def delete_doc(index: int):
    docs = _load_docs()
    if 0 <= index < len(docs):
        docs.pop(index)
        _save_docs(docs)
    return RedirectResponse("/documentation", status_code=303)


@router.post("/documentation/{index}/edit")
async def edit_doc(
    index: int,
    name: str = Form(...),
    url: str = Form(...),
    document_date: str = Form(""),
):
    docs = _load_docs()
    if 0 <= index < len(docs):
        docs[index] = {
            "name":          name.strip(),
            "url":           url.strip(),
            "document_date": _normalize_document_date(document_date),
        }
        _save_docs(docs)
    return RedirectResponse("/documentation?saved=1", status_code=303)
