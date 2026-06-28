# Usage: imported by crud.py, cogs.py, and routers — multi-craft data shaping & validation
# Schema: see AGENTS.md / plan-multiCraftModeSupport — a project carries 1+ CraftVariant
# entries (one per physical face/side). Per-craft *config* lives in Project.crafts_json
# (JSON array); the SUMMED ink across crafts is the authoritative ProjectInkUsage aggregate.
"""Pydantic schemas for InkTrack multi-craft support.

A single UV-print project can have multiple craft modes (e.g. a 2-sided case where
one face is "Flat Raised" and the other "Flat"). Rather than introducing per-craft
ink tables (which would break ``cogs.ink_level_pct`` cartridge tracking), per-craft
configuration is stored as a JSON array in ``Project.crafts_json`` while the summed
ink usage continues to live in ``ProjectInkUsage`` rows.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, field_validator

# Canonical craft modes — must match the wizard's craftModes list.
CRAFT_MODES: tuple[str, ...] = (
    "Flat",
    "Flat Raised",
    "Pattern Texture",
    "Relief Texture",
    "Customize Texture",
)

# Maximum craft variants per project (keeps JSON payloads small; see plan §8).
MAX_CRAFTS_PER_PROJECT = 12


class CraftVariant(BaseModel):
    """One craft face/side within a project.

    ``ink_usage`` is this variant's ml-per-channel contribution. The project-level
    ``ProjectInkUsage`` aggregate is the sum of every variant's ``ink_usage``.
    """

    variant_name: str = Field(default="Primary", min_length=1, max_length=100)
    order_index: int = 0
    craft_mode: str = "Flat"
    craft_ink_mode: str = Field(default="", max_length=50)
    ink_mode: str = Field(default="CMYK", max_length=50)
    craft_mode_params: dict[str, Any] = Field(default_factory=dict)
    layer_stack: list[dict[str, Any]] = Field(default_factory=list)
    ink_usage: dict[str, float] = Field(default_factory=dict)  # {channel: ml} for THIS variant
    print_time_hours: float = 0.0

    @field_validator("craft_mode")
    @classmethod
    def _coerce_craft_mode(cls, v: str) -> str:
        # Be forgiving with legacy/unknown values so backfilled rows never fail validation.
        return v if v in CRAFT_MODES else "Flat"

    @field_validator("ink_usage")
    @classmethod
    def _coerce_ink_usage(cls, v: dict[str, float]) -> dict[str, float]:
        clean: dict[str, float] = {}
        for ch, ml in (v or {}).items():
            try:
                amount = float(ml)
            except (TypeError, ValueError):
                continue
            if amount > 0:
                clean[str(ch)] = amount
        return clean


class ProjectCraftsPayload(BaseModel):
    """Validated envelope for a project's craft list (used at the API boundary)."""

    crafts: list[CraftVariant] = Field(default_factory=list, max_length=MAX_CRAFTS_PER_PROJECT)


def parse_crafts(crafts_json: str | None) -> list[CraftVariant]:
    """Parse a ``crafts_json`` string into validated variants.

    Returns an empty list for blank/invalid input; skips malformed elements rather
    than raising, so a partially-bad row never takes down a read path.
    """
    if not crafts_json:
        return []
    try:
        raw = json.loads(crafts_json)
    except (ValueError, TypeError):
        return []
    if not isinstance(raw, list):
        return []
    variants: list[CraftVariant] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        # Intentionally skip any malformed craft element rather than failing the
        # whole read path; a single bad row must never take down project rendering.
        try:
            variant = CraftVariant(**item)
        except Exception:  # nosec B112 - deliberate defensive skip of bad elements
            continue
        if not item.get("order_index"):
            variant.order_index = i
        variants.append(variant)
    return variants


def synthesize_primary_craft(
    *,
    craft_mode: str | None,
    craft_ink_mode: str | None,
    craft_mode_params_json: str | None,
    ink_mode: str | None,
    layer_stack_json: str | None,
    ink_usage: dict[str, float] | None = None,
    print_time_hours: float = 0.0,
    variant_name: str = "Primary",
) -> CraftVariant:
    """Build a single "Primary" variant from legacy single-craft fields.

    Used for backward compatibility when a project/template has no ``crafts_json``.
    """
    params = _safe_json_dict(craft_mode_params_json)
    layers = _safe_json_list(layer_stack_json)
    return CraftVariant(
        variant_name=variant_name or "Primary",
        order_index=0,
        craft_mode=craft_mode or "Flat",
        craft_ink_mode=craft_ink_mode or "",
        ink_mode=ink_mode or "CMYK",
        craft_mode_params=params,
        layer_stack=layers,
        ink_usage=ink_usage or {},
        print_time_hours=float(print_time_hours or 0.0),
    )


def crafts_to_json(crafts: list[CraftVariant]) -> str:
    """Serialize variants back to a JSON string for storage."""
    return json.dumps([c.model_dump() for c in crafts])


def sum_ink_across_crafts(crafts: list[CraftVariant]) -> dict[str, float]:
    """Sum every variant's ``ink_usage`` into one ``{channel: ml}`` map.

    This is the authoritative project ink usage written to ``ProjectInkUsage``.
    """
    totals: dict[str, float] = {}
    for craft in crafts:
        for channel, ml in (craft.ink_usage or {}).items():
            totals[channel] = round(totals.get(channel, 0.0) + float(ml), 4)
    return totals


def rolled_up_print_hours(crafts: list[CraftVariant], project_print_time_hours: float) -> float:
    """Project print time wins if set; otherwise roll up per-craft times (no double-count)."""
    if project_print_time_hours and project_print_time_hours > 0:
        return float(project_print_time_hours)
    return round(sum(float(c.print_time_hours or 0.0) for c in crafts), 4)


def _safe_json_dict(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except (ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _safe_json_list(raw: str | None) -> list[Any]:
    try:
        value = json.loads(raw or "[]")
    except (ValueError, TypeError):
        return []
    return value if isinstance(value, list) else []
