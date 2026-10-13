"""Modul live pe o înregistrare AIS construită aici (formatul data.aisstream), fără rețea."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from contracts.geo import destination, kn_to_kmh
from contracts.models import Timeline
from core.live import Live
from core.tests.test_no_future import _assert_nothing_after
from contracts.runtime import iso, write_json_atomic
from data.aisstream import POS_FIELDS, STATIC_FIELDS, DailyCsv
from sar.store import RECORD_VERSION

NOW = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)
SEA = (43.21, 28.15)           # larg, în zona varna; 2 h la 10 kn spre est rămân înăuntru
DARK, ESCORT = "273000001", "273000002"


def _write(ais_dir, tracks: dict[str, list[tuple[datetime, float, float, float]]]) -> None:
    pos, st = DailyCsv(ais_dir, "positions", POS_FIELDS), DailyCsv(ais_dir, "static", STATIC_FIELDS)
    for mmsi, pts in tracks.items():
        st.write({"received_utc": "2026-10-12T00:00:00Z", "mmsi": mmsi, "msg_type": "ShipStaticData",
                  "name": f"REAL {mmsi[-1]}", "ship_type_code": 70, "length_m": 120, "width_m": 20, "imo": None,
                  "callsign": None, "destination": None})
        for t, lat, lon, sog in pts:
            pos.write({"received_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "mmsi": mmsi, "msg_type": "PositionReport",
                       "lat": round(lat, 6), "lon": round(lon, 6), "sog_kn": sog, "cog_deg": 90.0,
                       "heading_deg": None, "nav_status": 0})
    pos.close()
    st.close()


def _track(t_from: datetime, t_to: datetime, lat: float, lon: float, sog: float = 10.0):
    """Un raport pe minut, în linie dreaptă spre est, pornind din (lat, lon) la t_from."""
    out, t = [], t_from
    while t <= t_to:
        la, lo = destination(lat, lon, 90.0, kn_to_kmh(sog) * (t - t_from).total_seconds() / 3600)
        out.append((t, la, lo, sog))
        t += timedelta(minutes=1)
    return out


def _radar_pass(sar_dir, cfg, acquired: datetime, published: datetime, targets: list[tuple[float, float]]) -> None:
    """O trecere procesată (formatul sar/process.py), fără imagine, peste toată zona varna; marea fără uscat."""
    b = cfg["areas"]["varna"]["bbox"]
    ring = [[b["lat_min"], b["lon_min"]], [b["lat_max"], b["lon_min"]], [b["lat_max"], b["lon_max"]],
            [b["lat_min"], b["lon_max"]], [b["lat_min"], b["lon_min"]]]
    pid = "S1X_" + acquired.strftime("%Y%m%dT%H%M%S") + "_1"
    write_json_atomic(sar_dir / "sea.geojson", {"bbox": b, "geometry": {
        "type": "Polygon", "coordinates": [[[lon, lat] for lat, lon in ring]]}})
    write_json_atomic(sar_dir / pid / "pass.json", {
        "version": RECORD_VERSION, "pass_id": pid, "area": "varna", "platform": "sentinel-1x",
        "acquired_at": iso(acquired), "available_at": iso(published), "footprint": ring, "rendered": True,
        "targets": [{"target_id": f"{pid}-{k:03d}", "lat": lat, "lon": lon, "length_m": 120.0, "width_m": 30.0,
                     "peak_db": 22.0, "pixels": 40, "coast_km": 20.0, "fixed": None} for k, (lat, lon) in enumerate(targets)]})


def _run(tmp_path, cfg, monkeypatch, escort_nearby: bool, radar: bool = False) -> Timeline:
    monkeypatch.setenv("SEAGRID_AREA", "varna")
    went_dark = NOW - timedelta(minutes=cfg["detect"]["gap"]["threshold_min"] + 20)
    # Nava "dark" transmite regulat 2 h, apoi tace. A doua navă stă acostată chiar lângă locul unde a tăcut (celula
    # devine "acoperită": acolo se aude AIS) sau departe (tăcerea nu mai dovedește nimic). După `now` înregistrarea
    # continuă: pipeline-ul nu are voie să vadă acele mesaje.
    dark = _track(NOW - timedelta(hours=2), went_dark, *SEA)
    escort_at = (dark[-1][1] + 0.003, dark[-1][2]) if escort_nearby else (42.75, 28.40)
    _write(tmp_path / "ais", {
        DARK: dark,
        ESCORT: _track(NOW - timedelta(hours=2), NOW + timedelta(hours=1), *escort_at, sog=0.0),
    })
    if radar:
        # Radarul trece la 35 min după ce nava a tăcut (gaura există deja) și o vede pe drumul ei; trecerea e
        # publicată înainte de now.
        silent = cfg["detect"]["gap"]["threshold_min"] + 5
        acquired = went_dark + timedelta(minutes=silent)
        seen = destination(dark[-1][1], dark[-1][2], 90.0, kn_to_kmh(10.0) * silent / 60)
        _radar_pass(tmp_path / "sar", cfg, acquired, NOW - timedelta(minutes=5), [seen])
    tl = Live(cfg, tmp_path / "ais", tmp_path / "out", tmp_path / "sar").tick(NOW)
    assert tl is not None
    return tl


def test_live_gap_alert_inside_receiver_coverage(tmp_path, cfg, monkeypatch):
    tl = _run(tmp_path, cfg, monkeypatch, escort_nearby=True)
    assert tl.mode == "live" and tl.simulated is False
    assert tl.area_name == cfg["areas"]["varna"]["name"] and tl.ais_coverage
    assert tl.scenario_start == NOW - timedelta(minutes=cfg["live"]["window_min"])
    dark = [a for a in tl.alerts if a.mmsi == DARK]
    assert [a.alert_type for a in dark] == ["ais_gap"]
    assert dark[0].vessel_name == "REAL 1"
    # Infrastructura și unitățile de patrulare ale zonei varna, nu cele ale scenariului demo (Constanța).
    assert tl.area_assets == "assets/areas/varna"
    assert dark[0].nearest_infrastructure and all(i.infra_id.startswith("BG-") for i in dark[0].nearest_infrastructure)
    patrols = [v for v in tl.vessels if v.ship_type == "patrol"]
    assert patrols and all(v.mmsi.startswith("207") for v in patrols)
    _assert_nothing_after(tl, NOW)
    assert (tmp_path / "out" / "timeline.json").exists()


def test_live_silence_outside_coverage_is_not_an_alert(tmp_path, cfg, monkeypatch):
    # Singură pe traseul ei, nava "dark" nu face celulele acoperite (live.coverage_min_vessels): tăcerea nu dovedește
    # nimic.
    tl = _run(tmp_path, cfg, monkeypatch, escort_nearby=False)
    assert not [a for a in tl.alerts if a.mmsi == DARK]
    assert not [e for e in tl.events if e.mmsi == DARK and e.event_type == "ais_gap"]


def test_live_without_recording_writes_nothing(tmp_path, cfg, monkeypatch):
    monkeypatch.setenv("SEAGRID_AREA", "varna")
    assert Live(cfg, tmp_path / "ais", tmp_path / "out").tick(NOW) is None
    assert not (tmp_path / "out" / "timeline.json").exists()


def test_live_radar_confirms_the_silent_vessel(tmp_path, cfg, monkeypatch):
    tl = _run(tmp_path, cfg, monkeypatch, escort_nearby=True, radar=True)
    dark = next(a for a in tl.alerts if a.mmsi == DARK)
    codes = {f.code for f in dark.factors}
    assert {"ais_gap", "sar_gap_confirmation"} <= codes
    without = _run(tmp_path / "no_radar", cfg, monkeypatch, escort_nearby=True)
    assert dark.risk_score > next(a for a in without.alerts if a.mmsi == DARK).risk_score
    [rp] = tl.radar_passes
    [target] = rp.targets
    assert target.status == "dark" and target.mmsi == DARK and rp.satellite == "Sentinel-1X"
    assert rp.available_at <= NOW
    _assert_nothing_after(tl, NOW)


def test_live_radar_pass_unknown_before_it_is_published(tmp_path, cfg, monkeypatch):
    monkeypatch.setenv("SEAGRID_AREA", "varna")
    _radar_pass(tmp_path / "sar", cfg, NOW - timedelta(minutes=30), NOW + timedelta(minutes=10), [SEA])
    _write(tmp_path / "ais", {ESCORT: _track(NOW - timedelta(hours=2), NOW, *SEA, sog=0.0)})
    tl = Live(cfg, tmp_path / "ais", tmp_path / "out", tmp_path / "sar").tick(NOW)
    assert tl.radar_passes == [] and not [e for e in tl.events if e.source == "sar"]
