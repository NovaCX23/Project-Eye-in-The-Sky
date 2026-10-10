---
paths:
  - "detect/**"
---

# detect/ (owner: Dev 2)

- Owns: `ais_rules.py` (gap, speed inconsistency on reappearance, loitering, position jump), `zones.py`
  (exclusion-zone policy).
- Consumes: a DataFrame of PositionMessage rows with timestamp <= `now` (core guarantees it; `run_all` raises
  otherwise), `now`, `config.yaml` section `detect`, `contracts.geo`, `contracts.assets`.
- Produces: `list[SensorEvent]` with `source="ais"`, ids from `stable_id("ais", type, mmsi, start)`, and every
  number the explanation template needs in `metrics`.
- Commands: `python -m pytest detect`; end to end `python -m core.demo` then `python -m eval.evaluate`.
- Done when: unit tests cover one injected case and one normal-traffic case per rule; the demo alert still fires;
  false alarms do not rise on the tuning seed (`/eval-report`).
- Hard rules: gap = `now - last_message > threshold`; speed check is separate, on reappearance, both directions;
  haversine only; thresholds only from config; no I/O, no state, no knowledge of how results are delivered.
- Allowed shortcuts: naive loops, bbox-diagonal extent for loitering, mean SOG before/after the gap (`# STUB`).
- New rule: use `/add-rule`.
