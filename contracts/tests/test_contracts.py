"""Contractele: exemplele sunt valide, schema exportată e la zi, datele invalide sunt respinse."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from contracts.export_schema import EXAMPLES_DIR, schema_path, schema_text
from contracts.models import ALL_MODELS, PositionMessage
from contracts.validate import validate_data


@pytest.mark.parametrize("name", sorted(ALL_MODELS))
def test_example_is_valid(name):
    data = json.loads((EXAMPLES_DIR / f"{name}.json").read_text(encoding="utf-8"))
    assert validate_data(data, name) == []
    ALL_MODELS[name].model_validate(data)


@pytest.mark.parametrize("name", sorted(ALL_MODELS))
def test_exported_schema_is_up_to_date(name):
    assert schema_path(name).read_text(encoding="utf-8") == schema_text(name), (
        "Run python -m contracts.export_schema (through the contract-change skill)")


@pytest.mark.parametrize("name", sorted(ALL_MODELS))
def test_roundtrip(name):
    data = json.loads((EXAMPLES_DIR / f"{name}.json").read_text(encoding="utf-8"))
    obj = ALL_MODELS[name].model_validate(data)
    again = ALL_MODELS[name].model_validate(obj.model_dump(mode="json"))
    assert again == obj


def test_invalid_mmsi_rejected():
    data = json.loads((EXAMPLES_DIR / "PositionMessage.json").read_text(encoding="utf-8"))
    data["mmsi"] = "12345"
    with pytest.raises(ValidationError):
        PositionMessage.model_validate(data)
    assert validate_data(data, "PositionMessage")


def test_unknown_field_rejected():
    data = json.loads((EXAMPLES_DIR / "SensorEvent.json").read_text(encoding="utf-8"))
    data["surpriza"] = 1
    assert validate_data(data, "SensorEvent")


def test_live_timeline_with_area_and_coverage():
    # Câmpuri aditive pentru datele reale: fișierele vechi (fără ele) rămân valide, vezi exemplele.
    data = json.loads((EXAMPLES_DIR / "Timeline.json").read_text(encoding="utf-8"))
    data.update(mode="live", simulated=False, area_name="Varna sector, Bulgarian Black Sea",
                area_assets="assets/areas/varna", ais_coverage=[[43.15, 28.0, 43.2, 28.05]])
    assert validate_data(data, "Timeline") == []
    data["mode"] = "realtime"
    assert validate_data(data, "Timeline")


def test_area_assets_dir_and_files():
    from contracts.assets import area_assets_dir, area_infrastructure, load_patrol_units
    from contracts.runtime import ASSETS_DIR, load_config

    cfg = load_config()
    assert area_assets_dir(cfg) == ASSETS_DIR                       # scenariul demo: assets/
    live = dict(cfg, active_area="varna")
    d = area_assets_dir(live)
    assert d == ASSETS_DIR / "areas" / "varna"
    feats = area_infrastructure(live)
    # Aceleași câmpuri obligatorii ca assets/infrastructure.geojson; poziții aproximative.
    assert feats and all(f.approximate and "(approx.)" in f.name for f in feats)
    assert any(f.protected for f in feats) and any(f.exclusion and f.geom_type == "Polygon" for f in feats)
    units = load_patrol_units(d / "patrol_units.json")
    assert units and all(u.simulated for u in units)
    assert area_assets_dir(dict(cfg, active_area="constanta")) == ASSETS_DIR   # zonă fără assets proprii
