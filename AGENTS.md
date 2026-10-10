# AGENTS.md — SeaGrid

Single source of truth for every coding assistant and every human working in this repo.
`CLAUDE.md` imports this file. Module details live in each directory's `README.md`.

## Project

SeaGrid detects suspicious activity around Romania's maritime infrastructure in the Black Sea
(gas platforms, pipelines, subsea cables, the approach to the port of Constanța).
Defense hackathon, 5 developers, ~10 hours to a complete demo.
Demo scenario: a cargo ship bound for Constanța turns AIS off for 2 h near a gas platform and a cable route;
on reappearance its position does not match its reported speed. A second vessel loiters at low speed nearby.
SeaGrid correlates both tracks with the infrastructure map, plus acoustic and fibre-optic events, and raises
an alert with a risk score, a template explanation, and the recommended patrol unit with ETA.
Judged on: detection rate of injected anomalies, false alarms on normal traffic, explanation quality, time to alert.
All data is synthetic and every simulated item carries `simulated: true`.

## Architecture (variant B: micro-batch, no server)

```
data/ (ais.csv, ground_truth, fibre events) ─┐
acoustic/ (precomputed acoustic events) ─────┼─> core/sources.py ─> detect/ rules ─> core/fusion ─> core/sinks.py ─> out/timeline.json ─> web/ (Leaflet replay)
assets/ (infrastructure, patrol units) ──────┘        (<= now only)                                    (atomic write)        (polls the file)
```

- `python -m core.pipeline` runs micro-batches on a simulated clock; `--watch` reruns every N seconds.
- `contracts/` holds the pydantic models, exported JSON Schema, and examples. Everything exchanged between modules matches them.
- Path to variant A (live server + WebSocket): replace only `core/sources.py`, `core/sinks.py`, and `web/loader.js`.
  `contracts/`, `detect/`, `acoustic/` must never import or assume anything about transport.
- No server, database, Docker, or cloud. The team adds containerisation later; do not add it.

## Mandatory design rules

1. The pipeline never reads a message with timestamp > `now`. All input goes through `core/sources.until()`.
2. An AIS gap is `now - last_message > threshold`, never the difference between two consecutive messages.
   The speed-consistency check is separate, runs on reappearance, and flags both too fast and too slow.
3. Every alert and event has a stable, deterministic id (`contracts.runtime.stable_id`), so repeated runs never duplicate.
4. All thresholds and score points live in `config.yaml`. No magic numbers in code.
5. Distances use haversine (`contracts/geo.py`). Never Euclidean distance on lat/lon.
6. Explanations come from templates (`core/explain.py`) filled with the detector's numbers. No LLM.
7. `web/` only displays. No detection, scoring, or threshold logic in the UI.
8. Anything simulated carries `simulated: true` in its data and is visibly labelled in the UI.

## Run commands

Run from the repo root with the virtualenv active. `make` is optional; each target wraps one `python -m` command.

| make | plain command |
|---|---|
| `make setup` | `python -m devtools.bootstrap` |
| `make test` | `python -m pytest` |
| `make demo` | `python -m core.demo` |
| `make eval` | `python -m eval.evaluate --seed-set tuning --run` |
| `make eval-report` | `python -m eval.evaluate --seed-set both --run --write-md pitch/metrics.md` |
| `make watch` | `python -m core.pipeline --watch` |
| `make serve` | `python -m http.server 8000` then open http://localhost:8000/web/ |
| `make schema` | `python -m contracts.export_schema` |
| `make validate` | `python -m contracts.validate out/timeline.json --model Timeline` |

Single steps: `python -m data.generate`, `python -m data.inject`, `python -m acoustic.analyze`, `python -m core.pipeline [--now ISO]`.
Seeds: tuning `42`, held-out reporting `1337` (in `config.yaml`). Never tune thresholds on the reporting seed.

## Directory ownership

Each directory has exactly one owner. Only the owner changes it.

| Directory | Owner | Contents |
|---|---|---|
| `contracts/` | shared; changed only via the `contract-change` skill | models, JSON Schema, examples, geo, runtime helpers |
| `assets/` | shared; the team agrees, Dev 4 merges | infrastructure GeoJSON (approximate), patrol units (simulated) |
| `data/` | Dev 1 | AIS loader, synthetic traffic, anomaly injector, ground truth, scenario file |
| `eval/` | Dev 1 | `evaluate.py`: detection rate, false alarms, time to alert |
| `detect/` | Dev 2 | AIS rules (gap, speed inconsistency, loitering, position jump), exclusion zones |
| `acoustic/` | Dev 3 | low-frequency energy detector, clips, acoustic events |
| `core/` | Dev 4 | orchestration, fusion, score, explanations, patrol ETA, timeline, `--watch` |
| `web/` | Dev 5 | `index.html` map, alert panel, factor breakdown, replay, uncertainty area |
| `pitch/` | Dev 5 | presentation outline, jury questions, `metrics.md` (generated) |
| root files, `devtools/`, `.githooks/`, `.claude/` | Dev 4 (integration owner) | Makefile, requirements, hooks, assistant config |

`config.yaml` is shared by section: each owner edits only their own section
(`generator`/`injector`/`eval`: Dev 1, `detect`: Dev 2, `acoustic`: Dev 3,
`fusion`/`score`/`patrol`/`pipeline`: Dev 4, `web`: Dev 5, `scenario`: Dev 1 with team agreement).

Branches: `main` plus `role/data-eval`, `role/detect`, `role/acoustic`, `role/core`, `role/web-pitch`.

## Working rules

- Do not modify a directory you do not own. If a change is needed there, say so and stop.
- Do not change `contracts/` except through the `contract-change` skill, and only on explicit request.
- `main` must always run the demo. Work on your role branch; merge only after `verify` passes.
- Prefer the simplest thing that honours the contract. Mark shortcuts with `# STUB` or `# HACK` and a one-line reason.
- Identifiers and file names in English; READMEs, code comments, and UI text in Romanian.
- Python 3.11+, pandas, numpy, shapely, pyyaml, pydantic, pytest. `librosa` only inside `acoustic/`.
- Modules are run with `python -m` from the repo root. No `sys.path` hacks.
- Read and write files as UTF-8; call `contracts.runtime.utf8_stdout()` in CLI entry points (Windows consoles).
- Do not download datasets. Do not add features beyond the module task lists.
- Small commits with clear messages, on your role branch.

## Authorship: no AI co-authors

No AI tool may present itself as an author or contributor in this repository. This binds every assistant, every session.

- Never add `Co-Authored-By` trailers, "Generated with" lines, robot emoji, or any assistant name as author
  to commit messages, pull requests, code comments, READMEs, or file headers.
- Commits are authored only by the human git identity already configured on the machine.
  Never set or change `user.name` or `user.email`.
- Enforced by `.githooks/commit-msg` (activated by `make setup` via `core.hooksPath`) and tested in
  `devtools/tests/test_commit_msg_hook.py`. Never bypass it with `--no-verify`.

## Definition of done (every change)

1. `python -m pytest` passes.
2. `python -m core.demo` writes `out/timeline.json`, which validates against `contracts/schema/Timeline.schema.json`
   and still contains the demo scenario alert (the `verify` skill does all three).
3. If detection changed: `python -m eval.evaluate --seed-set both --run` shows no rise in false alarms.
