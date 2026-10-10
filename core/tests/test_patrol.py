"""Repartizarea unităților: o unitate per alertă, după prioritate; o unitate trimisă rămâne la alerta ei."""

from __future__ import annotations

from contracts.assets import load_patrol_units
from contracts.runtime import read_json
from core import patrol

OFFSHORE = (44.10, 29.65)   # cel mai aproape de unitatea din larg


def _cfg(cfg: dict, exclusive: bool) -> dict:
    return {**cfg, "patrol": {**cfg["patrol"], "one_alert_per_unit": exclusive}}


def test_one_unit_per_alert_in_priority_order(cfg):
    cands = [("a1", *OFFSHORE, "critical"), ("a2", *OFFSHORE, "critical"), ("a3", *OFFSHORE, "high")]
    recs = patrol.assign(cands, _cfg(cfg, True), {})
    units = [recs[a].unit_id for a in ("a1", "a2", "a3")]
    assert len(set(units)) == 3
    nearest = patrol.recommend(*OFFSHORE, "critical", cfg)
    assert units[0] == nearest.unit_id            # prima alertă primește cea mai apropiată unitate


def test_more_alerts_than_units(cfg):
    n = len(load_patrol_units())
    cands = [(f"a{i}", *OFFSHORE, "critical") for i in range(n + 1)]
    recs = patrol.assign(cands, _cfg(cfg, True), {})
    assert len(recs) == n
    assert f"a{n}" not in recs


def test_dispatched_unit_stays_with_its_alert(cfg):
    c = _cfg(cfg, True)
    dispatched: dict[str, str] = {}
    first = patrol.assign([("old", *OFFSHORE, "high")], c, dispatched)
    # Apare o alertă mai prioritară lângă aceeași unitate: unitatea deja trimisă nu i se dă.
    later = patrol.assign([("new", *OFFSHORE, "critical"), ("old", *OFFSHORE, "high")], c, dispatched)
    assert later["old"].unit_id == first["old"].unit_id
    assert later["new"].unit_id != first["old"].unit_id


def test_below_recommend_level_gets_no_unit(cfg):
    assert patrol.assign([("a", *OFFSHORE, "medium")], _cfg(cfg, True), {}) == {}


def test_shared_units_when_not_exclusive(cfg):
    cands = [("a1", *OFFSHORE, "critical"), ("a2", *OFFSHORE, "critical")]
    recs = patrol.assign(cands, _cfg(cfg, False), {})
    assert recs["a1"].unit_id == recs["a2"].unit_id


def test_demo_units_are_not_double_booked(demo_out):
    tl = read_json(demo_out / "timeline.json")
    units = [a["recommendation"]["unit_id"] for a in tl["alerts"] if a["recommendation"]]
    assert len(units) >= 2
    assert len(units) == len(set(units))
    for a in tl["alerts"]:
        assigned = [h["unit_id"] for h in a["history"] if h.get("unit_id")]
        assert len(set(assigned)) <= 1, a["alert_id"]     # unitatea nu sare de la o alertă la alta
