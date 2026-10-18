"""Public regressions for texture, accounting, inventory and startup fixes."""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import crud, models
from app.database import Base

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
    movement (``quantity_added_total``) — neither total ever decreases. The
    meaningful per-material net effect is therefore ``consumed - added``.
    """
    for b in crud.get_material_inventory_balance(db):
        if b["name"] == name:
            return b["quantity_consumed_total"] - b["quantity_added_total"]
    return None


def _project_args(**overrides):
    return {
        "name": "Original", "units": 2, "sell_price_per_unit": 20.0,
        "print_time_hours": 1.0, "hands_on_hours": 0.5,
        "ink_mode": "CMYK", "print_quality": "Standard",
        "ink_usage": {"C": 5.0}, "bom_items": [],
        **overrides,
    }


def _cost_snapshot(project):
    return {key: getattr(project, key) for key in (
        "ink_cost", "bom_cost", "machine_cost", "labor_cost",
        "overhead_cost", "total_cogs", "cogs_per_unit",
    )}


def test_metadata_edit_preserves_historical_cogs_after_settings_change(db):
    p = crud.create_project(db, **_project_args())
    before = _cost_snapshot(p)
    profit = p.total_profit
    crud.get_ink_configs(db)["C"].price_per_cartridge *= 2
    crud.get_machine_config(db).purchase_price *= 2
    crud.get_labor_config(db).hourly_rate *= 2
    crud.get_labor_config(db).overhead_pct *= 2
    db.commit()
    crud.update_project(db, project_id=p.id, **_project_args(name="Renamed", notes="Edited"))
    assert _cost_snapshot(p) == before
    assert p.total_profit == profit
    crud.update_project(db, project_id=p.id, **_project_args(sell_price_per_unit=30.0))
    assert _cost_snapshot(p) == before
    assert p.total_profit == round(60.0 - before["total_cogs"], 4)


def test_unit_change_preserves_batch_cost_and_updates_cost_per_unit(db):
    p = crud.create_project(db, **_project_args())
    before = _cost_snapshot(p)
    crud.get_ink_configs(db)["C"].price_per_cartridge *= 2
    db.commit()
    crud.update_project(db, project_id=p.id, **_project_args(units=4))
    assert p.total_cogs == before["total_cogs"]
    assert p.cogs_per_unit == round(before["total_cogs"] / 4, 4)


@pytest.mark.parametrize("change", [
    {"ink_usage": {"C": 6.0}},
    {"print_time_hours": 2.0},
    {"hands_on_hours": 1.0},
    {"bom_items": [{"name": "Box", "quantity": 2, "unit_cost": 3.0}]},
])
def test_production_changes_still_recalculate_costs(db, change):
    from app.cogs import calculate_cogs

    p = crud.create_project(db, **_project_args())
    crud.get_ink_configs(db)["C"].price_per_cartridge *= 2
    db.commit()
    args = _project_args(**change)
    crud.update_project(db, project_id=p.id, **args)
    expected = calculate_cogs(
        ink_usage=args["ink_usage"],
        bom_total=sum(i["quantity"] * i["unit_cost"] for i in args["bom_items"]),
        machine_cfg=crud.get_machine_config(db), ink_cfgs=crud.get_ink_configs(db),
        labor_cfg=crud.get_labor_config(db), print_time_hours=args["print_time_hours"],
        hands_on_hours=args["hands_on_hours"], units=args["units"],
    )
    assert _cost_snapshot(p) == expected


@pytest.mark.parametrize("status", ["Completed", "Queued", "Printing"])
def test_update_route_preserves_status_when_omitted(db, status):
    from fastapi import Request
    from app.routers.projects import project_update

    p = crud.create_project(db, **_project_args(status=status))
    completed_at = p.completed_at
    args = _project_args(name="Renamed")
    args["ink_usage_json"] = json.dumps(args.pop("ink_usage"))
    args["bom_json"] = json.dumps(args.pop("bom_items"))
    # Invoke with the same defaults FastAPI supplies for absent form fields.
    import inspect
    for key, parameter in inspect.signature(project_update).parameters.items():
        if key not in args and hasattr(parameter.default, "default"):
            args[key] = parameter.default.default
    args["photo"] = None
    asyncio.run(project_update(p.id, Request({"type": "http"}), db=db, **args))
    assert p.name == "Renamed"
    assert p.status == status
    assert p.completed_at == completed_at


@pytest.mark.parametrize("source", ["bom", "substrate"])
def test_new_library_item_cannot_refund_unrecorded_project_consumption(db, source):
    original = _project_args(
        substrate="Box" if source == "substrate" else "",
        bom_items=[{"name": "Box", "quantity": 4, "unit_cost": 1}] if source == "bom" else [],
    )
    p = crud.create_project(db, **original)
    item = crud.create_material_item(db, name="Box", category="Other", unit_cost=1, unit="pcs")
    crud.create_material_inventory_movement(
        db, material_item_id=item.id, movement_type="in", quantity=10,
    )
    db.commit()
    crud.update_project(db, project_id=p.id, **_project_args())
    assert _consumed(db, "Box") == -10.0
    crud.update_project(db, project_id=p.id, **original)
    assert _consumed(db, "Box") == -10.0 + (2 if source == "substrate" else 4)
    crud.update_project(db, project_id=p.id, **_project_args())
    assert _consumed(db, "Box") == -10.0


def test_material_rename_rolls_back_the_recorded_item_not_its_replacement(db):
    item = crud.create_material_item(db, name="Box", category="Other", unit_cost=1, unit="pcs")
    p = crud.create_project(db, **_project_args(
        bom_items=[{"name": "Box", "quantity": 4, "unit_cost": 1}],
    ))
    crud.update_material_item(db, item.id, name="Renamed Box", category="Other", unit_cost=1, unit="pcs")
    replacement = crud.create_material_item(db, name="Box", category="Other", unit_cost=1, unit="pcs")
    crud.update_project(db, project_id=p.id, **_project_args())
    assert _consumed(db, "Renamed Box") == 0
    assert replacement.quantity_added_total == 0


def test_substrate_and_bom_transitions_use_one_recorded_balance(db):
    crud.create_material_item(db, name="Box", category="Other", unit_cost=1, unit="pcs")
    p = crud.create_project(db, **_project_args(
        substrate="Box", bom_items=[{"name": "Box", "quantity": 4, "unit_cost": 1}],
    ))
    assert _consumed(db, "Box") == 2
    crud.update_project(db, project_id=p.id, **_project_args(
        bom_items=[{"name": "Box", "quantity": 4, "unit_cost": 1}],
    ))
    assert _consumed(db, "Box") == 4
    crud.update_project(db, project_id=p.id, **_project_args())
    assert _consumed(db, "Box") == 0


def test_manual_project_stock_movements_are_not_reversed_by_metadata_edits(db):
    item = crud.create_material_item(db, name="Box", category="Other", unit_cost=1, unit="pcs")
    p = crud.create_project(db, **_project_args(
        bom_items=[{"name": "Box", "quantity": 4, "unit_cost": 1}],
    ))
    crud.create_material_inventory_movement(
        db, material_item_id=item.id, movement_type="out", quantity=1,
        project_id=p.id, notes="Manual extra packaging",
    )
    db.commit()
    crud.update_project(db, project_id=p.id, **_project_args(
        name="Renamed", bom_items=[{"name": "Box", "quantity": 4, "unit_cost": 1}],
    ))
    assert _consumed(db, "Box") == 5


def test_service_retention_keeps_consumption_until_all_affected_channels_replaced(db):
    from app.cogs import ink_channel_used_ml

    now = datetime.utcnow()
    old = now - timedelta(days=400)
    action = crud.log_service_action(
        db, None, "quick_action", "Old clean", {"C": 40, "CLN": 10}, occurred_at=old,
    )
    cutoff = now - timedelta(days=365)
    assert crud.purge_service_actions_older_than(db, cutoff) == 0
    assert ink_channel_used_ml("C", db) == 40
    db.add(models.CartridgeReplacement(channel="C", replaced_at=now))
    db.commit()
    assert crud.purge_service_actions_older_than(db, cutoff) == 0
    assert ink_channel_used_ml("CLN", db) == 10
    db.add(models.CartridgeReplacement(channel="CLN", replaced_at=now))
    db.commit()
    assert crud.purge_service_actions_older_than(db, cutoff) == 1
    assert db.get(models.ServiceAction, action.id) is None
    assert ink_channel_used_ml("C", db) == 0
    assert ink_channel_used_ml("CLN", db) == 0


def test_service_retention_preserves_corrections_boundary_and_bad_legacy_data(db):
    from app.cogs import ink_channel_used_ml

    old = datetime.utcnow() - timedelta(days=400)
    db.add(models.CartridgeReplacement(channel="C", replaced_at=old))
    crud.log_service_action(
        db, None, "quick_action", "Correction", {"C": -5}, occurred_at=old,
    )
    crud.log_service_action(db, None, "quick_action", "No ink", {}, occurred_at=old)
    db.add(models.ServiceAction(
        kind="quick_action", name_snapshot="Malformed", volumes_json="broken",
        total_ml=0, occurred_at=old,
    ))
    db.commit()
    assert crud.purge_service_actions_older_than(db, datetime.utcnow()) == 1
    assert ink_channel_used_ml("C", db) == -5


def test_retention_never_deletes_recent_superseded_actions(db):
    now = datetime.utcnow()
    old = now - timedelta(days=400)
    recent = now - timedelta(days=2)
    crud.log_service_action(db, None, "quick_action", "Old clean", {"C": 2}, occurred_at=old)
    crud.log_service_action(db, None, "quick_action", "Recent clean", {"C": 3}, occurred_at=recent)
    db.add(models.CartridgeReplacement(channel="C", replaced_at=now))
    db.commit()
    assert crud.purge_service_actions_older_than(db, now - timedelta(days=365)) == 1
    assert [a.name_snapshot for a in crud.get_service_actions(db)] == ["Recent clean"]
    assert crud.purge_service_actions_older_than(db, now - timedelta(days=365)) == 0


def test_multicraft_unchanged_usage_preserves_cost_after_price_change(db):
    crafts = [
        {"variant_name": "Front", "ink_usage": {"C": 1}},
        {"variant_name": "Back", "ink_usage": {"C": 2}},
    ]
    args = _project_args(crafts_json=json.dumps(crafts), ink_usage={"C": 3})
    p = crud.create_project(db, **args)
    before = _cost_snapshot(p)
    crud.get_ink_configs(db)["C"].price_per_cartridge *= 2
    db.commit()
    for _ in range(3):
        crud.update_project(db, project_id=p.id, **args)
        assert {u.channel: u.ml_used for u in p.ink_usage} == {"C": 3}
        assert _cost_snapshot(p) == before


def _json_request(payload):
    from fastapi import Request

    async def receive():
        return {"type": "http.request", "body": json.dumps(payload).encode()}

    return Request({"type": "http", "headers": []}, receive)


def _form_request(payload):
    from fastapi import Request
    from urllib.parse import urlencode

    async def receive():
        return {"type": "http.request", "body": urlencode(payload).encode()}

    return Request({"type": "http", "headers": [
        (b"content-type", b"application/x-www-form-urlencoded"),
    ]}, receive)


def _backup_payload(db):
    from app.routers.settings import download_backup

    async def read():
        response = download_backup(db)
        return json.loads(b"".join([chunk async for chunk in response.body_iterator]))

    return asyncio.run(read())


def _restore_payload(db, payload):
    from io import BytesIO
    from fastapi import UploadFile
    from app.routers.settings import upload_restore

    return asyncio.run(upload_restore(
        UploadFile(file=BytesIO(json.dumps(payload).encode()), filename="backup.json"), db,
    ))


def test_legacy_backup_preserves_settings_it_did_not_export(db):
    crud.update_feature_config(db, printer_profile="custom", multi_craft_enabled=False)
    crud.update_automation_config(db, enabled=False, run_time="09:15")
    payload = _backup_payload(db)
    payload["tables"].pop("feature_config")
    payload["tables"].pop("automation_config")
    response = _restore_payload(db, payload)
    assert response.status_code == 200, response.body
    assert crud.get_printer_profile(db) == "custom"
    assert crud.get_feature_config(db).multi_craft_enabled is False
    assert crud.get_automation_config(db).auto_maintenance_log_time == "09:15"
    assert crud.get_automation_config(db).auto_maintenance_log_enabled is False


@pytest.mark.parametrize("tables", [None, {}, [], {"feature_config": {}}, {"feature_config": [None]}])
def test_invalid_backup_tables_do_not_delete_existing_data(db, tables):
    p = crud.create_project(db, **_project_args())
    response = _restore_payload(db, {"version": "1.0", "tables": tables})
    assert response.status_code == 400
    assert crud.get_project(db, p.id) is not None


def test_creating_installed_lot_resets_baseline_once(db):
    from app.cogs import ink_channel_used_ml

    old = crud.create_cartridge_inventory_lot(db, channel="C", quantity_ml=100, is_in_use=True)
    action = crud.log_service_action(db, None, "quick_action", "Clean", {"C": 10})
    action.occurred_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()
    new = crud.create_cartridge_inventory_lot(db, channel="C", quantity_ml=100, is_in_use=True)
    assert not old.is_in_use
    assert new.is_in_use
    assert ink_channel_used_ml("C", db) == 0
    replacement = db.query(models.CartridgeReplacement).order_by(
        models.CartridgeReplacement.replaced_at.desc(),
    ).first()
    assert replacement.replaced_at == new.installed_at
    count = db.query(models.CartridgeReplacement).count()
    crud.set_cartridge_lot_in_use(db, new.id, True)
    assert db.query(models.CartridgeReplacement).count() == count
    crud.log_service_action(db, None, "quick_action", "New clean", {"C": 2})
    assert ink_channel_used_ml("C", db) == 2


def test_creating_spare_lot_does_not_reset_baseline(db):
    from app.cogs import ink_channel_used_ml

    crud.log_service_action(db, None, "quick_action", "Clean", {"C": 10})
    crud.create_cartridge_inventory_lot(db, channel="C", quantity_ml=100)
    assert ink_channel_used_ml("C", db) == 10
    assert db.query(models.CartridgeReplacement).count() == 0


@pytest.mark.parametrize("name,other", [("Coaster_A", "CoasterXA"), ("100% Cotton", "100X Cotton")])
def test_material_names_are_literal_case_insensitive_matches(db, name, other):
    unrelated = crud.create_material_item(db, name=other, category="Other", unit_cost=1, unit="pcs")
    assert crud.get_material_item_by_name(db, name) is None
    item = crud.create_material_item(db, name=name, category="Other", unit_cost=1, unit="pcs")
    assert crud.get_material_item_by_name(db, f" {name.lower()} ").id == item.id
    crud.create_project(db, **_project_args(
        bom_items=[{"name": name, "quantity": 2, "unit_cost": 1}],
    ))
    assert item.quantity_consumed_total == 2
    assert unrelated.quantity_consumed_total == 0


def test_factory_reset_clears_material_balances_and_preserves_library_settings(db):
    from sqlalchemy import text

    db.execute(text("PRAGMA foreign_keys=ON"))
    material = crud.create_material_item(db, name="Box", category="Other", unit_cost=2, unit="pcs")
    crud.create_material_inventory_movement(db, material_item_id=material.id,
                                          movement_type="in", quantity=10)
    crud.create_project(db, **_project_args(
        bom_items=[{"name": "Box", "quantity": 3, "unit_cost": 2}],
    ))
    crud.update_feature_config(db, printer_profile="custom")
    crud.factory_reset(db)
    db.expire_all()
    assert db.query(models.MaterialInventoryMovement).count() == 0
    assert db.query(models.Project).count() == 0
    assert (material.quantity_added_total, material.quantity_consumed_total) == (0, 0)
    assert (material.name, material.unit_cost) == ("Box", 2)
    assert crud.get_printer_profile(db) == "custom"


@pytest.mark.parametrize("project_type", ["gift", "sample", "internal", "commercial"])
def test_duplicate_preserves_project_metadata_but_starts_as_draft(db, project_type):
    crafts = [{"variant_name": "Front", "ink_usage": {"C": 1}},
              {"variant_name": "Back", "ink_usage": {"GL": 2}}]
    original = crud.create_project(db, **_project_args(
        project_type=project_type, white_choke_mm=0, include_preprime=False,
        status="Completed", crafts_json=json.dumps(crafts),
    ))
    duplicate = crud.duplicate_project(db, original.id)
    assert duplicate.project_type == project_type
    assert duplicate.white_choke_mm == 0
    assert duplicate.include_preprime is False
    assert duplicate.status == "Draft"
    assert duplicate.completed_at is None
    assert json.loads(duplicate.crafts_json) == json.loads(original.crafts_json)
    assert {u.channel: u.ml_used for u in duplicate.ink_usage} == {"C": 1, "GL": 2}


@pytest.mark.parametrize("white", ["W", "FW"])
def test_automatic_flash_clean_charges_loaded_white(db, white):
    from app.maintenance_scheduler import run_auto_flash_clean_for_time

    crud.get_ink_global_config(db).white_loaded = white
    db.commit()
    run_auto_flash_clean_for_time(db, datetime.utcnow())
    action = db.query(models.ServiceAction).one()
    volumes = json.loads(action.volumes_json)
    assert volumes[white] > 0
    assert volumes.get("W" if white == "FW" else "FW", 0) == 0


def test_scheduled_maintenance_preserves_liquid_only_presets(db):
    from app.maintenance_scheduler import run_auto_maintenance_for_time

    crud.get_ink_global_config(db).white_loaded = "FW"
    db.commit()
    run_auto_maintenance_for_time(db, datetime.utcnow())
    volumes = json.loads(db.query(models.ServiceAction).one().volumes_json)
    assert "W" not in volumes and "FW" not in volumes
    assert volumes["CLN"] > 0 and volumes["ML"] > 0


def test_backup_restore_preserves_inventory_relationships_with_foreign_keys(db):
    from sqlalchemy import text

    db.execute(text("PRAGMA foreign_keys=ON"))
    assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
    material = crud.create_material_item(db, name="Box", category="Other", unit_cost=2, unit="pcs")
    p = crud.create_project(db, **_project_args(
        bom_items=[{"name": material.name, "quantity": 3, "unit_cost": 2}],
    ))
    project_id, material_id = p.id, material.id
    response = _restore_payload(db, _backup_payload(db))
    assert response.status_code == 200, response.body
    movement = db.query(models.MaterialInventoryMovement).one()
    assert movement.project_id == project_id
    assert movement.material_item_id == material_id
    assert movement.material_item.quantity_consumed_total == 3
    assert len(movement.project.bom_items) == 1


@pytest.mark.parametrize("multi", [False, True])
@pytest.mark.parametrize("preprime", [False, True])
def test_actual_wizard_payload_and_preview_match_saved_cogs(db, multi, preprime):
    from pathlib import Path
    import subprocess

    cfgs = crud.get_ink_configs(db)
    cfgs["C"].cartridge_capacity_ml = 125
    cfgs["FW"].cartridge_capacity_ml = 290
    crud.get_ink_global_config(db).white_loaded = "FW"
    db.commit()
    settings = crud.get_settings_json(db)
    script = r"""
