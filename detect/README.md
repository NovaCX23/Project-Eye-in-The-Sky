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

**On real AIS** (live mode), `core` passes `LearnedZones` learned from the recording (`data/recorded.py`):
- `ais_gap` fires only where AIS is actually received (receiver coverage) and only for a vessel that was reporting
  regularly (`detect.gap.min_messages_last_hour`): leaving radio range is not "going dark";
- learned anchorages count as exclusion zones, like the drawn ones;
- the port buffer: closer than `detect.exclusion.port_buffer_km` to the OpenStreetMap coastline (harbours, quays,
  basins behind breakwaters) is port activity, excluded like a drawn zone (coastline cached by `sar/landmask.py`);
- a vessel sitting still (mean speed <= `detect.loitering.max_moored_sog_kn`) is moored, not loitering.

**Radar** (`sar_rules.py`, real data only): when a Sentinel-1 pass is published, `core` hands over its targets
(found by `sar/`) and the AIS known up to `now`. Every AIS vessel gets a position at the image time (interpolated
between two fixes, or dead-reckoned for a few minutes), targets and vessels are paired one-to-one (Hungarian
assignment) inside a gate that grows with the position uncertainty plus an along-track allowance for moving ships.
What is left over:

| Event | Logic | Points |
|---|---|---|
| `sar_gap_confirmation` | a dark target inside the area a vessel could have reached since its AIS went silent (same conditions as `ais_gap`, at the image time), nearest to its dead-reckoned position | 40 |
| `sar_dark_target` | a ship-sized target with no AIS vessel, not a fixed structure, not coastal clutter, where AIS reception is proven | 35 |
| `sar_dark_target_uncovered` | the same where no receiver is proven to hear AIS: a weak clue, never an alert on its own | 10 |
| `ais_no_radar_return` | a vessel of at least `min_length_no_return_m` (by its own static report) at a near-certain position on open sea, with no radar return | 15 |

Thresholds: `detect.sar.*`; points: `score.points`.

Without learned zones (synthetic data) the whole coverage box counts as covered. The tuning and held-out metrics
did not change with these rules (100% detection, 0 false alarms on both seeds).

## Consumes
A DataFrame of `PositionMessage` rows with timestamp `<= now` (guaranteed by `core/sources.py`; `run_all` raises otherwise),
`now`, `config.yaml`.

## Produces
`list[SensorEvent]` with `source="ais"` (and `source="sar"` from `sar_rules.py`, plus the status of every radar
target), a deterministic id and every number the explanation needs in `metrics`.
No I/O, no state: it does not know how results are delivered.

## Running it on its own
```bash
python -m pytest detect
python -m core.demo && python -m eval.evaluate      # effect on the metrics
```
From Python: `from detect.ais_rules import run_all`.

## Tasks (prioritised)
1. P1: a new rule with `/add-rule`, for example rendezvous (two slow vessels close together).
   Needs an injected rendezvous anomaly first (`data/`, `/add-anomaly`), otherwise it cannot be evaluated.
2. P2: loitering extent as a radius around the centroid instead of the bbox diagonal. A per-window haversine loop
   would slow the replay noticeably, and the bbox diagonal already catches every injected case on all seeds.
3. P2: ignore service vessels (pilot, tug) by type. The synthetic pilot boat now exists but stays inside the port
   exclusion zone, so it triggers nothing today.

## Done
- ✔ Re-checked against the new slow normal traffic (3 trawlers, 1 pilot boat): no events on them, 0 false alarms on both seeds.
- ✔ A lone loitering far from infrastructure now raises an alert (`score.points.loitering` 15 -> 20): held-out detection 80% -> 100%, 0 false alarms.
- ✔ Expected speed on reappearance = median SOG of the `history_min` before the gap (the speed after reappearance no longer counts).
- ✔ A loitering episode starts at the first slow message (the demo start now matches the ground truth).
