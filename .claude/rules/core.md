---
paths:
  - "core/**"
---

# core/ (owner: Dev 4, also integration owner)

- Owns: `sources.py` (input transport, the only `<= now` gate), `pipeline.py` (micro-batch, replay, `--watch`),
  `fusion.py` (episodes, context, correlation, alert assembly), `scoring.py` (additive score, levels),
  `explain.py` (English templates), `patrol.py` (unit + ETA), `sinks.py` (output transport), `demo.py`,
  `live.py` (live mode on the real AIS recording and Sentinel-1 passes, wall clock, learned zones).
- Consumes: `out/ais.csv`, `out/acoustic_events.json`, `out/fibre_events.json`, `detect.ais_rules.run_all`,
  in live mode `data/raw/ais/<area>/` and `data/raw/sar/<area>/` (via `sar.store`), `detect.sar_rules`,
  `contracts.*`, `config.yaml` sections `fusion`, `score`, `patrol`, `pipeline`, `web.reload_interval_s`.
- Produces: `out/timeline.json` (Timeline contract), written atomically.
- Commands: `python -m core.demo`, `python -m core.pipeline [--now ISO | --watch]`,
  `python -m core.live [--once | --at ISO --ais-dir DIR --sar-dir DIR]`, `python -m pytest core`.
- Done when: no-future, alert-id and demo-scenario tests pass; `/verify` and `/demo-check` pass.
- Hard rules: every input passes through `sources.until(now)`; alert ids come from `stable_id`; score points only
  from `config.yaml`; explanations only from templates; transport stays in `sources.py`/`sinks.py`.
- Allowed shortcuts: in-memory state, straight-line ETA, only AIS events open alerts (`# STUB`).
