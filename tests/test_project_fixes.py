# Usage: pytest tests/  OR  python -m pytest tests/test_project_fixes.py
# Functional regression tests for the 2026-07-17 project-wizard fixes:
#   #113 pre-prime + white-choke edit round-trip (and COGS stability)
#   #115 per-printer-profile print-quality options
#   #116 BOM <-> Materials-library link (prefill source, add-to-library, consumption)
"""These exercise the real crud/cogs/model code against a fresh in-memory
SQLite database (schema created from the SQLAlchemy models, seeded via
crud.seed_defaults), so they validate behaviour end-to-end at the data layer ΓÇö
not just that migrations run. PostgreSQL-specific migration DDL is validated
separately (see the review doc: applied on DEV PostgreSQL at deploy time)."""
from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import crud, models  # noqa: E402
from app.database import Base  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    crud.seed_defaults(session)
    try:
        yield session
    finally:
        session.close()


def _consumed(db, name):
    """Net stock drawn down by projects for a material.

    The inventory ledger is append-only: consumption adds an ``out`` movement
    (``quantity_consumed_total``) and a rollback adds an offsetting ``in``
    movement (``quantity_added_total``) ΓÇö neither total ever decreases. The
    meaningful per-material net effect is therefore ``consumed - added``.
    """
    for b in crud.get_material_inventory_balance(db):
        if b["name"] == name:
            return b["quantity_consumed_total"] - b["quantity_added_total"]
    return None


# ΓöÇΓöÇ #113 pre-prime + choke round-trip / COGS stability ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def test_choke_zero_and_preprime_off_round_trip(db):
    p = crud.create_project(
        db, name="P", units=1, sell_price_per_unit=10.0,
        print_time_hours=1.0, hands_on_hours=0.5, ink_mode="CMYK",
        print_quality="Standard", ink_usage={"C": 5.0, "M": 3.0}, bom_items=[],
        white_choke_mm=0.0, include_preprime=False,
    )
    assert p.white_choke_mm == 0.0
    assert p.include_preprime is False

    back = crud.get_project(db, p.id)
    assert back.white_choke_mm == 0.0
    assert back.include_preprime is False


def test_unrelated_edit_preserves_choke_preprime_and_cogs(db):
    """The reported #113 symptom: an edit that changes something other than ink
    must NOT alter the stored ink_cost / COGS or the choke/pre-prime state."""
    p = crud.create_project(
        db, name="P", units=1, sell_price_per_unit=10.0,
        print_time_hours=1.0, hands_on_hours=0.5, ink_mode="CMYK",
        print_quality="Standard", ink_usage={"C": 5.0, "M": 3.0}, bom_items=[],
        white_choke_mm=0.0, include_preprime=False,
    )
    ink_cost_before = p.ink_cost
    cogs_before = p.total_cogs

    # Rename only; caller passes back the saved choke/pre-prime (as the router does).
    crud.update_project(
        db, project_id=p.id, name="Renamed", units=1, sell_price_per_unit=10.0,
        print_time_hours=1.0, hands_on_hours=0.5, ink_mode="CMYK",
        print_quality="Standard", ink_usage={"C": 5.0, "M": 3.0}, bom_items=[],
        white_choke_mm=0.0, include_preprime=False,
    )
    after = crud.get_project(db, p.id)
    assert after.name == "Renamed"
    assert after.white_choke_mm == 0.0
    assert after.include_preprime is False
    assert after.ink_cost == ink_cost_before
    assert after.total_cogs == cogs_before


def test_preprime_flag_does_not_change_cogs(db):
    """Confirms the documented invariant: include_preprime is display-only and
    never folded into stored ink_cost."""
    common = dict(
        units=1, sell_price_per_unit=10.0, print_time_hours=1.0,
        hands_on_hours=0.5, ink_mode="CMYK", print_quality="Standard",
        ink_usage={"C": 5.0, "M": 3.0}, bom_items=[],
    )
    on = crud.create_project(db, name="on", include_preprime=True, **common)
    off = crud.create_project(db, name="off", include_preprime=False, **common)
    assert on.ink_cost == off.ink_cost


# ΓöÇΓöÇ #115 per-profile print-quality options ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def test_eufymake_profile_excludes_ultra():
    assert "Ultra" not in models.qualities_for_profile("eufymake_e1")
    assert models.qualities_for_profile("eufymake_e1") == ["Draft", "Standard", "High"]


def test_custom_profile_keeps_ultra():
    assert "Ultra" in models.qualities_for_profile("custom")


