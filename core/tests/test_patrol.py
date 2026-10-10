"""Unitățile de patrulare: mișcare pe rută, trimitere spre alertă, ETA din poziția curentă, repartizare pe priorități."""

from __future__ import annotations

from datetime import timedelta

import pytest

from contracts.geo import haversine_km
from contracts.runtime import parse_time, read_json
from core import patrol
from data.generate import load_scenario

OFFSHORE = (44.10, 29.65)


@pytest.fixture
def t0(cfg):
    return parse_time(cfg["scenario"]["start"])


def _cfg(cfg: dict, exclusive: bool) -> dict:
    return {**cfg, "patrol": {**cfg["patrol"], "one_alert_per_unit": exclusive}}


def test_units_patrol_their_route(cfg, t0):
    for plan in patrol.load_plans():
        at_start = patrol.state_at(plan, t0, [], t0)
        later = patrol.state_at(plan, t0 + timedelta(minutes=30), [], t0)
        assert (at_start.lat, at_start.lon) == pytest.approx(plan.route[0])
        moved = haversine_km(at_start.lat, at_start.lon, later.lat, later.lon)
        assert moved == pytest.approx(plan.patrol_kn * 1.852 / 2, rel=0.05)   # 30 min la viteza de patrulare


def test_dispatched_unit_closes_in_and_stays_on_scene(cfg, t0):
    plan = patrol.load_plans()[0]
    target = OFFSHORE
    legs = [patrol.Leg(t0 + timedelta(minutes=60), *target, "alr-x")]
    etas = []
    for minutes in (60, 75, 90, 300):
        s = patrol.state_at(plan, t0 + timedelta(minutes=minutes), legs, t0)
        etas.append(haversine_km(s.lat, s.lon, *target))
    assert etas[0] > etas[1] > etas[2]
    assert etas[-1] == pytest.approx(0.0, abs=1e-6)


def test_one_unit_per_alert_in_priority_order(cfg, t0):
    cands = [("a1", *OFFSHORE, "critical"), ("a2", *OFFSHORE, "critical"), ("a3", *OFFSHORE, "high")]
    recs = patrol.assign(cands, _cfg(cfg, True), {}, t0, {})
    units = [recs[a].unit_id for a in ("a1", "a2", "a3")]
    assert len(set(units)) == 3
    assert units[0] == patrol.recommend(*OFFSHORE, "critical", cfg, t0).unit_id   # prima primește cea mai apropiată


def test_more_alerts_than_units(cfg, t0):
    n = len(patrol.load_plans())
    cands = [(f"a{i}", *OFFSHORE, "critical") for i in range(n + 1)]
    recs = patrol.assign(cands, _cfg(cfg, True), {}, t0, {})
    assert len(recs) == n
    assert f"a{n}" not in recs


def test_dispatched_unit_stays_with_its_alert(cfg, t0):
    c, dispatched, legs = _cfg(cfg, True), {}, {}
    first = patrol.assign([("old", *OFFSHORE, "high")], c, dispatched, t0, legs)
    later = patrol.assign([("new", *OFFSHORE, "critical"), ("old", *OFFSHORE, "high")], c, dispatched,
                          t0 + timedelta(minutes=10), legs)
    assert later["old"].unit_id == first["old"].unit_id
    assert later["new"].unit_id != first["old"].unit_id
    assert later["old"].eta_min < first["old"].eta_min          # unitatea trimisă s-a apropiat
    assert [g.alert_id for g in legs[first["old"].unit_id]] == ["old"]


def test_dispatched_unit_follows_a_moving_alert(cfg, t0):
    c, dispatched, legs = _cfg(cfg, True), {}, {}
    unit = patrol.assign([("a", *OFFSHORE, "critical")], c, dispatched, t0, legs)["a"].unit_id
    moved = (OFFSHORE[0] + 0.01, OFFSHORE[1])                    # centrul alertei s-a mutat ~1 km
    patrol.assign([("a", *moved, "critical")], c, dispatched, t0 + timedelta(minutes=5), legs)
    plan = next(p for p in patrol.load_plans() if p.unit_id == unit)
    s = patrol.state_at(plan, t0 + timedelta(hours=6), legs[unit], t0)
    assert haversine_km(s.lat, s.lon, *moved) == pytest.approx(0.0, abs=1e-6)


def test_below_recommend_level_gets_no_unit(cfg, t0):
    assert patrol.assign([("a", *OFFSHORE, "medium")], _cfg(cfg, True), {}, t0, {}) == {}


def test_shared_units_when_not_exclusive(cfg, t0):
    legs: dict = {}
    recs = patrol.assign([("a1", *OFFSHORE, "critical"), ("a2", *OFFSHORE, "critical")], _cfg(cfg, False), {}, t0, legs)
    assert recs["a1"].unit_id == recs["a2"].unit_id
    assert legs == {}                                            # fără exclusivitate unitățile nu sunt trimise


def test_tracks_stop_at_now(cfg, t0):
    now = t0 + timedelta(minutes=47)
    tracks = patrol.tracks({}, now, cfg, 5)
    assert {t.ship_type for t in tracks} == {patrol.SHIP_TYPE}
    for t in tracks:
        assert t.points[-1].t == now
        assert all(p.t <= now for p in t.points)


def test_demo_patrol_units_in_timeline(demo_out):
    tl = read_json(demo_out / "timeline.json")
    plans = {p.mmsi: p for p in patrol.load_plans()}
    patrols = [v for v in tl["vessels"] if v["ship_type"] == patrol.SHIP_TYPE]
    assert {v["mmsi"] for v in patrols} == set(plans)
    ais = {v["mmsi"] for v in tl["vessels"] if v["ship_type"] != patrol.SHIP_TYPE}
    assert not ais & set(plans), "patrol MMSIs must not collide with AIS traffic"
    assert all(v["simulated"] for v in patrols)


def test_demo_unit_reaches_the_dark_vessel_and_is_redirected(demo_out):
    sc = load_scenario()
    tl = read_json(demo_out / "timeline.json")
    alert = next(a for a in tl["alerts"] if a["mmsi"] == sc["dark_vessel"]["mmsi"])
    reappeared = next(f["added_at"] for f in alert["factors"] if f["code"] == "speed_inconsistency")
    hist = [h for h in alert["history"] if h.get("unit_id")]
    before = [h["eta_min"] for h in hist if h["t"] < reappeared]
    after = [h["eta_min"] for h in hist if h["t"] >= reappeared]
    assert before == sorted(before, reverse=True) and before[-1] == 0     # ajunge la ultima poziție cunoscută
    assert max(after) > 0                                                 # nava reapare în altă parte: redirecționare
    assert after[-1] == 0                                                 # și o ajunge din urmă
    assert alert["explanation"].endswith("is on scene.")


def test_demo_units_are_not_double_booked(demo_out):
    tl = read_json(demo_out / "timeline.json")
    units = [a["recommendation"]["unit_id"] for a in tl["alerts"] if a["recommendation"]]
    assert len(units) >= 2
    assert len(units) == len(set(units))
    for a in tl["alerts"]:
        assigned = [h["unit_id"] for h in a["history"] if h.get("unit_id")]
        assert len(set(assigned)) <= 1, a["alert_id"]
