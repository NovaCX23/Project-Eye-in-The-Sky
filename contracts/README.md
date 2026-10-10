# contracts/ (shared)

**Changed only through the `contract-change` skill, on explicit request.**

## What it does
Defines the format of the data exchanged between modules, plus the helpers everyone must use the same way.

| File | Contents |
|---|---|
| `models.py` | `PositionMessage`, `SensorEvent`, `Alert` (with `ScoreFactor`, `ScorePoint`, `PatrolRecommendation`), `Timeline` |
| `schema/*.schema.json` | exported JSON Schema (generated, never edited by hand) |
| `examples/*.json` | one valid example per model |
| `geo.py` | haversine, point–segment distance on the sphere, `destination` |
| `runtime.py` | paths, `load_config`, `stable_id`, ISO time, atomic JSON write, UTF-8 console |
| `assets.py` | loading of the infrastructure and the patrol units |
| `testing.py` | builders of small AIS datasets for tests |
| `validate.py` | validates a JSON file against the schema |

## Consumes
Nothing from other modules.

## Produces
The types imported by every other module.

## Running it on its own
```bash
python -m contracts.export_schema            # regenerates the schema
python -m contracts.export_schema --check    # fails if the schema is out of date
python -m contracts.validate out/timeline.json --model Timeline
python -m pytest contracts
```

## Tasks (prioritised)
1. P0: frozen for the demo; changes only through `contract-change`.
2. P1: once the organisers publish the AIS/evaluation format, adapt the export (possibly a new output model).
3. P2: schema version visible in the UI.
