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
- `patrol.py`: assigns patrol units by alert priority, one unit per alert, lowest ETA (haversine, straight line, STUB).
- `sinks.py`: output transport (atomic write of `out/timeline.json`).
- `state.py`: `--watch` saves its state to `out/pipeline_state.json` after every batch and resumes from it after a restart,
  but only if the input data up to that moment is unchanged; otherwise it starts from the scenario start.
- `demo.py`: the full chain for `make demo`.

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
python -m pytest core
```

Variant A (server + WebSocket): only `sources.py` and `sinks.py` are replaced; everything else stays.

## Tasks (prioritised)
1. P0: keep `main` green (`/verify`, `/demo-check`); integrate the branches with `/integrate`.
2. P1: alerts opened by sensors with no AIS vessel in the area (a vibration on the cable with no visible vessel is suspicious).
   **Blocked:** `Alert.mmsi` is required by the contract; this needs `/contract-change` first (the `# STUB` in `fusion.py` marks the spot).
3. P1: when every patrol unit is already dispatched, `recommendation` is null and the UI says the alert is below the
   recommendation threshold. Telling the two cases apart needs a field in the contract (`/contract-change`), then a UI change (Dev 5).
4. P1: ETA that routes around land. **Needs:** a coastline / land polygon in `assets/` (team agreement, Dev 4 merges).
   In the current demo every straight line stays at sea, so this does not change the story.
5. P2: mention the acoustic signature in the explanation (`metrics.signature`: propeller vs. anchor chain),
   now that `acoustic/` produces it.

## Done
- ✔ Factor texts are frozen when the factor enters the score: scrubbing back never shows numbers not yet known.
- ✔ One patrol unit per alert, assigned by priority (level, score, age); a dispatched unit stays with its alert.
- ✔ `--watch` resumes from its saved state after a restart (`--fresh` starts over).
- ✔ UI, explanations, data, CLI output and docs switched to English.
