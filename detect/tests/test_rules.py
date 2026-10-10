"""Regulile AIS pe cazuri mici, controlate: câte un caz pozitiv și unul de trafic normal."""

from __future__ import annotations

from datetime import timedelta

import pytest

from contracts.geo import destination
from contracts.runtime import parse_time
from contracts.testing import straight_track, to_df
from detect import ais_rules

OPEN_SEA = (44.0, 29.6)          # departe de margini și de zonele de excludere
ANCHORAGE = (44.05, 28.79)       # în ANCH-1


@pytest.fixture
def t0(cfg):
    return parse_time(cfg["scenario"]["start"])


def _types(events, mmsi="111111111"):
    return [e.event_type for e in events if e.mmsi == mmsi]


def test_gap_is_now_minus_last_message(t0, cfg):
    df = to_df(straight_track("111111111", t0, range(0, 30), *OPEN_SEA))
    last = t0 + timedelta(minutes=29)
    thr = cfg["detect"]["gap"]["threshold_min"]
    assert ais_rules.detect_gaps(df, last + timedelta(minutes=thr - 1), cfg) == []
    ev = ais_rules.detect_gaps(df, last + timedelta(minutes=thr + 5), cfg)
    assert [e.event_type for e in ev] == ["ais_gap"]
    assert ev[0].end is None and ev[0].metrics["gap_min"] == pytest.approx(thr + 5)


def test_historic_hole_is_not_a_current_gap(t0, cfg):
    # Pauză de 40 min între mesaje, dar nava transmite acum: nu e ais_gap (doar regula de reapariție o vede).
    rows = straight_track("111111111", t0, list(range(0, 20)) + list(range(60, 90)), *OPEN_SEA)
    df = to_df(rows)
    assert ais_rules.detect_gaps(df, t0 + timedelta(minutes=90), cfg) == []


def test_gap_at_coverage_edge_ignored(t0, cfg):
    edge = (cfg["scenario"]["coverage_bbox"]["lat_max"] - 0.01, 29.6)
    df = to_df(straight_track("111111111", t0, range(0, 30), *edge))
    assert ais_rules.detect_gaps(df, t0 + timedelta(minutes=120), cfg) == []


@pytest.mark.parametrize(("km_moved", "direction"), [(3.0, "too_slow"), (60.0, "too_fast")])
def test_speed_inconsistency_both_directions(t0, cfg, km_moved, direction):
    # Raportează 12 kn; după 61 min de tăcere ar trebui să fie la ~22 km, dar e la km_moved.
    before = straight_track("111111111", t0, range(0, 20), *OPEN_SEA, sog=12.0)
    lat, lon = destination(before[-1]["lat"], before[-1]["lon"], 90.0, km_moved)
    after = straight_track("111111111", t0, range(80, 90), lat, lon, sog=12.0)
    ev = ais_rules.detect_speed_inconsistency(to_df(before + after), cfg)
    assert [e.metrics["direction"] for e in ev] == [direction]


def test_consistent_reappearance_is_normal(t0, cfg):
    rows = straight_track("111111111", t0, list(range(0, 20)) + list(range(60, 80)), *OPEN_SEA, sog=12.0)
    assert ais_rules.detect_speed_inconsistency(to_df(rows), cfg) == []


def test_loitering_detected_in_open_sea(t0, cfg):
    rows = straight_track("111111111", t0, range(0, 90), *OPEN_SEA, sog=0.5)
    assert "loitering" in _types(ais_rules.detect_loitering(to_df(rows), cfg))


def test_loitering_ignored_in_anchorage(t0, cfg):
    rows = straight_track("111111111", t0, range(0, 90), *ANCHORAGE, sog=0.3)
    assert ais_rules.detect_loitering(to_df(rows), cfg) == []


def test_normal_transit_has_no_events(t0, cfg):
    df = to_df(straight_track("111111111", t0, range(0, 120), *OPEN_SEA, sog=12.0))
    assert ais_rules.run_all(df, t0 + timedelta(minutes=120), cfg) == []


def test_position_jump(t0, cfg):
    rows = straight_track("111111111", t0, range(0, 30), *OPEN_SEA)
    rows[15]["lat"] += 0.3  # ~33 km într-un minut
    ev = ais_rules.detect_position_jumps(to_df(rows), cfg)
    assert ev and all(e.event_type == "position_jump" for e in ev)


def test_event_ids_stable(t0, cfg):
    df = to_df(straight_track("111111111", t0, range(0, 30), *OPEN_SEA))
    now = t0 + timedelta(minutes=80)
    a = ais_rules.detect_gaps(df, now, cfg)
    b = ais_rules.detect_gaps(df, now + timedelta(minutes=10), cfg)
    assert a[0].event_id == b[0].event_id
