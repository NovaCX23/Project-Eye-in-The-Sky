# eval/ (Dev 1)

## What it does
`evaluate.py` compares the alerts in `timeline.json` with `ground_truth.json` and prints:
detection rate, number of false alarms, false alarms per normal vessel, mean time to alert
(`created_at` minus the anomaly start), a per-type breakdown and the list of missed anomalies.

Matching (STUB): an alert detects an anomaly if it has the same MMSI and was created within
`[start, end + eval.match_grace_min]`. Any other alert is a false alarm.

## Consumes
`out/ground_truth.json`, `out/timeline.json` (or `out/eval/<set>/...`), `config.yaml` (`eval`, `scenario.seeds`).

## Produces
A markdown table on the console; with `--write-md`, the held-out seed table in `pitch/metrics.md`.

## Running it on its own
```bash
python -m eval.evaluate                                             # evaluates out/ (after make demo)
python -m eval.evaluate --seed-set tuning --run                     # = make eval
python -m eval.evaluate --seed-set both --run --write-md pitch/metrics.md   # = make eval-report
python -m pytest eval
```

The `reporting` seed (1337) is held out: nothing is tuned on it.

## Tasks (prioritised)
1. P0: find out how the organisers evaluate (format, matching, what counts as a "false alarm") and align `evaluate.py`.
2. P1: false alarms per hour of traffic, in addition to per vessel.
3. P1: average over several reporting seeds.
4. P2: CSV export of the matches for debugging.
