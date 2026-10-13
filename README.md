# SeaGrid

Detection of suspicious activity around Romania's maritime infrastructure in the Black Sea:
gas platforms, pipelines, subsea cables, the approach to the port of Constanța.

**All data is synthetic (SIMULATED), and infrastructure coordinates are approximate.**

Demo scenario: a cargo ship bound for Constanța turns its AIS off for 2 hours near a platform and a cable.
On reappearance, its position does not match its reported speed. Meanwhile, a second vessel loiters at low speed
in the same area. SeaGrid correlates the tracks with the infrastructure map, a hydrophone and the fibre sensor,
then raises an alert with a risk score, an explanation and the recommended patrol unit (with ETA).

## Quick start

```bash
python -m venv .venv
# Windows (PowerShell):  .\.venv\Scripts\Activate.ps1      Linux/macOS:  source .venv/bin/activate
python -m devtools.bootstrap        # = make setup: dependencies + git hooks
python -m core.demo                 # = make demo: writes out/timeline.json
python -m http.server 8000          # = make serve
# open http://localhost:8000/web/ and press ▶
```

Python 3.11 or newer. Versions in `requirements.txt` are pinned and have wheels for 3.11–3.14.

## Commands

Each `make` target is a thin wrapper around a `python -m` command. Without `make` (Windows), run the right-hand column.

| make | direct command | what it does |
|---|---|---|
| `make setup` | `python -m devtools.bootstrap` | installs dependencies, activates `.githooks/` |
| `make test` | `python -m pytest` | all tests |
| `make demo` | `python -m core.demo` | traffic (seed 42) + scenario + acoustic + pipeline -> `out/timeline.json` |
| `make eval` | `python -m eval.evaluate --seed-set tuning --run` | metrics table on the tuning seed |
| `make eval-report` | `python -m eval.evaluate --seed-set both --run --write-md pitch/metrics.md` | tuning + held-out |
| `make watch` | `python -m core.pipeline --watch` | micro-batches on a simulated clock (after `make demo`) |
| `make serve` | `python -m http.server 8000` | static server; the page is at `/web/` |
| `make schema` | `python -m contracts.export_schema` | regenerates the JSON Schema |
| `make validate` | `python -m contracts.validate out/timeline.json --model Timeline` | validates the output |
| `make data` | `python -m data.generate` then `python -m data.inject` | data only |
| `make acoustic` | `python -m acoustic.analyze` | acoustic events only |
| `make pipeline` | `python -m core.pipeline` | pipeline only (replay) |
| `make record` | `python -m data.aisstream` | records REAL AIS (needs `.env`, see below) |
| `make live` | `python -m core.live` | pipeline on the real recording, wall clock |

Watch mode (simulated clock): run `python -m core.pipeline --watch` in one terminal and `python -m http.server 8000` in another,
then tick "Live" on the page. If `--watch` is restarted it resumes where it stopped; add `--fresh` to start the scenario over.

### Live mode on REAL AIS

1. Copy `.env.example` to `.env` and put your free aisstream.io key in it (https://aisstream.io, sign in with GitHub,
   "API Keys"). `.env` is never committed.
2. Pick the area in `config.yaml` (`live.area`, or the `SEAGRID_AREA` environment variable). **aisstream.io has no receiver
   near Constanța**, so use `varna` to get real traffic.
3. Three terminals:
   ```bash
   python -m data.aisstream     # = make record: keeps recording into data/raw/ais/<area>/
   python -m core.live          # = make live: rewrites out/live/timeline.json every minute
   python -m http.server 8000   # open http://localhost:8000/web/?mode=live (or click "Live" in the header)
   ```
The rules learn from the recording where AIS is actually received and where ships anchor, so a ship leaving radio range
or waiting at an anchorage is not an alert. A useful coverage map needs a few hours of recording.
`python -m core.live --at <ISO time> --ais-dir <folder>` replays one moment of an existing recording.
Live mode writes its own file, so running the demo (or `/verify`) never replaces it: the Demo / Live switch in the
page header picks which one you see.

## Architecture (variant B, micro-batch)

```
data/ ──> out/ais.csv, out/fibre_events.json, out/ground_truth.json
acoustic/ ──> out/acoustic_events.json
core/sources.py (only data <= now) -> detect/ (rules) -> core/fusion (score, explanations, patrol) -> core/sinks.py -> out/timeline.json
web/ reads out/timeline.json and replays it with a slider and speed control
```

No server, database, Docker or cloud. Moving to variant A (server + WebSocket) changes only
`core/sources.py`, `core/sinks.py` and `web/loader.js`.

## Structure and owners

| Directory | Owner | Role |
|---|---|---|
| `contracts/` | shared (only through the `contract-change` skill) | models, JSON Schema, examples, haversine |
| `assets/` | shared | infrastructure (approx.), patrol units (simulated) |
| `data/`, `eval/` | Dev 1 | AIS data, generator, injector, ground truth, evaluation |
| `detect/` | Dev 2 | AIS rules, exclusion zones |
| `acoustic/` | Dev 3 | low-frequency detector |
| `core/` | Dev 4 (integration) | pipeline, fusion, score, explanations, recommendation, `--watch` |
| `web/`, `pitch/` | Dev 5 | the UI, the presentation |

Branches: `main` (always runs the demo) ← `role/<role>` ← `feat/<module>-<name>`.
Each feature gets its own branch, created from the role branch. Commit often (at every step with green tests)
and push after each commit. Merge into the role branch only after `/verify`; into `main` only through `/integrate`.
Details: the "Git workflow" section of [AGENTS.md](AGENTS.md).
Role branches: `role/data-eval`, `role/detect`, `role/acoustic`, `role/core`, `role/web-pitch`.

Full working and design rules: [AGENTS.md](AGENTS.md). Each directory has its own `README.md` with tasks.

## Authorship

Commits are made only by humans, with the git identity configured on the machine. The `.githooks/commit-msg` hook
rejects messages that attribute authorship to an AI tool (`Co-Authored-By`, "Generated with", etc.).
`make setup` activates it via `git config core.hooksPath .githooks`.
