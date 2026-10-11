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


def test_stopping_after_reappearance_is_not_an_inconsistency(t0, cfg):
    # 12 kn înainte de pauză, 61 min de tăcere, ~22 km parcurși (consistent); la reapariție nava stă (0 kn).
    before = straight_track("111111111", t0, range(0, 20), *OPEN_SEA, sog=12.0)
    lat, lon = destination(before[-1]["lat"], before[-1]["lon"], 90.0, 22.6)
    after = straight_track("111111111", t0, range(80, 90), lat, lon, sog=0.0)
    assert ais_rules.detect_speed_inconsistency(to_df(before + after), cfg) == []


def test_expected_speed_ignores_a_single_glitch_before_the_gap(t0, cfg):
    # O singură valoare SOG eronată chiar înainte de pauză nu schimbă viteza așteptată (mediană pe istoric).
    before = straight_track("111111111", t0, range(0, 20), *OPEN_SEA, sog=12.0)
    before[-1]["sog_kn"] = 40.0
    lat, lon = destination(before[-1]["lat"], before[-1]["lon"], 90.0, 22.6)
    after = straight_track("111111111", t0, range(80, 90), lat, lon, sog=12.0)
    assert ais_rules.detect_speed_inconsistency(to_df(before + after), cfg) == []


def test_consistent_reappearance_is_normal(t0, cfg):
    rows = straight_track("111111111", t0, list(range(0, 20)) + list(range(60, 80)), *OPEN_SEA, sog=12.0)
    assert ais_rules.detect_speed_inconsistency(to_df(rows), cfg) == []


def test_loitering_detected_in_open_sea(t0, cfg):
    rows = straight_track("111111111", t0, range(0, 90), *OPEN_SEA, sog=0.5)
    assert "loitering" in _types(ais_rules.detect_loitering(to_df(rows), cfg))


def test_loitering_starts_at_first_slow_position(t0, cfg):
    # 30 min de tranzit cu 9 kn, apoi 90 min de staționare: episodul începe la primul mesaj lent, nu mai devreme.
    transit = straight_track("111111111", t0, range(0, 30), *OPEN_SEA, sog=9.0)
    slow = straight_track("111111111", t0, range(30, 120), transit[-1]["lat"], transit[-1]["lon"], sog=0.5)
    ev = ais_rules.detect_loitering(to_df(transit + slow), cfg)
    assert [e.start for e in ev] == [slow[0]["timestamp"]]


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


def test_rendezvous_detected(t0, cfg):
    # Două nave în larg care stau la ~250m una de alta la 0.5 kn timp de 30 min => rendezvous
    vessel_a = straight_track("111111111", t0, range(0, 30), *OPEN_SEA, sog=0.5)
    lat_b, lon_b = destination(OPEN_SEA[0], OPEN_SEA[1], 45.0, 0.25)  # 250 m
    vessel_b = straight_track("222222222", t0, range(0, 30), lat_b, lon_b, sog=0.5)
    df = to_df(vessel_a + vessel_b)
    ev = ais_rules.detect_rendezvous(df, cfg)
    assert len(ev) == 2
    types = {e.event_type for e in ev}
    mmsis = {e.mmsi for e in ev}
    assert types == {"rendezvous"}
    assert mmsis == {"111111111", "222222222"}
    ev_a = next(e for e in ev if e.mmsi == "111111111")
    assert ev_a.metrics["other_mmsi"] == "222222222"
    assert ev_a.metrics["distance_km"] <= 0.5


def test_rendezvous_ignored_in_anchorage(t0, cfg):
    # În radă/ancoraj, apropierea navelor este normală
    vessel_a = straight_track("111111111", t0, range(0, 30), *ANCHORAGE, sog=0.3)
    lat_b, lon_b = destination(ANCHORAGE[0], ANCHORAGE[1], 45.0, 0.2)
    vessel_b = straight_track("222222222", t0, range(0, 30), lat_b, lon_b, sog=0.3)
    df = to_df(vessel_a + vessel_b)
    assert ais_rules.detect_rendezvous(df, cfg) == []


