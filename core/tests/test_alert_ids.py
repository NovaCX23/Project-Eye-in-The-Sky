"""Id-urile alertelor sunt deterministe: rulări repetate nu creează duplicate."""

from __future__ import annotations

from datetime import timedelta

from contracts.runtime import parse_time, read_json, stable_id
from core import sources
from core.pipeline import PipelineState, replay, run_batch


def test_stable_id_is_deterministic():
    t = parse_time("2026-03-15T07:30:00Z")
    assert stable_id("636012345", "ais_gap", t) == stable_id("636012345", "ais_gap", t)
    assert stable_id("636012345", "ais_gap", t) != stable_id("636012345", "loitering", t)
    assert stable_id("636012345", "ais_gap", t) != stable_id("636012345", "ais_gap", t + timedelta(seconds=1))
    # Același moment, scris diferit, dă același id.
    assert stable_id("x", parse_time("2026-03-15T09:30:00+02:00")) == stable_id("x", t)


def test_single_batch_ids_repeat(demo_out, cfg):
    now = parse_time(cfg["scenario"]["start"]) + timedelta(minutes=200)
    inputs = sources.load_all(demo_out)
    a = run_batch(inputs, now, cfg, PipelineState(), mode="single")
    b = run_batch(inputs, now, cfg, PipelineState(), mode="single")
    assert [x.alert_id for x in a.alerts] == [x.alert_id for x in b.alerts]
    assert a.model_dump() == b.model_dump()


def test_replay_is_reproducible_and_has_no_duplicates(demo_out, cfg, tmp_path):
    first = read_json(demo_out / "timeline.json")
    second = replay(demo_out, tmp_path, cfg, verbose=False).model_dump(mode="json")
    ids = [a["alert_id"] for a in second["alerts"]]
    assert len(ids) == len(set(ids))
    assert ids == [a["alert_id"] for a in first["alerts"]]
    assert second["alerts"] == first["alerts"]


def test_one_alert_per_demo_incident(demo_out):
    tl = read_json(demo_out / "timeline.json")
    gt = read_json(demo_out / "ground_truth.json")
    for an in (a for a in gt["anomalies"] if a["origin"] == "demo"):
        assert sum(1 for a in tl["alerts"] if a["mmsi"] == an["mmsi"]) == 1, an["mmsi"]
