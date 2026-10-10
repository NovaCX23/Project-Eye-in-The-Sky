---
name: tune-thresholds
description: Tunes SeaGrid detection thresholds and score points by editing config.yaml only, re-evaluating on the tuning seed after each change, and reporting the held-out seed result once at the end. Use when detection rate, false alarms or time to alert need improving without code changes.
allowed-tools: Bash(python -m eval.evaluate *) PowerShell(python -m eval.evaluate *)
---

# tune-thresholds

Only `config.yaml` may change. Only the section owned by the requesting developer (see `AGENTS.md`).

1. Baseline: `python -m eval.evaluate --seed-set tuning --run`. Record detection rate, false alarms, mean time to alert.
2. Change one value at a time in `config.yaml`. State the hypothesis first (e.g. "lower `detect.gap.threshold_min`
   from 30 to 20 to cut time to alert").
3. Re-run step 1. Keep the change only if the tuning table improves without raising false alarms.
4. Repeat 2–3. Stop after a handful of changes; do not overfit.
5. Never run or look at `--seed-set reporting` while tuning. Never edit code, tests, `data/scenarios/demo.yaml`,
   or the seeds.
6. At the end, once: run `/eval-report` and report the held-out row next to the baseline. If held-out
   false alarms rose, recommend reverting.
7. Run `python .claude/skills/verify/verify.py --skip-tests` and `python .claude/skills/demo-check/check_story.py --no-regen`
   so the demo story still holds.
