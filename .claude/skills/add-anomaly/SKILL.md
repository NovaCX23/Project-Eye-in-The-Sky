---
name: add-anomaly
description: Adds a new injected anomaly type to the SeaGrid synthetic data together with its ground-truth record and a test. Use when evaluation needs coverage for a behaviour the injector cannot yet produce.
---

# add-anomaly

Owner: Dev 1 (`data/`, `eval/`). Do not touch `detect/` or `core/`.

1. Parameters: add them under `injector:` in `config.yaml` (duration, distance, count in `random_anomalies`).
2. Injection: add a branch for the new kind in `inject_random` in `data/inject.py`. Pick vessels and times from
   the seeded `rng` only, skip exclusion zones and the coverage edge (reuse the existing checks), and keep the
   vessel transmitting after the anomaly.
3. Ground truth: append `_gt(kind, mmsi, start, end, lat, lon, "random", [expected event types], description)`.
   `expected_event_types` lists what a detector should emit.
4. Test in `data/tests/test_data.py`: generate + inject for a fixed seed into `tmp_path` and assert the ground-truth
   record exists and the injected change is visible in `ais.csv`.
5. Determinism: run `python -m data.inject --seed 42` twice and confirm identical output.
6. Run `python -m pytest data eval` and `/eval-report`. A new anomaly no detector catches yet shows as `MISSED`;
   that is expected, so report it to Dev 2.
7. Run `/demo-check`: the demo scenario must be unchanged.