const fs = require('node:fs'), vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const template = fs.readFileSync(process.argv[1], 'utf8');
const nodes = {
  'wizard-settings-json': { textContent: JSON.stringify(input.settings) },
  'wizard-form': { submit() {} },
};
const context = vm.createContext({
  document: { getElementById: id => nodes[id] ??= {} },
});
vm.runInContext(template.match(/<script>\s*([\s\S]*?)<\/script>/)[1], context);
const w = context.wizardData();
w.setInkMode('White>CMYK');
w.inkUsage = {C: 2, FW: 3, GL: 90};
w.units = 2; w.printH = 1; w.handsM = 30;
w.includePreprime = input.preprime;
w.bomItems = [{name: 'Box', qty: 0, unitCost: 10}, {name: 'Wrap', qty: 2, unitCost: 3}];
w.multiCraftEnabled = input.multi;
const face = w.makeExtraCraft(0);
face.inkMode = 'Gloss Varnish'; face.inkUsage = {GL: 4, C: 80};
w.extraCrafts = [face];
w.submit();
console.log(JSON.stringify({
  ink_usage: JSON.parse(nodes.ink_usage_json.value),
  bom_items: JSON.parse(nodes.bom_json.value),
  crafts_json: nodes.f_crafts_json.value,
  ink_cost: w.inkCost, total_cogs: w.totalCogs, cogs_per_unit: w.cogsPerUnit,
}));
"""
    result = subprocess.run(
        ["node", "-e", script, str(Path(__file__).resolve().parents[1] /
                                   "app" / "templates" / "projects" / "wizard.html")],
        input=json.dumps({"settings": settings, "multi": multi, "preprime": preprime}),
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(result.stdout)
    p = crud.create_project(db, **_project_args(
        ink_mode="White>CMYK", ink_usage=payload["ink_usage"],
        bom_items=payload["bom_items"], crafts_json=payload["crafts_json"],
        include_preprime=preprime,
    ))
    assert p.ink_cost == pytest.approx(payload["ink_cost"], abs=0.0001)
    assert p.total_cogs == pytest.approx(payload["total_cogs"], abs=0.0001)
    assert p.cogs_per_unit == pytest.approx(payload["cogs_per_unit"], abs=0.0001)
    assert p.bom_items[0].quantity == 0
    assert {u.channel: u.ml_used for u in p.ink_usage} == (
        {"C": 2, "FW": 3, "GL": 4} if multi else {"C": 2, "FW": 3}
    )
