# Usage: pytest tests/  OR  python -m pytest tests/test_security_fixes.py
# Regression tests for the 2026-07-18 public-security-review fixes:
#   F1 XSS: wizard JSON blobs are HTML-safe (tojson, not json.dumps + | safe)
#   F2    : documentation link URLs are scheme-allowlisted (http/https only)
#   F6    : FastAPI /docs, /redoc, /openapi.json disabled unless ENABLE_API_DOCS
"""These validate the security hardening at the unit level (URL sanitizer,
template escaping, app doc-endpoint gating) without needing a running server."""
from __future__ import annotations

import importlib
import os
import sys

from jinja2 import Environment, FileSystemLoader, select_autoescape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ΓöÇΓöÇ F1: template escaping ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def test_tojson_neutralizes_script_breakout():
    """A </script> payload in a project field must not break out of the
    embedded <script type="application/json"> block."""
    env = Environment(autoescape=select_autoescape(["html"]))
    tmpl = env.from_string('<script>{{ data | tojson }}</script>')
    out = tmpl.render(data={"name": "</script><img src=x onerror=alert(1)>"})
    assert "</script><img" not in out          # no literal breakout
    assert "\\u003c/script" in out.lower()      # escaped instead


def test_wizard_template_uses_tojson_not_safe():
    """Guard against a regression back to `| safe` on the JSON blobs."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app", "templates", "projects", "wizard.html",
    )
    with open(path, encoding="utf-8") as fh:
        html = fh.read()
    for line in html.splitlines():
        if 'type="application/json"' in line:
            assert "| tojson" in line, f"JSON blob not using tojson: {line}"
            assert "| safe" not in line, f"JSON blob still uses | safe: {line}"


# ΓöÇΓöÇ F2: documentation URL scheme allowlist ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def test_sanitize_url_allowlist():
    from app.routers.docs import _sanitize_url

    assert _sanitize_url("https://ok.com/a") == "https://ok.com/a"
    assert _sanitize_url("http://ok.com") == "http://ok.com"
    # Dangerous schemes are rejected (blanked).
    assert _sanitize_url("javascript:alert(1)") == ""
    assert _sanitize_url("  JavaScript:alert(1)") == ""
    assert _sanitize_url("data:text/html,<script>") == ""
    assert _sanitize_url("vbscript:msgbox(1)") == ""
    # Scheme-less host is upgraded to https; junk is rejected.
    assert _sanitize_url("example.com/page") == "https://example.com/page"
    assert _sanitize_url("not a url") == ""
    assert _sanitize_url("") == ""


# ΓöÇΓöÇ F6: API docs disabled by default ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def test_api_docs_disabled_by_default():
    os.environ.pop("ENABLE_API_DOCS", None)
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    import app.main as m
    importlib.reload(m)
    assert m.app.docs_url is None
    assert m.app.redoc_url is None
    assert m.app.openapi_url is None


def test_api_docs_enabled_by_flag():
    os.environ["ENABLE_API_DOCS"] = "true"
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    import app.main as m
    importlib.reload(m)
    try:
        assert m.app.docs_url == "/docs"
        assert m.app.openapi_url == "/openapi.json"
    finally:
        os.environ.pop("ENABLE_API_DOCS", None)
        importlib.reload(m)
