"""Starea pipeline-ului salvată între reporniri ale `--watch` (out/pipeline_state.json).

La repornire se reia de la ultimul `now` doar dacă datele de intrare până la acel moment sunt aceleași
ca la salvare; altfel se pornește de la începutul scenariului. Ieșirea e identică cu o rulare fără pauză.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from contracts.models import ScorePoint, SensorEvent
from contracts.runtime import iso, parse_time, read_json, write_json_atomic
from core import sources
from core.patrol import Leg
from core.fusion import AlertMemory

STATE_FILE = "pipeline_state.json"
STATE_VERSION = 2


def _guard(inputs: sources.Inputs, now: datetime) -> dict:
    """Amprenta datelor <= now: dacă s-a schimbat trecutul, starea salvată nu mai e valabilă."""
    view = sources.until(inputs, now)
    return {"ais_messages": int(len(view.ais)), "sensor_events": sorted(e.event_id for e in view.sensors)}


def save(path: Path, state, now: datetime, inputs: sources.Inputs, cfg: dict) -> None:
    m: AlertMemory = state.memory
    write_json_atomic(path, {
        "version": STATE_VERSION,
        "scenario_start": cfg["scenario"]["start"],
        "now": iso(now),
        "batch_index": state.batch_index,
        "guard": _guard(inputs, now),
        "events": [e.model_dump(mode="json") for e in state.events.values()],
        "memory": {
            "created_at": {k: iso(v) for k, v in m.created_at.items()},
            "factor_added": [[a, c, iso(t)] for (a, c), t in m.factor_added.items()],
            "factor_evidence": [[a, c, d, eid, sim] for (a, c), (d, eid, sim) in m.factor_evidence.items()],
            "history": {k: [p.model_dump(mode="json") for p in v] for k, v in m.history.items()},
            "primary_of_event": m.primary_of_event,
            "dispatched": m.dispatched,
            "unit_legs": {u: [[iso(g.t), g.lat, g.lon, g.alert_id] for g in legs] for u, legs in m.unit_legs.items()},
        },
    })


def load(path: Path, inputs: sources.Inputs, cfg: dict, state_cls) -> tuple[object, datetime] | tuple[None, str]:
    """Întoarce (stare, now) sau (None, motivul pentru care se pornește de la început)."""
    if not path.exists():
        return None, "no saved state"
    raw = read_json(path)
    if raw.get("version") != STATE_VERSION or raw.get("scenario_start") != cfg["scenario"]["start"]:
        return None, "saved state belongs to another scenario or version"
    now = parse_time(raw["now"])
    if raw["guard"] != _guard(inputs, now):
        return None, "input data up to the saved moment has changed"
    mem = raw["memory"]
    memory = AlertMemory(
        created_at={k: parse_time(v) for k, v in mem["created_at"].items()},
        factor_added={(a, c): parse_time(t) for a, c, t in mem["factor_added"]},
        factor_evidence={(a, c): (d, eid, sim) for a, c, d, eid, sim in mem["factor_evidence"]},
        history={k: [ScorePoint.model_validate(p) for p in v] for k, v in mem["history"].items()},
        primary_of_event=dict(mem["primary_of_event"]),
        dispatched=dict(mem["dispatched"]),
        unit_legs={u: [Leg(parse_time(t), lat, lon, a) for t, lat, lon, a in legs] for u, legs in mem["unit_legs"].items()},
    )
    events = [SensorEvent.model_validate(e) for e in raw["events"]]
    state = state_cls(events={e.event_id: e for e in events}, memory=memory, batch_index=raw["batch_index"])
    return state, now
