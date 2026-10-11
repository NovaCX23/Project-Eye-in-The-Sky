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


def test_slow_normal_traffic_is_present_and_never_flagged(cfg):
    """Traulerele și pilotina sunt trafic lent NORMAL: nu trebuie să producă niciun eveniment AIS."""
    from datetime import timedelta

    import pandas as pd

    from contracts.assets import in_exclusion_zone
    from contracts.runtime import parse_time
    from detect.ais_rules import run_all

    g = cfg["generator"]
    df = generate(cfg["scenario"]["seeds"]["tuning"], cfg, load_scenario())
    types = df.groupby("mmsi")["ship_type"].first()
    assert (types == "fishing").sum() == g["n_fishing"]
    assert (types == "pilot").sum() == g["n_pilot"]
    fishing = df[df["ship_type"] == "fishing"]
    assert fishing["sog_kn"].mean() > cfg["detect"]["loitering"]["max_mean_sog_kn"]
    pilot = df[df["ship_type"] == "pilot"]
    assert all(in_exclusion_zone(r.lat, r.lon) for r in pilot.itertuples() if r.sog_kn <= g["pilot_hold_sog_kn"] * 2)

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    now = parse_time(cfg["scenario"]["start"]) + timedelta(minutes=cfg["scenario"]["duration_min"])
    slow = set(types[types.isin(["fishing", "pilot"])].index)
    assert [e for e in run_all(df, now, cfg) if e.mmsi in slow] == []


def test_random_anomalies_only_on_allowed_ship_types(demo_out, cfg):
    gt = read_json(demo_out / "ground_truth.json")
    df = load_ais(demo_out / "ais.csv")
    types = df.groupby("mmsi")["ship_type"].first()
    for a in gt["anomalies"]:
        if a["origin"] == "random":
            assert types[a["mmsi"]] in cfg["injector"]["random_ship_types"]
