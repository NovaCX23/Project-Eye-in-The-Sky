"""Generator determinist; injectorul scrie ground truth pentru scenariul demo."""

from __future__ import annotations

from contracts.runtime import read_json
from contracts.validate import validate_data
from data.generate import generate, load_scenario
from data.loader import load_ais


def test_generator_is_deterministic(cfg):
    sc = load_scenario()
    a = generate(7, cfg, sc)
    b = generate(7, cfg, sc)
    c = generate(8, cfg, sc)
    assert a.equals(b)
    assert not a.equals(c)


def test_demo_ground_truth_and_outputs(demo_out):
    sc = load_scenario()
    gt = read_json(demo_out / "ground_truth.json")
    demo = {(a["type"], a["mmsi"]) for a in gt["anomalies"] if a["origin"] == "demo"}
    assert demo == {("ais_gap", sc["dark_vessel"]["mmsi"]), ("loitering", sc["loiter_vessel"]["mmsi"])}
    for ev in read_json(demo_out / "fibre_events.json"):
        assert ev["simulated"] is True
        assert validate_data(ev, "SensorEvent") == []
    df = load_ais(demo_out / "ais.csv", validate=True)
    assert df["simulated"].all()
