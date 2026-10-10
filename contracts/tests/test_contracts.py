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
        "Rulați python -m contracts.export_schema (prin skill-ul contract-change)")


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
