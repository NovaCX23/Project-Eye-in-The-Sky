"""Scenariul demo produce alerta așteptată, validă față de schemă."""

from __future__ import annotations

from contracts.runtime import read_json
from contracts.validate import validate_data
from data.generate import load_scenario


def test_timeline_matches_schema(demo_out):
    assert validate_data(read_json(demo_out / "timeline.json"), "Timeline") == []


def test_dark_vessel_alert(demo_out):
    sc = load_scenario()
    tl = read_json(demo_out / "timeline.json")
    alert = next(a for a in tl["alerts"] if a["mmsi"] == sc["dark_vessel"]["mmsi"])
    codes = {f["code"] for f in alert["factors"]}
    assert {"ais_gap", "speed_inconsistency", "near_infrastructure"} <= codes
    assert {"acoustic_lowfreq", "fibre_vibration", "correlated_vessel"} <= codes
    assert any(h["level"] == "critical" for h in alert["history"])
    assert alert["recommendation"] is not None
    assert alert["simulated"] is True
    assert "prea lent" in alert["explanation"]


def test_loiter_vessel_alert(demo_out):
    sc = load_scenario()
    tl = read_json(demo_out / "timeline.json")
    alert = next(a for a in tl["alerts"] if a["mmsi"] == sc["loiter_vessel"]["mmsi"])
    assert alert["alert_type"] == "loitering"
    assert sc["dark_vessel"]["mmsi"] in alert["related_mmsis"]
