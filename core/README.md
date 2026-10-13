# core/ (Dev 4, integration owner)

## What it does
- `sources.py`: input transport (files). `until(now)` is the only gate: nothing with timestamp `> now` gets through.
- `pipeline.py`: one micro-batch = inputs `<= now` -> `detect.run_all` -> event store (deterministic ids,
  upsert) -> fusion -> `Timeline`. Modes: replay (default, simulated clock step by step), `--now` (one batch), `--watch`.
- `fusion.py`: groups a vessel's AIS events into incidents; attaches nearby sensors (acoustic, fibre),
  infrastructure proximity and correlation with other suspicious vessels; remembers `created_at`, when each factor
  was added, and the score history.
- `scoring.py`: additive score with the points from `config.yaml`, capped; levels low/medium/high/critical.
- `explain.py`: English templates filled with the detector's numbers. No LLM.
- `patrol.py`: moving patrol units. Each unit loops its patrol route from `assets/patrol_units.json`; when dispatched it
  heads from where it is to the vessel's last known AIS position at response speed (redirected if the vessel
  reappears elsewhere) and escorts it once within `patrol.on_scene_km`. Units are assigned by alert priority,
  one unit per alert, lowest ETA from the unit's position at `now` (haversine, straight line, STUB). Their tracks go into
  the timeline as vessels with `ship_type: "patrol"`, so no contract change was needed.
- `sinks.py`: output transport (atomic write of `out/timeline.json`).
- `state.py`: `--watch` saves its state to `out/pipeline_state.json` after every batch and resumes from it after a restart,
  but only if the input data up to that moment is unchanged; otherwise it starts from the scenario start.
- `demo.py`: the full chain for `make demo`.
- Radar (real data only): `sources.load_live` also loads the Sentinel-1 passes processed by `sar.process` and
  published by `now` (the pass exists from its ESA processing time, not its acquisition time). `pipeline.run_batch`
  runs `detect.sar_rules` once per pass, at the first batch after publication; radar events with an MMSI join that
  vessel's incident, a dark target with no AIS opens its own alert (`mmsi: null`, `target_id`). The timeline lists
  the recent passes with every target's status in `radar_passes` (`detect.sar.max_age_h`).
- `live.py`: LIVE mode on real AIS recorded by `data.aisstream`, on the wall clock. Every `live.tick_s` seconds it loads the
  last `live.window_min` minutes (plus `live.lookback_min` for the rules that look back) through `sources.load_live`,
  relearns receiver coverage and anchorages every `live.zones_refresh_min` minutes (`detect.zones.LearnedZones`),
  and writes `out/live/timeline.json` (separate from the demo) with `mode: "live"`, the area name and the coverage cells. On start it replays the
  window once so alerts keep their history. `--at ISO --ais-dir DIR` runs one batch at a past moment of a recording.
  No injected anomalies: only the patrol units are simulated.

## Consumes
`out/ais.csv`, `out/acoustic_events.json`, `out/fibre_events.json`, `assets/`, `config.yaml`
(`fusion`, `score`, `patrol`, `pipeline`, `web`).

## Produces
`out/timeline.json` (the `Timeline` contract).

## Running it on its own
```bash
python -m core.pipeline                              # replay to the end of the scenario
python -m core.pipeline --now 2026-03-15T08:30:00Z   # a single batch
python -m core.pipeline --watch --interval-s 3 --sim-step-min 5   # resumes after a restart; --fresh starts over
python -m core.live                                  # real AIS, wall clock (needs python -m data.aisstream running;
                                                     # radar passes come from python -m sar.process --watch)
python -m core.live --at 2026-10-12T04:00:00Z --ais-dir data/raw/ais/varna   # one batch at a past moment
python -m pytest core
```

Variant A (server + WebSocket): only `sources.py` and `sinks.py` are replaced; everything else stays.

## Tasks (prioritised)
1. P0: keep `main` green (`/verify`, `/demo-check`); integrate the branches with `/integrate`.
2. P1: alerts opened by sensors with no AIS vessel in the area (a vibration on the cable with no visible vessel is suspicious).
   **Blocked:** `Alert.mmsi` is required by the contract; this needs `/contract-change` first (the `# STUB` in `fusion.py` marks the spot).
3. P1: when every patrol unit is already dispatched, `recommendation` is null, so the UI can only show a neutral message
   covering both cases (below the recommendation level, or every unit dispatched). Telling the two cases apart needs a field in the contract (`/contract-change`), then a UI change (Dev 5).
4. P1: ETA that routes around land. **Needs:** a coastline / land polygon in `assets/` (team agreement, Dev 4 merges).
   In the current demo every straight line stays at sea, so this does not change the story.
5. P2: a unit whose alert drops below the recommendation level stays where it is; it should return to its patrol route.
   (Alerts never de-escalate in the current scenarios, so this does not show in the demo.)

## Done
- ✔ The acoustic factor names the signature (propeller vs. anchor chain) and its dominant frequency.
- ✔ Factor texts are frozen when the factor enters the score: scrubbing back never shows numbers not yet known.
- ✔ One patrol unit per alert, assigned by priority (level, score, age); a dispatched unit stays with its alert.
- ✔ `--watch` resumes from its saved state after a restart (`--fresh` starts over).
- ✔ Moving patrol units: patrol routes from real bases, dispatch towards the alert, ETA from the current position that
  counts down in the alert history until "on scene"; unit tracks in the timeline (`ship_type: "patrol"`).
- ✔ UI, explanations, data, CLI output and docs switched to English.
