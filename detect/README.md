# detect/ (Dev 2)

## What it does
Naive but real AIS rules (they catch the demo scenario), in `ais_rules.py`:

| Rule | Logic | Threshold (config.yaml) |
|---|---|---|
| `ais_gap` | `now - last_message > threshold`; ignores the coverage edge and the exclusion zones | `detect.gap.*` |
| `speed_inconsistency` | on reappearance after a gap: haversine distance vs. reported speed, **too slow** and **too fast** | `detect.speed_consistency.*` |
| `loitering` | sliding window: low mean speed and tightly clustered positions, outside the exclusion zones | `detect.loitering.*` |
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
1. P0: tune the thresholds on the tuning seed (`/tune-thresholds`): random loitering far from infrastructure is missed on held-out.
2. P1: loitering by radius around the centroid instead of the bbox diagonal; an episode that starts at the first slow position, not at the window edge.
3. P1: expected speed from the history before the gap (not just the mean SOG).
4. P1: a new rule with `/add-rule`, for example rendezvous (two slow vessels close together).
5. P2: ignore service vessels (pilot, tug) by type.
