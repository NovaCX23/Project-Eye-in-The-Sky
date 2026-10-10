# detect/ (Dev 2)

## What it does
Naive but real AIS rules (they catch the demo scenario), in `ais_rules.py`:

| Rule | Logic | Threshold (config.yaml) |
|---|---|---|
| `ais_gap` | `now - last_message > threshold`; ignores the coverage edge and the exclusion zones | `detect.gap.*` |
| `speed_inconsistency` | on reappearance after a gap: haversine distance vs. the median speed reported in the `history_min` before the gap, **too slow** and **too fast** | `detect.speed_consistency.*` |
| `loitering` | sliding window: low mean speed and tightly clustered positions, outside the exclusion zones; the episode starts at the first slow message | `detect.loitering.*` |
| `position_jump` | two messages close in time with an impossible implied speed | `detect.position_jump.*` |

`zones.py` decides which rules take the exclusion zones into account (the anchorage, the port corridor).

## Consumes
A DataFrame of `PositionMessage` rows with timestamp `<= now` (guaranteed by `core/sources.py`; `run_all` raises otherwise),
`now`, `config.yaml`.

## Produces
`list[SensorEvent]` with `source="ais"`, a deterministic id and every number the explanation needs in `metrics`.
No I/O, no state: it does not know how results are delivered.

## Running it on its own
```bash
python -m pytest detect
python -m core.demo && python -m eval.evaluate      # effect on the metrics
```
From Python: `from detect.ais_rules import run_all`.

## Tasks (prioritised)
1. P1: re-check loitering false alarms once `data/` adds slow normal traffic (fishing boats, pilot boats).
   Today no normal vessel ever triggers a rule, so a lone loitering (20 points = `score.alert_min`) is safe;
   with slow normal traffic it may not be.
2. P1: a new rule with `/add-rule`, for example rendezvous (two slow vessels close together).
   Needs an injected rendezvous anomaly first (`data/`, `/add-anomaly`), otherwise it cannot be evaluated.
3. P2: loitering extent as a radius around the centroid instead of the bbox diagonal. A per-window haversine loop
   would slow the replay noticeably, and the bbox diagonal already catches every injected case on all seeds.
4. P2: ignore service vessels (pilot, tug) by type (the synthetic traffic has none yet).
