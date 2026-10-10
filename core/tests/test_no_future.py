"""Regula de aur: pipeline-ul nu citește niciodată date cu timestamp > now."""

from __future__ import annotations

import re
from datetime import timedelta

import pandas as pd
import pytest

from contracts.models import SensorEvent
from contracts.runtime import parse_time
from contracts.testing import straight_track, to_df
from core import sources
from core.pipeline import PipelineState, run_batch
from detect import ais_rules

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def _all_timestamps(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _all_timestamps(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_timestamps(v)
    elif isinstance(obj, str) and ISO.match(obj):
        yield parse_time(obj)


def _assert_nothing_after(tl, now):
    data = tl.model_dump(mode="json")
    late = [t for t in _all_timestamps(data) if t > now]
    assert not late, f"future timestamps in the timeline: {late[:3]}"


@pytest.fixture
def scenario(cfg):
    t0 = parse_time(cfg["scenario"]["start"])
    # A: transmite 0..40, tace, apoi "reapare" la 80 foarte departe (asta e în viitor față de now=75).
    a = straight_track("111111111", t0, range(0, 41), 44.0, 29.6, name="A")
    jump = straight_track("111111111", t0, range(80, 90), 44.0, 29.6, sog=12.0, name="A")
    for r in jump:
        r["lon"] += 1.0
    # B: apare abia la minutul 70.
    b = straight_track("222222222", t0, range(70, 120), 44.2, 29.9, name="B")
    sensor_future = SensorEvent(event_id="evt-future", event_type="fibre_vibration", source="fibre",
                                start=t0 + timedelta(minutes=100), lat=44.0, lon=29.6, confidence=0.9, simulated=True)
    sensor_spanning = SensorEvent(event_id="evt-span", event_type="acoustic_lowfreq", source="acoustic",
                                  start=t0 + timedelta(minutes=70), end=t0 + timedelta(minutes=90),
                                  lat=44.0, lon=29.7, confidence=0.9, simulated=True)
    return t0, sources.Inputs(ais=to_df(a + jump + b), sensors=[sensor_future, sensor_spanning])


def test_until_drops_future(scenario):
    t0, inputs = scenario
    now = t0 + timedelta(minutes=75)
    view = sources.until(inputs, now)
    assert view.ais["timestamp"].max() <= pd.Timestamp(now)
    assert "222222222" in set(view.ais["mmsi"])
    assert [e.event_id for e in view.sensors] == ["evt-span"]
    assert view.sensors[0].end is None  # sfârșitul (minutul 90) e în viitor


def test_batch_uses_only_past(scenario, cfg):
    t0, inputs = scenario
    now = t0 + timedelta(minutes=75)
    tl = run_batch(inputs, now, cfg, PipelineState(), mode="single")
    types = {(e.mmsi, e.event_type) for e in tl.events}
    # Gaura e detectată din now - ultimul_mesaj (35 min > 30), fără să "vadă" reapariția de la minutul 80.
    assert ("111111111", "ais_gap") in types
    assert ("111111111", "speed_inconsistency") not in types
    assert ("111111111", "position_jump") not in types
    b = next(v for v in tl.vessels if v.mmsi == "222222222")
    assert max(p.t for p in b.points) <= now
    _assert_nothing_after(tl, now)


def test_detect_refuses_future_rows(scenario, cfg):
    t0, inputs = scenario
    with pytest.raises(ValueError):
        ais_rules.run_all(inputs.ais, t0 + timedelta(minutes=30), cfg)


@pytest.mark.parametrize("minute", [95, 150, 240])
def test_demo_batches_have_no_future(demo_out, cfg, minute):
    now = parse_time(cfg["scenario"]["start"]) + timedelta(minutes=minute)
    tl = run_batch(sources.load_all(demo_out), now, cfg, PipelineState(), mode="single")
    _assert_nothing_after(tl, now)
