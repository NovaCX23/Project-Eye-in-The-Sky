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
- `patrol.py`: the unit with the lowest ETA (haversine, straight line, STUB).
- `sinks.py`: output transport (atomic write of `out/timeline.json`).
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
python -m core.pipeline --watch --interval-s 3 --sim-step-min 5
python -m pytest core
```

Variant A (server + WebSocket): only `sources.py` and `sinks.py` are replaced; everything else stays.

## Tasks (prioritised)
1. P0: keep `main` green (`/verify`, `/demo-check`); integrate the branches with `/integrate`.
2. P1: alerts opened by sensors with no AIS vessel in the area (a vibration on the cable with no visible vessel is suspicious).
3. P1: ETA that routes around land; unit availability.
4. P2: persist state across `--watch` restarts.
