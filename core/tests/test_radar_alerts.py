"""Alerte pornite de radar: o țintă fără AIS devine propriul incident (fără MMSI), cu explicație și unitate."""

from __future__ import annotations

from datetime import timedelta

from contracts.models import Alert, SensorEvent
from contracts.runtime import parse_time
from core.fusion import AlertMemory, build_alerts

TARGET = "S1X_TEST-007"


def _dark(t, lat: float, lon: float, event_type: str = "sar_dark_target") -> SensorEvent:
    return SensorEvent(
        event_id=f"evt-{event_type}", event_type=event_type, source="sar", target_id=TARGET, sensor_id="S1X_TEST",
        start=t, end=t, lat=lat, lon=lon, confidence=0.8,
        metrics={"pass_id": "S1X_TEST", "satellite": "Sentinel-1X", "acquired": "09:00 UTC", "published": "10:00 UTC",
                 "target_id": TARGET, "length_m": 140.0, "peak_db": 24.0, "coast_km": 30.0, "nearest_ais_km": 12.3})


def test_dark_target_alert_has_no_mmsi(cfg):
    t = parse_time(cfg["scenario"]["start"]) + timedelta(hours=3)
    plt = (44.30, 29.45)   # la ~4 km de platforma de nord a scenariului demo (PLT-N)
    [a] = build_alerts([_dark(t, *plt)], t + timedelta(hours=1), cfg, {}, AlertMemory())
    Alert.model_validate(a.model_dump())
    assert a.mmsi is None and a.target_id == TARGET and a.alert_type == "sar_dark_target"
    codes = {f.code for f in a.factors}
    assert {"sar_dark_target", "near_infrastructure"} <= codes
    assert a.explanation.startswith(f"Unidentified radar target {TARGET} (no AIS)")
    assert "no AIS" in next(f.detail for f in a.factors if f.code == "sar_dark_target")
    assert "Nearest AIS vessel: 12.3 km." in a.explanation


def test_uncovered_target_alone_is_not_an_alert(cfg):
    t = parse_time(cfg["scenario"]["start"]) + timedelta(hours=3)
    ev = _dark(t, 44.0, 30.6, "sar_dark_target_uncovered")
    assert cfg["score"]["points"]["sar_dark_target_uncovered"] < cfg["score"]["alert_min"]
    assert build_alerts([ev], t + timedelta(hours=1), cfg, {}, AlertMemory()) == []


def test_weak_radar_clues_do_not_correlate_each_other(cfg):
    # Două ținte unde recepția AIS nu e dovedită, una lângă alta: niciuna nu devine alertă prin "corelare".
    t = parse_time(cfg["scenario"]["start"]) + timedelta(hours=3)
    a = _dark(t, 44.0, 30.6, "sar_dark_target_uncovered")
    b = _dark(t, 44.01, 30.61, "sar_dark_target_uncovered").model_copy(
        update={"event_id": "evt-b", "target_id": "S1X_TEST-008"})
    assert build_alerts([a, b], t + timedelta(hours=1), cfg, {}, AlertMemory()) == []
