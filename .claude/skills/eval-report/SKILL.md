---
name: eval-report
description: Runs the SeaGrid evaluation on the tuning seed and on the held-out reporting seed, prints both metrics tables, and writes the reporting table to pitch/metrics.md. Use after any detection, fusion or scoring change, and before quoting numbers in the pitch.
allowed-tools: Bash(python -m eval.evaluate *) PowerShell(python -m eval.evaluate *)
---

# eval-report

1. From the repo root run:
   `python -m eval.evaluate --seed-set both --run --write-md pitch/metrics.md`
   (same as `make eval-report`). It regenerates data for seed `tuning` and seed `reporting` from `config.yaml`
   under `out/eval/<set>/`, runs the full pipeline for each, and prints both tables.
2. Show both tables to the user, plus any `MISSED` lines.
3. Point out which numbers are which: the tuning row may be tuned against, the reporting row is held out
   and is the only one that goes in the pitch. `pitch/metrics.md` contains only the reporting row.
4. If you were called from `add-rule` or `tune-thresholds`, compare the false alarm count with the previous run
   and say plainly whether it rose.
5. Do not edit `pitch/metrics.md` by hand.
