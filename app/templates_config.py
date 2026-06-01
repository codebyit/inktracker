from pathlib import Path
from fastapi.templating import Jinja2Templates
from .models import (
    INK_CHANNELS, SERVICE_CHANNELS, INK_CHANNEL_NAMES, INK_CHANNEL_HEX,
    PROJECT_TYPES, PROJECT_TYPE_LABELS,
)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

templates.env.globals.update({
    "INK_CHANNELS":      INK_CHANNELS,
    "SERVICE_CHANNELS":  SERVICE_CHANNELS,
    "INK_CHANNEL_NAMES": INK_CHANNEL_NAMES,
    "INK_CHANNEL_HEX":   INK_CHANNEL_HEX,
    "currency":          "€",
    "PROJECT_TYPES":       PROJECT_TYPES,
    "PROJECT_TYPE_LABELS": PROJECT_TYPE_LABELS,
    "MARGIN_BADGE": {
        "Strong":  "bg-emerald-100 text-emerald-700 border border-emerald-200",
        "Target":  "bg-blue-100   text-blue-700   border border-blue-200",
        "Minimum": "bg-amber-100  text-amber-700  border border-amber-200",
        "Loss":    "bg-red-100    text-red-700    border border-red-200",
        "N/A":     "bg-slate-100  text-slate-500  border border-slate-200",
    },
    "MARGIN_LABEL": {
        "Strong":  "Strong ≥50%",
        "Target":  "Target 30–50%",
        "Minimum": "Minimum 0–30%",
        "Loss":    "Loss <0%",
        "N/A":     "N/A",
    },
    "PROJECT_TYPE_BADGE": {
        "commercial": "bg-slate-100  text-slate-600  border border-slate-200",
        "gift":       "bg-purple-100 text-purple-700 border border-purple-200",
        "sample":     "bg-cyan-100   text-cyan-700   border border-cyan-200",
        "internal":   "bg-orange-100 text-orange-700 border border-orange-200",
    },
})
