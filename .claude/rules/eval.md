---
paths:
  - "eval/**"
---

# eval/ (owner: Dev 1)

- Owns: `evaluate.py` (matches alerts to ground truth, prints the metrics table, writes `pitch/metrics.md`
  only when asked via `--write-md`).
- Consumes: `out/**/ground_truth.json`, `out/**/timeline.json` (Timeline contract), `config.yaml` section `eval`.
- Produces: the metrics table (detection rate, false alarms, false alarms per normal vessel, mean time to alert,
  per-type breakdown, list of misses).
- Commands: `python -m eval.evaluate` (current `out/`), `python -m eval.evaluate --seed-set tuning --run`,
  `python -m eval.evaluate --seed-set both --run --write-md pitch/metrics.md`, `python -m pytest eval`.
- Done when: the table prints for both seeds and the demo anomalies count as detected.
- Rules: the reporting seed is held out. Never use its numbers to change thresholds.
  Matching must not peek at anything the pipeline could not know at alert time.
- Allowed shortcuts: matching by MMSI + time window (`# STUB`) until the organisers publish their format.
