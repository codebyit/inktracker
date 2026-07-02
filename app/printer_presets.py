"""Printer presets and supported currencies for the first-time setup wizard.

These are plain Python constants (no database table) so new printer models and
currencies can be added in code without a migration. The seeded defaults and the
setup wizard both source their starting values from here, keeping a single source
of truth.

Currency is stored as a *symbol* string on ``InkGlobalConfig.currency`` (the
existing field). We use ``CA$`` / ``A$`` for the Canadian and Australian dollars
so the three dollar currencies are distinguishable in the prepend-symbol price
templates without any schema change.
"""
from __future__ import annotations

# ── Supported currencies ──────────────────────────────────────────────────────
# Ordered list shown in the wizard and Settings. ``code`` is the canonical key
# used to look up printer-preset ink prices; ``symbol`` is what gets stored and
# rendered on prices.
CURRENCIES: list[dict] = [
    {"code": "EUR", "symbol": "€",   "label": "Euro"},
    {"code": "GBP", "symbol": "£",   "label": "British Pound"},
    {"code": "USD", "symbol": "$",   "label": "US Dollar"},
    {"code": "CAD", "symbol": "CA$", "label": "Canadian Dollar"},
    {"code": "AUD", "symbol": "A$",  "label": "Australian Dollar"},
]

DEFAULT_CURRENCY_CODE = "EUR"

_SYMBOL_BY_CODE = {c["code"]: c["symbol"] for c in CURRENCIES}
_CODE_BY_SYMBOL = {c["symbol"]: c["code"] for c in CURRENCIES}


def symbol_for(code: str) -> str:
    """Return the currency symbol for a currency code (falls back to EUR)."""
    return _SYMBOL_BY_CODE.get((code or "").upper(), _SYMBOL_BY_CODE[DEFAULT_CURRENCY_CODE])


def code_for(symbol: str) -> str:
    """Best-effort reverse lookup: currency symbol -> code (falls back to EUR)."""
    return _CODE_BY_SYMBOL.get(symbol or "", DEFAULT_CURRENCY_CODE)


# ── Printer presets ───────────────────────────────────────────────────────────
# Each preset carries the machine cost defaults, the ink hardware defaults, and a
# per-currency ink price-per-cartridge (applies to all color inks + Gloss). The
# cleaning solution (CLN) and moisturizing liquid (ML) reservoirs are priced at
# 0.0 and are handled separately (not part of ``ink_price_by_currency``).
PRINTER_PRESETS: dict[str, dict] = {
    "eufymake_e1": {
        "label": "Eufymake E1",
        "machine": {
            "purchase_price":     2500.0,
            "setup_cost":         0.0,
            "lifespan_hours":     10000.0,
            "annual_hours":       500.0,
            "power_watts":        250.0,
            "electricity_rate":   0.13,
            "annual_maintenance": 499.0,
        },
        "ink": {
            "cartridge_capacity_ml": 100.0,
            "cartridge_tare_g":      75.0,
            "ink_density_g_per_ml":  1.0,
            "white_loaded":          "W",
        },
        # Real Eufymake E1 cartridge prices (all color inks + Gloss) by currency.
        "ink_price_by_currency": {
            "EUR": 42.99,
            "GBP": 34.99,
            "USD": 42.99,
            "CAD": 59.99,
            "AUD": 79.99,
        },
    },
    "custom": {
        "label": "Other / Custom",
        "machine": {
            "purchase_price":     2500.0,
            "setup_cost":         0.0,
            "lifespan_hours":     10000.0,
            "annual_hours":       500.0,
            "power_watts":        250.0,
            "electricity_rate":   0.13,
            "annual_maintenance": 499.0,
        },
        "ink": {
            "cartridge_capacity_ml": 100.0,
            "cartridge_tare_g":      75.0,
            "ink_density_g_per_ml":  1.0,
            "white_loaded":          "W",
        },
        # Generic starting prices; the user is expected to adjust these to their
        # own printer's cartridges.
        "ink_price_by_currency": {
            "EUR": 45.0,
            "GBP": 39.0,
            "USD": 49.0,
            "CAD": 65.0,
            "AUD": 79.0,
        },
    },
}

DEFAULT_PRESET = "eufymake_e1"


def get_preset(slug: str) -> dict:
    """Return a preset by slug, falling back to the default preset."""
    return PRINTER_PRESETS.get(slug or "", PRINTER_PRESETS[DEFAULT_PRESET])


def default_ink_price(preset_slug: str, currency_code: str) -> float:
    """Default ink price-per-cartridge for a printer preset + currency."""
    preset = get_preset(preset_slug)
    prices = preset.get("ink_price_by_currency", {})
    return float(prices.get((currency_code or "").upper(),
                            prices.get(DEFAULT_CURRENCY_CODE, 45.0)))


def presets_json() -> list[dict]:
    """Serialisable list of presets for embedding in the wizard template."""
    return [
        {
            "slug": slug,
            "label": p["label"],
            "machine": p["machine"],
            "ink": p["ink"],
            "ink_price_by_currency": p["ink_price_by_currency"],
        }
        for slug, p in PRINTER_PRESETS.items()
    ]