def test_unknown_profile_keeps_full_list():
    assert models.qualities_for_profile("") == models.PRINT_QUALITIES
    assert models.qualities_for_profile("nonexistent") == models.PRINT_QUALITIES


def test_printer_profile_persists(db):
    assert crud.get_printer_profile(db) == "eufymake_e1"
    crud.update_feature_config(db, printer_profile="custom")
    assert crud.get_printer_profile(db) == "custom"


def test_update_feature_config_partial_kwargs(db):
    """Setting only one field must not clobber the other."""
    crud.update_feature_config(db, printer_profile="custom")
    before_multi = crud.get_feature_config(db).multi_craft_enabled
    crud.update_feature_config(db, multi_craft_enabled=not before_multi)
    assert crud.get_printer_profile(db) == "custom"  # unchanged
    assert crud.get_feature_config(db).multi_craft_enabled == (not before_multi)


# ΓöÇΓöÇ #116 BOM <-> Materials library ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def test_bom_consumes_matching_library_material(db):
    crud.create_material_item(db, name="Ceramic Coaster", category="Substrate", unit_cost=0.5, unit="pcs")
    crud.create_project(
        db, name="Mug", units=1, sell_price_per_unit=10.0, print_time_hours=1.0,
        hands_on_hours=0.5, ink_mode="CMYK", print_quality="Standard",
        ink_usage={"C": 2.0},
        bom_items=[{"name": "Ceramic Coaster", "quantity": 4, "unit": "pcs", "unit_cost": 0.5}],
    )
    assert _consumed(db, "Ceramic Coaster") == 4.0


def test_bom_free_text_no_library_no_movement(db):
    crud.create_project(
        db, name="Mug", units=1, sell_price_per_unit=10.0, print_time_hours=1.0,
        hands_on_hours=0.5, ink_mode="CMYK", print_quality="Standard",
        ink_usage={"C": 2.0},
        bom_items=[{"name": "Random Thing", "quantity": 3, "unit": "pcs", "unit_cost": 1.0}],
        bom_add_to_library=False,
    )
    assert crud.get_material_item_by_name(db, "Random Thing") is None
    assert crud.get_material_inventory_movements(db) == []


def test_bom_add_to_library_creates_and_consumes(db):
    crud.create_project(
        db, name="Mug", units=1, sell_price_per_unit=10.0, print_time_hours=1.0,
        hands_on_hours=0.5, ink_mode="CMYK", print_quality="Standard",
        ink_usage={"C": 2.0},
        bom_items=[{"name": "Gift Box", "quantity": 2, "unit": "pcs", "unit_cost": 1.2}],
        bom_add_to_library=True,
    )
    assert crud.get_material_item_by_name(db, "Gift Box") is not None
    assert _consumed(db, "Gift Box") == 2.0


def test_bom_add_to_library_dedupes_case_insensitive(db):
    """Two lines, same name differing only by case, must create ONE library item."""
    crud.create_project(
        db, name="Mug", units=1, sell_price_per_unit=10.0, print_time_hours=1.0,
        hands_on_hours=0.5, ink_mode="CMYK", print_quality="Standard",
        ink_usage={"C": 2.0},
        bom_items=[
            {"name": "Sticker", "quantity": 1, "unit": "pcs", "unit_cost": 0.1},
            {"name": "sticker", "quantity": 2, "unit": "pcs", "unit_cost": 0.1},
        ],
        bom_add_to_library=True,
    )
    matches = [m for m in crud.get_material_items(db) if m.name.lower() == "sticker"]
    assert len(matches) == 1
    # Both lines aggregate against the single item for consumption (1 + 2 = 3).
    assert _consumed(db, matches[0].name) == 3.0


def test_bom_edit_reconciles_consumption(db):
    crud.create_material_item(db, name="Coaster", category="Substrate", unit_cost=0.5, unit="pcs")
    p = crud.create_project(
        db, name="Mug", units=1, sell_price_per_unit=10.0, print_time_hours=1.0,
        hands_on_hours=0.5, ink_mode="CMYK", print_quality="Standard",
        ink_usage={"C": 2.0},
        bom_items=[{"name": "Coaster", "quantity": 4, "unit": "pcs", "unit_cost": 0.5}],
    )
    assert _consumed(db, "Coaster") == 4.0
    # Increase 4 -> 7: net consumed must settle at 7.
    crud.update_project(
        db, project_id=p.id, name="Mug", units=1, sell_price_per_unit=10.0,
        print_time_hours=1.0, hands_on_hours=0.5, ink_mode="CMYK",
        print_quality="Standard", ink_usage={"C": 2.0},
        bom_items=[{"name": "Coaster", "quantity": 7, "unit": "pcs", "unit_cost": 0.5}],
    )
    assert _consumed(db, "Coaster") == 7.0


