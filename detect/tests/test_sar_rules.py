"""Regulile radar pe o trecere construită aici: ținte asociate, dark, structuri fixe, confirmarea unei găuri AIS."""

from __future__ import annotations

from datetime import timedelta

import pytest

from contracts.geo import destination, kn_to_kmh
from contracts.runtime import iso, parse_time
from contracts.testing import straight_track, to_df
from detect import sar_rules

OPEN_SEA = (44.0, 29.6)          # departe de margini și de zonele de excludere
FAR = lambda lat, lon: 50.0      # noqa: E731  (distanța până la coastă: larg)


@pytest.fixture
def t(cfg):
    return parse_time(cfg["scenario"]["start"]) + timedelta(hours=3)   # momentul imaginii


def _target(k: int, lat: float, lon: float, **kw) -> dict:
    return dict(target_id=f"S1X_TEST-{k:03d}", lat=lat, lon=lon, length_m=120.0, width_m=30.0, peak_db=22.0,
                pixels=40, coast_km=50.0, fixed=None, **kw)


def _pass(t, targets, published_after_min: float = 60) -> dict:
    return {"pass_id": "S1X_TEST", "platform": "sentinel-1x", "acquired_at": iso(t),
            "available_at": iso(t + timedelta(minutes=published_after_min)),
            "footprint": [[43.6, 28.6], [44.9, 28.6], [44.9, 30.8], [43.6, 30.8], [43.6, 28.6]], "targets": targets}


def _status(statuses):
    return {s.target_id[-3:]: s.status for s in statuses}


def test_matched_dark_fixed_and_coastal(t, cfg):
    # O navă AIS trece exact prin ținta 000 la momentul imaginii; 001 e pe mare, fără AIS; 002 e o platformă; 003 e
    # lângă coastă.
    ship = straight_track("111111111", t - timedelta(minutes=20), range(0, 41), *OPEN_SEA, sog=10.0)
    at_t = next(r for r in ship if r["timestamp"] == t)
    rec = _pass(t, [_target(0, at_t["lat"], at_t["lon"]), _target(1, 44.3, 30.2),
                    _target(2, 44.5, 29.9, ) | {"fixed": "known platform: X"}, _target(3, 44.2, 29.0) | {"coast_km": 0.2}])
    now = t + timedelta(minutes=60)
    statuses, events = sar_rules.cross_reference(rec, to_df(ship), now, cfg, FAR)
    assert _status(statuses) == {"000": "matched", "001": "dark", "002": "fixed", "003": "coastal"}
    assert statuses[0].mmsi == "111111111"
    assert [(e.event_type, e.target_id, e.mmsi) for e in events] == [("sar_dark_target", "S1X_TEST-001", None)]
    e = events[0]
    assert e.source == "sar" and e.start == t and e.sensor_id == "S1X_TEST"
    assert e.metrics["nearest_ais_km"] > 10 and e.metrics["satellite"] == "Sentinel-1X"


def test_moving_ship_matches_within_the_doppler_allowance(t, cfg):
    # Radarul arată nava deplasată în azimut cu 1.2 km: în raza de bază (1 km) nu intră, cu toleranța Doppler da.
    ship = straight_track("111111111", t - timedelta(minutes=20), range(0, 41), *OPEN_SEA, sog=14.0)
    at_t = next(r for r in ship if r["timestamp"] == t)
    lat, lon = destination(at_t["lat"], at_t["lon"], 0.0, 1.2)
    statuses, events = sar_rules.cross_reference(_pass(t, [_target(0, lat, lon)]), to_df(ship), t + timedelta(hours=1),
                                                 cfg, FAR)
    assert _status(statuses) == {"000": "matched"} and events == []


def test_radar_confirms_the_vessel_that_went_dark(t, cfg):
    # Nava transmite regulat, tace cu 60 min înaintea imaginii; radarul o vede pe drumul ei, fără AIS.
    silent_min, sog = 60, 10.0
    ship = straight_track("222222222", t - timedelta(minutes=silent_min + 90), range(0, 91), *OPEN_SEA, sog=sog,
                          name="DARK ONE")
    last = ship[-1]
    lat, lon = destination(last["lat"], last["lon"], 90.0, kn_to_kmh(sog) * silent_min / 60)
    decoy = destination(lat, lon, 0.0, 30.0)   # altă țintă fără AIS, prea departe ca să fie aceeași navă
    rec = _pass(t, [_target(0, lat, lon), _target(1, *decoy)])
    # Altă navă, departe, transmite în jurul imaginii: înregistratorul mergea, deci tăcerea contează.
    other = straight_track("444444444", t - timedelta(minutes=20), range(0, 41), 43.8, 30.5, sog=10.0)
    statuses, events = sar_rules.cross_reference(rec, to_df(ship + other), t + timedelta(hours=1), cfg, FAR,
                                                 lengths={"222222222": 140.0})
    conf = [e for e in events if e.event_type == "sar_gap_confirmation"]
    assert len(conf) == 1 and conf[0].mmsi == "222222222" and conf[0].target_id == "S1X_TEST-000"
    assert conf[0].metrics["silent_min"] == silent_min and conf[0].metrics["candidate_name"] == "DARK ONE"
    assert statuses[0].mmsi == "222222222" and statuses[0].status == "dark"
    assert [e.event_type for e in events if e.target_id == "S1X_TEST-001"] == ["sar_dark_target"]


def test_big_ship_without_radar_return(t, cfg):
    ship = straight_track("333333333", t - timedelta(minutes=20), range(0, 41), *OPEN_SEA, sog=10.0)
    rec = _pass(t, [_target(0, 44.3, 30.2)])
    _, events = sar_rules.cross_reference(rec, to_df(ship), t + timedelta(hours=1), cfg, FAR,
                                          lengths={"333333333": 180.0})
    assert [(e.event_type, e.mmsi) for e in events if e.mmsi] == [("ais_no_radar_return", "333333333")]
    # O navă mică (sub detect.sar.min_length_no_return_m) poate lipsi de pe radar fără să fie suspectă.
    _, events = sar_rules.cross_reference(rec, to_df(ship), t + timedelta(hours=1), cfg, FAR,
                                          lengths={"333333333": 30.0})
    assert not [e for e in events if e.mmsi]


def test_no_ais_recorded_at_image_time_means_unchecked(t, cfg):
    # Înregistratorul a pornit după imagine: țintele fără AIS nu dovedesc nimic, nicio alertă.
    later = straight_track("111111111", t + timedelta(minutes=45), range(0, 30), *OPEN_SEA, sog=10.0)
    rec = _pass(t, [_target(0, 44.3, 30.2), _target(1, 44.5, 29.9) | {"fixed": "known platform: X"}])
    statuses, events = sar_rules.cross_reference(rec, to_df(later), t + timedelta(hours=2), cfg, FAR)
    assert _status(statuses) == {"000": "unchecked", "001": "fixed"} and events == []


def test_no_future_data(t, cfg):
    rec = _pass(t, [_target(0, 44.3, 30.2)], published_after_min=60)
    with pytest.raises(ValueError):
        sar_rules.cross_reference(rec, to_df([]), t + timedelta(minutes=30), cfg, FAR)   # încă nepublicată


def test_satellite_name():
    assert sar_rules.satellite_name("sentinel-1c") == "Sentinel-1C"