def test_identity_spoofing_detected(t0, cfg):
    # Același MMSI raportează la distanță de 35 km la interval de 1 minut => transponder clonat
    msg1 = straight_track("111111111", t0, [0], *OPEN_SEA, sog=12.0)
    lat_far, lon_far = destination(OPEN_SEA[0], OPEN_SEA[1], 90.0, 35.0)
    msg2 = straight_track("111111111", t0, [1], lat_far, lon_far, sog=12.0)
    df = to_df(msg1 + msg2)
    ev = ais_rules.detect_identity_spoofing(df, cfg)
    assert len(ev) == 1
    assert ev[0].event_type == "identity_spoofing"
    assert ev[0].metrics["distance_km"] >= 30.0
    assert ev[0].metrics["implied_kn"] > 500.0



# --- Date reale: acoperire de recepție, transmisie regulată, ancoraje învățate, nave acostate ---------------------

def _learned(cfg, lat, lon, coverage=True, anchorage=False):
    from detect.zones import LearnedZones

    lc = cfg["live"]
    cov, anc = lc["coverage_cell_deg"], lc["anchorage_cell_deg"]
    cell = lambda size: (int(lat // size), int(lon // size))  # noqa: E731
    return LearnedZones(bbox=cfg["scenario"]["coverage_bbox"], coverage_cell_deg=cov, anchorage_cell_deg=anc,
                        coverage=frozenset({cell(cov)} if coverage else set()),
                        anchorages=frozenset({cell(anc)} if anchorage else set()))


def test_gap_outside_receiver_coverage_is_ignored(t0, cfg):
    df = to_df(straight_track("111111111", t0, range(0, 30), *OPEN_SEA))
    now = t0 + timedelta(minutes=29 + cfg["detect"]["gap"]["threshold_min"] + 5)
    last = (df.iloc[-1]["lat"], df.iloc[-1]["lon"])
    assert _types(ais_rules.detect_gaps(df, now, cfg, _learned(cfg, *last))) == ["ais_gap"]
    assert ais_rules.detect_gaps(df, now, cfg, _learned(cfg, *last, coverage=False)) == []


def test_gap_needs_regular_reporting_before(t0, cfg):
    # Un raport la 15 minute: sub detect.gap.min_messages_last_hour, deci tăcerea nu e o gaură AIS.
    sparse = to_df(straight_track("111111111", t0, range(0, 60, 15), *OPEN_SEA))
    now = t0 + timedelta(minutes=45 + cfg["detect"]["gap"]["threshold_min"] + 5)
    assert ais_rules.detect_gaps(sparse, now, cfg) == []


def test_learned_anchorage_excludes_loitering(t0, cfg):
    rows = straight_track("111111111", t0, range(0, 90), *OPEN_SEA, sog=0.5)
    assert ais_rules.detect_loitering(to_df(rows), cfg, _learned(cfg, *OPEN_SEA, anchorage=True)) == []
    assert "loitering" in _types(ais_rules.detect_loitering(to_df(rows), cfg, _learned(cfg, *OPEN_SEA)))


def test_moored_vessel_is_not_loitering(t0, cfg):
    still = cfg["detect"]["loitering"]["max_moored_sog_kn"] / 2
    rows = straight_track("111111111", t0, range(0, 90), *OPEN_SEA, sog=still)
    assert ais_rules.detect_loitering(to_df(rows), cfg) == []


def test_two_moored_vessels_side_by_side_are_not_a_rendezvous(t0, cfg):
    # Pe AIS real: două nave la ancoră, la 850 m, nemișcate ore întregi. Nu e o întâlnire.
    still = cfg["detect"]["rendezvous"]["max_moored_sog_kn"] / 2
    vessel_a = straight_track("111111111", t0, range(0, 60), *OPEN_SEA, sog=still)
    lat_b, lon_b = destination(OPEN_SEA[0], OPEN_SEA[1], 45.0, 0.85)
    vessel_b = straight_track("222222222", t0, range(0, 60), lat_b, lon_b, sog=0.0)
    assert ais_rules.detect_rendezvous(to_df(vessel_a + vessel_b), cfg) == []
