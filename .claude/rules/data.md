---
paths:
  - "data/**"
---

# data/ (owner: Dev 1)

- Owns: `loader.py` (CSV -> DataFrame with PositionMessage columns, `until=now` filter), `generate.py`
  (synthetic normal traffic, fixed seed), `inject.py` (demo scenario + random anomalies + simulated fibre events +
  ground truth), `tracks.py` (motion helpers), `scenarios/demo.yaml` (story geometry and timing).
- Consumes: `contracts` (PositionMessage, SensorEvent, geo, assets), `config.yaml` sections `scenario`,
  `generator`, `injector`.
- Produces: `out/ais_clean.csv`, `out/ais.csv` (PositionMessage rows), `out/ground_truth.json`,
  `out/fibre_events.json` (SensorEvent list, `simulated: true`).
- Commands: `python -m data.generate --seed 42`, `python -m data.inject --seed 42`, `python -m pytest data`.
- Done when: same seed gives byte-identical output; every injected anomaly has a ground-truth record with
  `expected_event_types`; the demo scenario is unchanged unless the team agreed (`/demo-check` still passes).
- Allowed shortcuts: straight-line routes, constant speeds, scripted fibre events, `# HACK` linear interpolation
  on short segments. Never place random anomalies inside exclusion zones or near the coverage edge.
- Not yours: detection thresholds (`detect.*` in config) and anything in `detect/` or `core/`.
