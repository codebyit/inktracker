from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..templates_config import templates
from ..paths import DOCS_FILE as _DOCS_FILE

router = APIRouter()

# Only these URL schemes are allowed for documentation links. This blocks
# `javascript:`, `data:`, `vbscript:` and similar payloads that would execute
# when the link is clicked (the doc URL is rendered directly into an href).
_ALLOWED_URL_SCHEMES = {"http", "https"}


def _sanitize_url(raw: str) -> str:
    """Return a safe http/https URL, or "" if the scheme is not allowed.

    A bare, scheme-less host (e.g. ``example.com/page``) is upgraded to
    ``https://`` for convenience; anything with a disallowed scheme
    (``javascript:``, ``data:``, ...) is rejected.
    """
    url = (raw or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.scheme:
        # No scheme -> assume https for a plausible host-looking value.
        return f"https://{url}" if "." in url.split("/")[0] else ""
    if parsed.scheme.lower() in _ALLOWED_URL_SCHEMES:
        return url
    return ""


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
            # Defense in depth: neutralize any unsafe URL already on disk.
            doc["url"] = _sanitize_url(doc.get("url", ""))
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
        "url":           _sanitize_url(url),
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
            "url":           _sanitize_url(url),
            "document_date": _normalize_document_date(document_date),
        }
        _save_docs(docs)
    return RedirectResponse("/documentation?saved=1", status_code=303)