def test_bom_line_removal_rolls_back(db):
    crud.create_material_item(db, name="Coaster", category="Substrate", unit_cost=0.5, unit="pcs")
    p = crud.create_project(
        db, name="Mug", units=1, sell_price_per_unit=10.0, print_time_hours=1.0,
        hands_on_hours=0.5, ink_mode="CMYK", print_quality="Standard",
        ink_usage={"C": 2.0},
        bom_items=[{"name": "Coaster", "quantity": 4, "unit": "pcs", "unit_cost": 0.5}],
    )
    # Remove the line entirely: net consumed must return to 0 (offsetting "in").
    crud.update_project(
        db, project_id=p.id, name="Mug", units=1, sell_price_per_unit=10.0,
        print_time_hours=1.0, hands_on_hours=0.5, ink_mode="CMYK",
        print_quality="Standard", ink_usage={"C": 2.0}, bom_items=[],
    )
    assert _consumed(db, "Coaster") == 0.0


def test_bom_matching_substrate_not_double_counted(db):
    """A BOM line whose name equals the project substrate must not be consumed
    twice (substrate sync handles the substrate; BOM sync excludes it)."""
    crud.create_material_item(db, name="Ceramic", category="Substrate", unit_cost=0.5, unit="pcs")
    crud.create_project(
        db, name="Mug", units=3, sell_price_per_unit=10.0, print_time_hours=1.0,
        hands_on_hours=0.5, ink_mode="CMYK", print_quality="Standard",
        ink_usage={"C": 2.0}, substrate="Ceramic",
        bom_items=[{"name": "Ceramic", "quantity": 4, "unit": "pcs", "unit_cost": 0.5}],
    )
    # Substrate consumes units (3); BOM excludes the substrate name -> total 3, not 7.
    assert _consumed(db, "Ceramic") == 3.0


def test_status_only_edit_does_not_reconsume_bom(db):
    """Editing only the status (Draft -> Completed), with the BOM unchanged, must
    NOT draw down stock again (net stays at the original quantity)."""
    crud.create_material_item(db, name="Coaster", category="Substrate", unit_cost=0.5, unit="pcs")
    p = crud.create_project(
        db, name="Mug", units=1, sell_price_per_unit=10.0, print_time_hours=1.0,
        hands_on_hours=0.5, ink_mode="CMYK", print_quality="Standard",
        ink_usage={"C": 2.0},
        bom_items=[{"name": "Coaster", "quantity": 4, "unit": "pcs", "unit_cost": 0.5}],
        status="Draft",
    )
    assert _consumed(db, "Coaster") == 4.0
    crud.update_project(
        db, project_id=p.id, name="Mug", units=1, sell_price_per_unit=10.0,
        print_time_hours=1.0, hands_on_hours=0.5, ink_mode="CMYK",
        print_quality="Standard", ink_usage={"C": 2.0},
        bom_items=[{"name": "Coaster", "quantity": 4, "unit": "pcs", "unit_cost": 0.5}],
        status="Completed",
    )
    assert _consumed(db, "Coaster") == 4.0  # unchanged, not 8


def test_add_to_library_and_consume_are_atomic_on_failure(db, monkeypatch):
    """If the movement write fails mid-save, the opt-in library creation must not
    persist either (single project transaction; nothing committed)."""
    import app.crud as crud_mod

    before = {m.name for m in crud.get_material_items(db)}

    # Force the consumption step to blow up after _add_bom_items_to_library ran.
    def _boom(*args, **kwargs):
        raise RuntimeError("simulated movement failure")

    monkeypatch.setattr(crud_mod, "_sync_project_bom_inventory", _boom)

    with pytest.raises(RuntimeError):
        crud.create_project(
            db, name="Mug", units=1, sell_price_per_unit=10.0, print_time_hours=1.0,
            hands_on_hours=0.5, ink_mode="CMYK", print_quality="Standard",
            ink_usage={"C": 2.0},
            bom_items=[{"name": "Brand New Widget", "quantity": 1, "unit": "pcs", "unit_cost": 1.0}],
            bom_add_to_library=True,
        )
    db.rollback()

    after = {m.name for m in crud.get_material_items(db)}
    assert after == before  # the new library item was NOT committed
    assert crud.get_material_item_by_name(db, "Brand New Widget") is None
