---
paths:
  - "detect/**"
---

# detect/ (owner: Dev 2)

- Owns: `ais_rules.py` (gap, speed inconsistency on reappearance, loitering, position jump), `zones.py`
  (exclusion-zone policy), `sar_rules.py` (Sentinel-1 radar targets vs AIS at the image time: dark targets, radar
  confirmation of an AIS gap, AIS with no radar return).
- Consumes: a DataFrame of PositionMessage rows with timestamp <= `now` (core guarantees it; `run_all` raises
  otherwise), `now`, `config.yaml` section `detect`, `contracts.geo`, `contracts.assets`, and on real data the
  `zones.LearnedZones` built by core (receiver coverage, anchorages; `None` for synthetic data).
- Produces: `list[SensorEvent]` with `source="ais"`, ids from `stable_id("ais", type, mmsi, start)`, and every
  number the explanation template needs in `metrics`. `sar_rules.cross_reference` also takes one processed radar
  pass (`sar/store.py` record), the distance to the coast and the vessel lengths, and returns `source="sar"` events
  plus the status of every target; it refuses a pass not yet published at `now`.
- Commands: `python -m pytest detect`; end to end `python -m core.demo` then `python -m eval.evaluate`.
- Done when: unit tests cover one injected case and one normal-traffic case per rule; the demo alert still fires;
  false alarms do not rise on the tuning seed (`/eval-report`).
- Hard rules: gap = `now - last_message > threshold`; speed check is separate, on reappearance, both directions;
  haversine only; thresholds only from config; no I/O, no state, no knowledge of how results are delivered.
- Allowed shortcuts: naive loops, bbox-diagonal extent for loitering (`# STUB`).
- New rule: use `/add-rule`.
