# Usage: pytest tests/  OR  python tests/test_multicraft.py
# Validates multi-craft schema shaping and the COGS single-craft parity invariant.
"""Tests for multi-craft support (schemas + cogs).

Critical invariant (CI gate): for a single-craft project whose variant ink_usage
equals the project's total ink_usage, the per-variant ink_cost breakdown must sum
to exactly the project ink_cost produced by calculate_cogs. This guards against
regressions when multi-craft is layered on top of the existing COGS engine.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import cogs, models, schemas  # noqa: E402


# ΓöÇΓöÇ Fixtures (hand-built config objects; no DB session needed) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def _ink_cfgs() -> dict:
    return {
        "C": models.InkChannelConfig(channel="C", price_per_cartridge=45.0, cartridge_capacity_ml=100.0),
        "M": models.InkChannelConfig(channel="M", price_per_cartridge=45.0, cartridge_capacity_ml=100.0),
        "Y": models.InkChannelConfig(channel="Y", price_per_cartridge=45.0, cartridge_capacity_ml=100.0),
        "K": models.InkChannelConfig(channel="K", price_per_cartridge=45.0, cartridge_capacity_ml=100.0),
        "W": models.InkChannelConfig(channel="W", price_per_cartridge=60.0, cartridge_capacity_ml=100.0),
        "GL": models.InkChannelConfig(channel="GL", price_per_cartridge=50.0, cartridge_capacity_ml=100.0),
    }


def _machine_cfg() -> models.MachineConfig:
    return models.MachineConfig(
        purchase_price=2500.0, setup_cost=0.0, lifespan_hours=10000.0,
        annual_hours=500.0, power_watts=250.0, electricity_rate=0.13,
        annual_maintenance=499.0,
    )


def _labor_cfg() -> models.LaborConfig:
    return models.LaborConfig(hourly_rate=15.0, overhead_pct=25.0)


# ΓöÇΓöÇ Schema shaping ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def test_parse_crafts_blank_and_invalid_returns_empty():
    assert schemas.parse_crafts("") == []
    assert schemas.parse_crafts(None) == []
    assert schemas.parse_crafts("not json") == []
    assert schemas.parse_crafts('{"not": "a list"}') == []


def test_parse_crafts_skips_malformed_elements():
    crafts = schemas.parse_crafts('[{"variant_name": "A", "craft_mode": "Flat"}, 42, "x"]')
    assert len(crafts) == 1
    assert crafts[0].variant_name == "A"


def test_invalid_craft_mode_coerces_to_flat():
    cv = schemas.CraftVariant(variant_name="Legacy", craft_mode="WhiteΓåÆCMYKΓåÆGloss")
    assert cv.craft_mode == "Flat"


def test_synthesize_primary_craft_from_legacy_fields():
    cv = schemas.synthesize_primary_craft(
        craft_mode="Flat Raised",
        craft_ink_mode="Gloss Raised",
        craft_mode_params_json='{"thickness": 0.3}',
        ink_mode="Gloss Varnish",
        layer_stack_json='[{"channel": "GL", "count": 1}]',
        ink_usage={"GL": 1.5},
        print_time_hours=0.5,
    )
    assert cv.variant_name == "Primary"
    assert cv.craft_mode == "Flat Raised"
    assert cv.craft_ink_mode == "Gloss Raised"
    assert cv.craft_mode_params == {"thickness": 0.3}
    assert cv.layer_stack == [{"channel": "GL", "count": 1}]
    assert cv.ink_usage == {"GL": 1.5}
    assert cv.print_time_hours == 0.5


def test_synthesize_handles_malformed_legacy_json():
    cv = schemas.synthesize_primary_craft(
        craft_mode="Flat", craft_ink_mode="", craft_mode_params_json="{bad",
        ink_mode="CMYK", layer_stack_json="also bad",
    )
    assert cv.craft_mode_params == {}
    assert cv.layer_stack == []


def test_ink_usage_drops_zero_and_negative():
    cv = schemas.CraftVariant(ink_usage={"C": 1.0, "M": 0.0, "Y": -2.0})
    assert cv.ink_usage == {"C": 1.0}


def test_sum_ink_across_crafts():
    crafts = [
        schemas.CraftVariant(variant_name="A", ink_usage={"C": 1.0, "M": 2.0}),
        schemas.CraftVariant(variant_name="B", ink_usage={"C": 0.5, "K": 3.0}),
    ]
    assert schemas.sum_ink_across_crafts(crafts) == {"C": 1.5, "M": 2.0, "K": 3.0}


def test_rolled_up_print_hours():
    crafts = [
        schemas.CraftVariant(variant_name="A", print_time_hours=0.4),
        schemas.CraftVariant(variant_name="B", print_time_hours=0.6),
    ]
    # Project value set ΓåÆ wins.
    assert schemas.rolled_up_print_hours(crafts, 2.0) == 2.0
    # Project value zero ΓåÆ roll up.
    assert schemas.rolled_up_print_hours(crafts, 0.0) == 1.0


# ΓöÇΓöÇ COGS parity invariants ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def test_single_craft_breakdown_matches_project_ink_cost():
    """CI GATE: one variant whose ink == project total ΓåÆ breakdown ink_cost == total."""
    ink_cfgs = _ink_cfgs()
    ink_usage = {"C": 2.0, "M": 2.0, "Y": 2.0, "K": 2.0}

    project_cogs = cogs.calculate_cogs(
        ink_usage=ink_usage, bom_total=0.0,
        machine_cfg=_machine_cfg(), ink_cfgs=ink_cfgs, labor_cfg=_labor_cfg(),
        print_time_hours=1.0, hands_on_hours=0.5, units=1,
    )

    crafts = [schemas.CraftVariant(variant_name="Primary", ink_usage=ink_usage)]
    breakdown = cogs.craft_variant_breakdown(crafts, ink_cfgs)

    assert len(breakdown) == 1
    assert round(breakdown[0]["ink_cost"], 4) == round(project_cogs["ink_cost"], 4)


def test_multi_craft_breakdown_sums_to_project_ink_cost():
    """Two faces with different ink ΓåÆ sum of variant ink_costs == calculate_cogs(summed)."""
    ink_cfgs = _ink_cfgs()
    side_a = {"C": 1.0, "M": 1.0, "Y": 1.0, "K": 1.0, "GL": 2.0}  # Flat Raised + gloss
    side_b = {"C": 0.5, "M": 0.5, "Y": 0.5, "K": 0.5}             # Flat

    crafts = [
        schemas.CraftVariant(variant_name="Side A", craft_mode="Flat Raised",
                             craft_ink_mode="Gloss Raised", ink_usage=side_a),
        schemas.CraftVariant(variant_name="Side B", craft_mode="Flat", ink_usage=side_b),
    ]

    summed = schemas.sum_ink_across_crafts(crafts)
    project_cogs = cogs.calculate_cogs(
        ink_usage=summed, bom_total=0.0,
        machine_cfg=_machine_cfg(), ink_cfgs=ink_cfgs, labor_cfg=_labor_cfg(),
        print_time_hours=1.0, hands_on_hours=0.5, units=1,
    )

    breakdown = cogs.craft_variant_breakdown(crafts, ink_cfgs)
    sum_variant_ink = round(sum(r["ink_cost"] for r in breakdown), 4)

    assert sum_variant_ink == round(project_cogs["ink_cost"], 4)


def test_summed_ink_equals_project_ink_usage_invariant():
    """The dict written to ProjectInkUsage must equal sum of per-craft ink."""
    crafts = [
        schemas.CraftVariant(variant_name="A", ink_usage={"C": 1.2, "W": 3.0}),
        schemas.CraftVariant(variant_name="B", ink_usage={"C": 0.8, "GL": 1.5}),
    ]
    assert schemas.sum_ink_across_crafts(crafts) == {"C": 2.0, "W": 3.0, "GL": 1.5}


# ΓöÇΓöÇ CRUD dual-write integrity (DB-backed, in-memory SQLite) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def _make_db():
    """Isolated in-memory SQLite session, seeded with defaults."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app import crud

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    crud.seed_defaults(db)
    return db


