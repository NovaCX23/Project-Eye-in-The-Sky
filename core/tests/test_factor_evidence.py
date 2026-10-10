"""Factorii nu dezvăluie viitorul: textul din timeline-ul final e cel cunoscut la intrarea factorului în scor."""

from __future__ import annotations

import re

from contracts.runtime import parse_time, read_json
from core import pipeline
from data.generate import load_scenario


def test_factor_detail_is_frozen_at_added_at(demo_out, cfg, tmp_path):
    final = read_json(demo_out / "timeline.json")
    added_times = sorted({f["added_at"] for a in final["alerts"] for f in a["factors"]})
    assert added_times
    for added in added_times:
        cut = pipeline.replay(demo_out, tmp_path, cfg, end=parse_time(added), verbose=False)
        then = {(a.alert_id, f.code): f for a in cut.alerts for f in a.factors}
        for a in final["alerts"]:
            for f in (f for f in a["factors"] if f["added_at"] == added):
                past = then[(a["alert_id"], f["code"])]
                assert f["detail"] == past.detail, (a["alert_id"], f["code"])
                assert f["event_id"] == past.event_id, (a["alert_id"], f["code"])


def test_gap_factor_states_onset_not_final_duration(demo_out):
    sc = load_scenario()
    tl = read_json(demo_out / "timeline.json")
    alert = next(a for a in tl["alerts"] if a["mmsi"] == sc["dark_vessel"]["mmsi"])
    gap = next(f for f in alert["factors"] if f["code"] == "ais_gap")
    speed = next(f for f in alert["factors"] if f["code"] == "speed_inconsistency")
    assert gap["detail"].startswith("AIS silent since ")
    # Durata finală a găurii apare doar în factorul de reapariție, adăugat mai târziu.
    assert gap["added_at"] < speed["added_at"]
    final_gap_min = re.search(r"km in (\d+) min", speed["detail"]).group(1)
    assert int(final_gap_min) >= sc["dark_vessel"]["gap_duration_min"]
    assert f"{final_gap_min} min" not in gap["detail"]