def test_crud_multicraft_sums_ink_into_project_ink_usage():
    """create_project with crafts_json must write the SUMMED ink to ProjectInkUsage
    and sync the legacy craft_mode from crafts[0]."""
    import json as _json
    from app import crud

    db = _make_db()
    crafts = _json.dumps([
        {"variant_name": "Side A", "craft_mode": "Flat Raised", "craft_ink_mode": "Gloss Raised",
         "ink_mode": "Gloss Varnish", "ink_usage": {"C": 1.0, "GL": 2.0}, "print_time_hours": 0.6},
        {"variant_name": "Side B", "craft_mode": "Flat", "ink_mode": "CMYK",
         "ink_usage": {"C": 0.5, "K": 0.5}, "print_time_hours": 0.4},
    ])
    p = crud.create_project(
        db, name="YK", units=10, sell_price_per_unit=25.0,
        print_time_hours=0.0, hands_on_hours=1.0, ink_mode="CMYK",
        print_quality="High", ink_usage={}, bom_items=[], craft_mode="Flat",
        crafts_json=crafts,
    )
    iu = {u.channel: u.ml_used for u in p.ink_usage}
    assert iu == {"C": 1.5, "GL": 2.0, "K": 0.5}          # summed across faces
    assert p.craft_mode == "Flat Raised"                   # legacy synced from crafts[0]
    assert p.has_multiple_crafts is True
    assert abs(p.print_time_hours - 1.0) < 1e-9            # rolled up 0.6 + 0.4
    db.close()


def test_crud_legacy_single_craft_synthesizes_primary():
    """create_project without crafts_json stays single-craft and keeps ink intact."""
    from app import crud

    db = _make_db()
    p = crud.create_project(
        db, name="Legacy", units=1, sell_price_per_unit=5.0,
        print_time_hours=0.5, hands_on_hours=0.2, ink_mode="CMYK",
        print_quality="Standard", ink_usage={"C": 1.0, "M": 1.0}, bom_items=[],
        craft_mode="Flat",
    )
    iu = {u.channel: u.ml_used for u in p.ink_usage}
    assert iu == {"C": 1.0, "M": 1.0}
    assert p.has_multiple_crafts is False
    crafts = schemas.parse_crafts(p.crafts_json)
    assert len(crafts) == 1 and crafts[0].variant_name == "Primary"
    db.close()


# ΓöÇΓöÇ Standalone runner (works without pytest installed) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {fn.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"ERROR {fn.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
